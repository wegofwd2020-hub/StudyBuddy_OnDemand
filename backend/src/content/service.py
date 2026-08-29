"""
backend/src/content/service.py

Core business logic for the Content Service.

All functions are async and use the asyncpg pool + aioredis passed in as
arguments — no global state, easy to unit-test with mocks.

Cache read order (per CLAUDE.md / studybuddy-docs/BACKEND_ARCHITECTURE.md):
  L1 (in-process TTLCache) → L2 (Redis) → DB / filesystem

This module handles L2 (Redis) + DB/filesystem. The router sits above and
handles L1 where applicable.
"""

from __future__ import annotations

import json
import uuid as _uuid

import asyncpg

from src.core.cache_keys import (
    content_key,
    csv_key,
    cur_key,
    curs_key,
    ent_key,
    quiz_set_key,
    school_ent_key,
)
from src.core.storage import StorageBackend
from src.utils.logger import get_logger

log = get_logger("content.service")

_ENT_TTL = 300  # 5 minutes
_CSV_TTL = 300  # 5 minutes
_CONTENT_TTL = 3600  # 1 hour

# Model tag written by scripts/seed_dev_content.py and scripts/setup_dev.py into
# every stub file they create. Content carrying this tag is never served to a
# student — see _reject_placeholder().
PLACEHOLDER_MODEL = "dev-placeholder"


# ── School subscription helper ────────────────────────────────────────────────


async def _get_school_sub(school_id: str, pool: asyncpg.Pool, redis) -> dict | None:
    """
    Return the active school subscription as {plan, status, valid_until} or None.

    Uses school:{school_id}:ent (TTL=300 s) as L2 cache.

    Called by get_entitlement() instead of the old get_school_entitlement_for_student()
    so that the school_id (already present in the JWT) is used directly — no extra
    SELECT from the students table.
    """
    cache_key = school_ent_key(school_id)
    cached = await redis.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return data if data.get("active") else None
        except Exception:
            pass

    async with pool.acquire() as conn:
        # school_subscriptions is RLS-protected (FORCE ROW LEVEL SECURITY).
        # Stamp app.current_school_id with the school we're querying so the
        # tenant_isolation policy lets us see the row. Without this the SELECT
        # silently returns None and every school is treated as inactive/free.
        await conn.execute(
            "SELECT set_config('app.current_school_id', $1, false)",
            school_id,
        )
        row = await conn.fetchrow(
            """
            SELECT plan, status, current_period_end, grace_period_end
            FROM school_subscriptions
            WHERE school_id = $1
            """,
            _uuid.UUID(school_id),
        )

    active = row is not None and row["status"] in ("active", "trialing", "past_due")

    if active:
        if row["status"] == "past_due" and row["grace_period_end"]:
            valid_until = row["grace_period_end"].isoformat()
        elif row["current_period_end"]:
            valid_until = row["current_period_end"].isoformat()
        else:
            valid_until = None
        blob = {
            "active": True,
            "plan": row["plan"],
            "status": row["status"],
            "valid_until": valid_until,
        }
    else:
        blob = {"active": False, "plan": None, "status": None, "valid_until": None}

    await redis.set(cache_key, json.dumps(blob), ex=_ENT_TTL)
    return blob if active else None


# ── Entitlement ───────────────────────────────────────────────────────────────


async def get_entitlement(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
    school_id: str | None = None,
) -> dict:
    """
    Return {plan, lessons_accessed, valid_until} for a student.

    Decision order (ADR-001 Decision 2 — school_subscriptions is source of truth):

      1. L2 cache: school:{school_id}:ent:{student_id}  (or ent:{student_id})  TTL=300
      2. If school_id present → query school_subscriptions via _get_school_sub()
           active/trialing/past_due  → derive plan from subscription
                                        lessons_accessed from student_entitlements (usage only)
           absent / cancelled        → treat as free
      3. Unaffiliated / free tier → query student_entitlements directly

    school_id is taken from the JWT payload, so no extra students-table lookup is needed.
    """
    key = ent_key(student_id, school_id)
    cached = await redis.get(key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass  # stale / corrupt — fall through to DB

    # ── School subscription path ──────────────────────────────────────────────
    if school_id:
        sub = await _get_school_sub(school_id, pool, redis)
        if sub is not None:
            # lessons_accessed is still tracked in student_entitlements (usage counter).
            async with pool.acquire() as conn:
                ent_row = await conn.fetchrow(
                    "SELECT lessons_accessed FROM student_entitlements WHERE student_id = $1",
                    student_id,
                )
            entitlement = {
                "plan": sub["plan"],
                "lessons_accessed": ent_row["lessons_accessed"] if ent_row else 0,
                "valid_until": sub["valid_until"],
            }
            await redis.set(key, json.dumps(entitlement), ex=_ENT_TTL)
            return entitlement
        # School exists but subscription inactive → fall through to free tier

    # ── Free / unaffiliated path ──────────────────────────────────────────────
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan, lessons_accessed, valid_until FROM student_entitlements WHERE student_id = $1",
            student_id,
        )

    if row is None:
        entitlement = {"plan": "free", "lessons_accessed": 0, "valid_until": None}
    else:
        entitlement = {
            "plan": row["plan"],
            "lessons_accessed": row["lessons_accessed"],
            "valid_until": row["valid_until"].isoformat() if row["valid_until"] else None,
        }

    await redis.set(key, json.dumps(entitlement), ex=_ENT_TTL)
    return entitlement


# ── Content publish check ─────────────────────────────────────────────────────


async def check_content_published(
    curriculum_id: str,
    subject: str,
    pool: asyncpg.Pool,
    redis,
) -> bool:
    """
    Return True if the subject's content is published for the given curriculum.

    L2 cache: csv:{curriculum_id}:{subject} TTL=300.
    """
    key = csv_key(curriculum_id, subject)
    cached = await redis.get(key)
    if cached is not None:
        return cached == b"1" or cached == "1"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM content_subject_versions
            WHERE curriculum_id = $1 AND subject = $2 AND status = 'published'
            LIMIT 1
            """,
            curriculum_id,
            subject,
        )

    published = row is not None
    await redis.set(key, "1" if published else "0", ex=_CSV_TTL)
    return published


# ── Content file serving ──────────────────────────────────────────────────────


def _reject_placeholder(data, curriculum_id: str, unit_id: str, filename: str) -> None:
    """
    Refuse to serve dev-seeded placeholder content.

    The dev/demo seeders backfill missing units with stub lessons and quizzes
    (always-'A' answers, "Sample question N about X?") tagged
    model="dev-placeholder". They only write where a file is absent, so any unit
    the pipeline hasn't generated keeps its stub forever. Serving one hands a
    student fake content — and a fake grade — indistinguishable from the real
    thing. Treat it as missing so the caller 404s into the normal
    "not available yet" state.
    """
    if isinstance(data, dict) and data.get("model") == PLACEHOLDER_MODEL:
        log.warning(
            "placeholder_content_refused",
            extra={
                "curriculum_id": curriculum_id,
                "unit_id": unit_id,
                "filename": filename,
            },
        )
        raise FileNotFoundError(
            f"placeholder content refused: curricula/{curriculum_id}/{unit_id}/{filename}"
        )


async def get_content_file(
    curriculum_id: str,
    unit_id: str,
    filename: str,
    redis,
    storage: StorageBackend,
) -> dict:
    """
    Read a content JSON file from the Content Store.

    L2 cache: content:{curriculum_id}:{unit_id}:{filename} TTL=3600.

    Raises FileNotFoundError if the file doesn't exist, or if it is dev-seeded
    placeholder content (see _reject_placeholder).
    """
    key = content_key(curriculum_id, unit_id, filename)
    cached = await redis.get(key)
    if cached:
        try:
            data = json.loads(cached)
        except (ValueError, TypeError):
            data = None  # corrupt cache entry — fall through to the store
        if data is not None:
            # Guard the cache path too: a stub cached by an older build would
            # otherwise keep being served for the full TTL.
            _reject_placeholder(data, curriculum_id, unit_id, filename)
            return data

    path = f"curricula/{curriculum_id}/{unit_id}/{filename}"
    data = await storage.read_json(path)  # raises FileNotFoundError if absent

    # Check before caching — never let a placeholder into L2.
    _reject_placeholder(data, curriculum_id, unit_id, filename)

    await redis.set(key, json.dumps(data), ex=_CONTENT_TTL)
    return data


# ── Lessons-accessed counter ──────────────────────────────────────────────────


async def increment_lessons_accessed(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
    school_id: str | None = None,
) -> None:
    """
    Increment lessons_accessed for a student.
    Upserts the student_entitlements row if absent.
    Invalidates the correct namespaced ent key (ADR-001 Decision 3).
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO student_entitlements (student_id, plan, lessons_accessed)
            VALUES ($1, 'free', 1)
            ON CONFLICT (student_id) DO UPDATE
                SET lessons_accessed = student_entitlements.lessons_accessed + 1,
                    updated_at = NOW()
            """,
            student_id,
        )

    # Invalidate L2 cache
    await redis.delete(ent_key(student_id, school_id))


# ── Curriculum resolver ───────────────────────────────────────────────────────


async def resolve_curriculum_id(
    student_id: str,
    grade: int,
    pool: asyncpg.Pool,
    redis,
    year: int = 2026,
    school_id: str | None = None,
) -> str:
    """
    Return the curriculum_id for a student.

    L2 cache: school:{school_id}:cur:{student_id} (or cur:{student_id} if unaffiliated).
    On miss: queries school enrollment or falls back to default-{year}-g{grade}.

    PRIMARY SCHOOL ONLY (decision 2026-08-24, from #572). A student may hold
    enrolments at several schools — a school for their regular curriculum and,
    say, an external tutor running additional classes. Content resolution
    deliberately follows ONE of them: `students.school_id`, their primary
    school. Step 1 below joins that column, so passing a different `school_id`
    changes the RLS scope and the cache key but NOT which school's curriculum is
    chosen.

    Consequence to be aware of before "fixing" this: additional enrolments are
    for ROSTERING AND REPORTING, not delivery. A tutor can enrol a student and
    report on them but cannot serve them different material. Making that work
    needs a way for the student to choose which school they are working in — an
    explicit product decision, not a change to this function alone.
    """
    ids = await resolve_curriculum_ids(
        student_id, grade, pool, redis, year=year, school_id=school_id
    )
    return ids[0]


async def resolve_curriculum_ids(
    student_id: str,
    grade: int,
    pool: asyncpg.Pool,
    redis,
    year: int = 2026,
    school_id: str | None = None,
) -> list[str]:
    """
    Every curriculum a student's content comes from, in order.

    A classroom may carry several packages and they are ADDITIVE and DISTINCT
    (product decision, 2026-08-28, #651): the student's curriculum is the UNION
    of its packages, not one of them. Resolution used to take

        ORDER BY cl.created_at DESC LIMIT 1

    — the classroom's creation date, then an arbitrary package among that
    classroom's several — which is why a Grade 11 student on the demo was served
    Grade 8 content while two other packages sat unread.

    `resolve_curriculum_id` returns element [0] of this list, so the single-
    curriculum callers (serving one unit, cache keys) cannot disagree with the
    additive ones about which curriculum is primary. One resolver, as ever.

    Ordering is `sort_order, assigned_at, curriculum_id` — deterministic, and it
    finally reads the `classroom_packages.sort_order` column that has existed
    unused since the table was created.

    Distinctness is already enforced by the table's PRIMARY KEY
    (classroom_id, curriculum_id); nothing yet prevents two packages from
    containing the SAME unit, which is a separate guard at assignment time.
    """
    key = curs_key(student_id, school_id)
    cached = await redis.get(key)
    if cached:
        try:
            raw = cached.decode() if isinstance(cached, bytes) else cached
            ids = json.loads(raw)
            if isinstance(ids, list) and ids:
                return ids
        except Exception:
            pass

    ids: list[str] = []
    async with pool.acquire() as conn:
        # Set RLS session variable upfront so both steps can see school-owned
        # rows. Without this, curricula with owner_type='school' are filtered
        # out by the RLS USING clause even though the JOIN condition references
        # the correct school_id FK column.
        if school_id:
            await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)

        # 1. School-owned curriculum for this student's grade — includes school
        #    fork curricula created by the teacher authoring flow (TA-0/TA-2).
        row = await conn.fetchrow(
            """
            SELECT c.curriculum_id
            FROM students s
            JOIN schools sc ON s.school_id = sc.school_id
            JOIN curricula c ON c.school_id = sc.school_id AND c.grade = s.grade
            WHERE s.student_id = $1
            LIMIT 1
            """,
            student_id,
        )
        if row:
            ids = [row["curriculum_id"]]

        # 2. Classroom packages — ALL of them (#651), in a stable order.
        if not ids and school_id:
            rows = await conn.fetch(
                """
                SELECT DISTINCT cp.curriculum_id, cp.sort_order, cp.assigned_at
                FROM classroom_students cs
                JOIN classrooms cl ON cl.classroom_id = cs.classroom_id
                JOIN classroom_packages cp ON cp.classroom_id = cl.classroom_id
                WHERE cs.student_id = $1
                ORDER BY cp.sort_order, cp.assigned_at, cp.curriculum_id
                """,
                student_id,
            )
            ids = [r["curriculum_id"] for r in rows]

    # 3. Default STEM fallback
    if not ids:
        ids = [f"default-{year}-g{grade}"]

    await redis.set(key, json.dumps(ids), ex=_CSV_TTL)
    # Keep the single-id cache in step with the set, so a caller reading either
    # gets the same primary.
    await redis.set(cur_key(student_id, school_id), ids[0], ex=_CSV_TTL)
    return ids


# ── Content block check ───────────────────────────────────────────────────────


async def check_content_block(
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    pool: asyncpg.Pool,
) -> bool:
    """
    Return True if the content item is actively blocked by an admin.
    A block is active when unblocked_at IS NULL.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM content_blocks
            WHERE curriculum_id = $1
              AND unit_id = $2
              AND content_type = $3
              AND unblocked_at IS NULL
            LIMIT 1
            """,
            curriculum_id,
            unit_id,
            content_type,
        )
    return row is not None


# ── Quiz rotation ─────────────────────────────────────────────────────────────


async def get_next_quiz_set(
    student_id: str,
    unit_id: str,
    redis,
) -> int:
    """
    Return the next quiz set number (1, 2, or 3) using round-robin rotation.
    Tracks state in Redis key quiz_set:{student_id}:{unit_id}.
    """
    key = quiz_set_key(student_id, unit_id)
    current = await redis.get(key)

    if current is None:
        next_set = 1
    else:
        try:
            last = int(current)
        except (ValueError, TypeError):
            last = 0
        next_set = (last % 3) + 1

    await redis.set(key, str(next_set), ex=86400 * 7)  # 7-day TTL
    return next_set


# ── Subject from unit ID ──────────────────────────────────────────────────────


async def get_unit_subject(
    unit_id: str,
    curriculum_id: str,
    pool: asyncpg.Pool,
) -> str | None:
    """
    Return the subject for a unit by looking it up in curriculum_units.
    Returns None if the unit is not found.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT subject FROM curriculum_units WHERE unit_id = $1 AND curriculum_id = $2",
            unit_id,
            curriculum_id,
        )
    return row["subject"] if row else None


# ── Teacher content overrides ─────────────────────────────────────────────────


async def get_active_override(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    lang: str,
    content_type: str,
    pool: asyncpg.Pool,
    redis,
) -> dict | None:
    """
    Return the active teacher override body for (school, curriculum, unit, lang,
    content_type), or None if no active override exists.

    L2 cache: school:{school_id}:override:... TTL=3600.
    A Redis value of JSON null is the miss sentinel — avoids a DB hit on every
    content request for units that don't have teacher overrides.
    """
    from src.core.cache_keys import override_key as _override_key

    key = _override_key(school_id, curriculum_id, unit_id, lang, content_type)
    raw = await redis.get(key)
    if raw is not None:
        try:
            return json.loads(raw)  # None for "null" sentinel, dict for override
        except Exception:
            pass

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        row = await conn.fetchrow(
            """
            SELECT uco.body
            FROM unit_content_active_versions ucav
            JOIN unit_content_overrides uco ON uco.override_id = ucav.override_id
            WHERE ucav.school_id = $1::UUID
              AND ucav.curriculum_id = $2
              AND ucav.unit_id = $3
              AND ucav.lang = $4
              AND ucav.content_type = $5
            """,
            school_id,
            curriculum_id,
            unit_id,
            lang,
            content_type,
        )

    body: dict | None = dict(row["body"]) if row else None
    await redis.set(key, json.dumps(body), ex=_CONTENT_TTL)
    return body


async def get_fork_source_curriculum(
    curriculum_id: str,
    school_id: str,
    pool: asyncpg.Pool,
) -> str | None:
    """
    Return the source OOB curriculum_id for a school fork, or None.

    School fork curricula have no rows in curriculum_units or content_subject_versions
    — both live under the source OOB curriculum_id. This is used by the content
    serving path to fall back to OOB files for units without active teacher overrides.
    """
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        row = await conn.fetchrow(
            "SELECT source_curriculum_id FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
    return row["source_curriculum_id"] if (row and row["source_curriculum_id"]) else None


# ── Quiz answer key (server-side grading) ─────────────────────────────────────


async def get_quiz_answer_key(
    curriculum_id: str,
    unit_id: str,
    set_number: int,
    lang: str,
    redis,
    storage: StorageBackend,
) -> dict[str, dict]:
    """
    Return the grading key for one quiz set: {question_id: {index, explanation}}.

    The correct answer lives ONLY on the server. Grading resolves it from the
    content store here rather than trusting anything the client sends.

    `correct_option` is a letter ("A".."D"); the index is that option's position
    in the question's own `options` list, matched by `option_id` — not by
    alphabetical position, so a question whose options are ordered B, A, C still
    grades correctly.

    Raises FileNotFoundError if the set is absent (placeholder content included —
    get_content_file refuses it).
    """
    filename = f"quiz_set_{set_number}_{lang}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        # Same English fallback the quiz endpoint uses, so grading matches what
        # was actually served to the student.
        data = await get_content_file(
            curriculum_id, unit_id, f"quiz_set_{set_number}_en.json", redis, storage
        )

    return _parse_quiz_answer_key(data, curriculum_id, unit_id, set_number)


def _parse_quiz_answer_key(
    data: dict, curriculum_id: str, unit_id: str, set_number: int
) -> dict[str, dict]:
    """Build {question_id: {index, explanation}} from a quiz-set body.

    Shared by the content-store path (`get_quiz_answer_key`) and the teacher-override
    path (`resolve_quiz_answer_key`) so both grade a question the same way — by the
    correct option's position in its OWN options list, matched by `option_id`.
    """
    key: dict[str, dict] = {}
    for question in data.get("questions", []):
        qid = question.get("question_id")
        if not qid:
            continue
        options = question.get("options", [])
        correct_option = question.get("correct_option")
        index = next(
            (i for i, o in enumerate(options) if o.get("option_id") == correct_option),
            None,
        )
        if index is None:
            # Content defect: the correct_option names an option that isn't in the
            # list. Skip rather than silently grading every answer wrong.
            log.error(
                "quiz_answer_key_unresolvable",
                extra={
                    "curriculum_id": curriculum_id,
                    "unit_id": unit_id,
                    "set_number": set_number,
                    "question_id": qid,
                    "correct_option": correct_option,
                },
            )
            continue
        key[qid] = {
            "index": index,
            "explanation": question.get("explanation", ""),
        }
    return key


async def resolve_content_curriculum(
    unit_id: str,
    curriculum_id: str,
    school_id: str | None,
    pool: asyncpg.Pool,
) -> tuple[str, str | None]:
    """Resolve the curriculum_id + subject to SERVE/GRADE store content under.

    School fork curricula have no rows in `curriculum_units` (those live under the
    source OOB curriculum_id), so for a fork we swap to the source. Returns the
    (possibly swapped) curriculum_id and the unit's subject, or (curriculum_id,
    None) when the unit resolves nowhere.

    This is the single source of truth for the fork→OOB swap that both the content
    serving path and the quiz grading path depend on. They drifted before
    (grading skipped the swap → every answer 404'd for fork-adopting schools, #529).
    """
    subject = await get_unit_subject(unit_id, curriculum_id, pool)
    if subject is None and school_id:
        source_id = await get_fork_source_curriculum(curriculum_id, school_id, pool)
        if source_id:
            src_subject = await get_unit_subject(unit_id, source_id, pool)
            if src_subject is not None:
                return source_id, src_subject
    return curriculum_id, subject


async def resolve_unit_curriculum(
    unit_id: str,
    curriculum_ids: list[str],
    school_id: str | None,
    pool: asyncpg.Pool,
) -> tuple[str, str | None]:
    """Which of a student's packages holds this unit, and the unit's subject.

    A classroom's packages are additive (#651), so "the student's curriculum" is
    a list and only one member of it actually contains any given unit. Serving
    used the FIRST — the primary — which meant a unit belonging to the second or
    third package resolved nowhere and 404'd, even though the curriculum tree
    listed it.

    Walks the list in resolution order and returns the first package that holds
    the unit, applying the fork -> OOB swap per package via
    `resolve_content_curriculum` — still the single source of truth for that
    swap, so serving and grading cannot drift apart (#529).

    When no package holds the unit, returns the primary with subject None, which
    is the same "resolves nowhere" signal callers already handle.
    """
    for candidate in curriculum_ids:
        resolved, subject = await resolve_content_curriculum(unit_id, candidate, school_id, pool)
        if subject is not None:
            return resolved, subject
    return (curriculum_ids[0] if curriculum_ids else ""), None


async def resolve_quiz_answer_key(
    school_id: str | None,
    curriculum_id: str,
    unit_id: str,
    set_number: int,
    lang: str,
    pool: asyncpg.Pool,
    redis,
    storage: StorageBackend,
) -> dict[str, dict]:
    """Grading-side answer key that mirrors exactly what the student was SERVED.

    Serving a quiz to a school student (content/router.py) resolves it in this
    order: an active teacher override (keyed by the school's own/fork curriculum_id)
    wins; otherwise store content under the fork's OOB source. Grading has to follow
    the same order or it grades against the wrong key:

    - override present  → grade against the override body (its `q1…qN` differ from
      the store's — the pitfall #35 collision that misgrades silently, #529);
    - fork, no override → swap to the OOB source and read the store (the fork has no
      store content of its own → a raw lookup 404s, #529).

    Raises FileNotFoundError only when the store content is genuinely absent.
    """
    if school_id:
        override = await get_active_override(
            school_id, curriculum_id, unit_id, lang, f"quiz_set_{set_number}", pool, redis
        )
        if override:
            return _parse_quiz_answer_key(override, curriculum_id, unit_id, set_number)
        curriculum_id, _ = await resolve_content_curriculum(unit_id, curriculum_id, school_id, pool)
    return await get_quiz_answer_key(curriculum_id, unit_id, set_number, lang, redis, storage)
