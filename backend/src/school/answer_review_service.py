"""
backend/src/school/answer_review_service.py

Quiz answer review (#762) — list every quiz question of a unit for a school
reviewer, with its correct answer, this school's validation state, and how
many of this school's own students flagged it.

Which BODY is listed mirrors serving exactly (`resolve_quiz_answer_key`,
content/service.py) so a reviewer always reviews what is actually served: the
school's active override where it has one, the content store otherwise, per
quiz set.

How a question is IDENTIFIED is a separate question with a single answer: the
`stable_question_id` is always hashed with the SOURCE curriculum id and with
the language of the file actually read. It names the QUESTION, not the place
the body came from, and every id already recorded against `progress_answers`
and `feedback` is `H(source_id, unit, key_lang, stem)` — the session stores
the swapped id, and the grading key mints it from there. An id minted any
other way joins to nothing: the flag count reads 0 forever and a correction
orphans the tick it just wrote.

Deliberately takes a single `conn` (acquired via `get_db(request)` in the
router, not `Depends(get_db)` -- see Epic 15's bug) rather than a pool. The
shared content-service helpers (`get_active_override`, `resolve_content_curriculum`,
`get_school_fork_for_source`) all take a `pool` because they acquire their own
connection and stamp a specific school's RLS context onto it. `_ConnAsPool`
adapts the single connection to that `pool.acquire()` shape so this module
reuses those helpers verbatim instead of re-deriving their SQL.
"""

from __future__ import annotations

from src.content.service import (
    get_active_override,
    get_content_file,
    get_school_fork_for_source,
    resolve_content_curriculum,
)
from src.core.question_identity import stable_question_id
from src.core.storage import StorageBackend
from src.utils.logger import get_logger

log = get_logger("school.answer_review")

_QUIZ_SET_NUMBERS = (1, 2, 3)


class _ConnAsPool:
    """Adapts a single asyncpg Connection to `pool.acquire()`.

    `pool.acquire()` is called (not awaited) and the result used as an async
    context manager -- exactly what asyncpg's real Pool.acquire() returns.
    Returning `self` from both `acquire()` and `__aenter__` satisfies that
    shape without a second connection: the caller already owns this one via
    `get_db(request)`, and the shared helpers only ever read.

    CONSTRAINT: every acquire must be SEQUENTIAL. Two concurrent acquires would
    both be handed the SAME connection and asyncpg would raise on the second
    query issued against it. `list_unit_answers` awaits its helpers one at a
    time and must keep doing so -- do not gather() them.
    """

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc_info):
        return False


def _normalise(text: str | None) -> str:
    """Collapse whitespace the way `_parse_quiz_answer_key` does
    (content/service.py:718), so a staleness comparison against a stored
    `question_validations.correct_text` means what it says."""
    return " ".join((text or "").split())


def _correct_option_text(options: list[dict], correct_option: str | None) -> str:
    """The correct option's normalised text, or "" when it names no option."""
    for option in options:
        if option.get("option_id") == correct_option:
            return _normalise(option.get("text"))
    return ""


async def _resolve_ownership(conn, pool, *, school_id: str, curriculum_id: str, unit_id: str):
    """(source_curriculum_id, owned_curriculum_id) for this school and path id.

    The path id can arrive either way round, and BOTH have to resolve to the
    same pair:

      - the school's own FORK id (from the unit editor, which only lists
        adopted curricula) -> swap to the source for store reads;
      - the PLATFORM id (from the Unit Performance report, which carries the
        curriculum the classroom package holds -- the spec's primary and, on
        the demo, only workable entry point) -> look up the school's fork of
        it, if any.

    Without the reverse lookup a school that already owns a fork is told it
    owns nothing, is shown the platform's questions rather than the ones its
    students sit, and is offered a fork-confirmation for a copy it has.
    """
    row = await conn.fetchrow(
        "SELECT owner_type, school_id, source_curriculum_id FROM curricula WHERE curriculum_id = $1",
        curriculum_id,
    )
    is_own_fork = bool(
        row and row["owner_type"] == "school" and str(row["school_id"]) == str(school_id)
    )
    if is_own_fork:
        source_curriculum_id, _subject = await resolve_content_curriculum(
            unit_id, curriculum_id, school_id, pool
        )
        return source_curriculum_id, curriculum_id

    owned = await get_school_fork_for_source(curriculum_id, school_id, pool)
    return curriculum_id, owned


async def list_unit_answers(
    conn,
    storage: StorageBackend,
    redis,
    *,
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    lang: str,
) -> dict:
    """Every quiz question of `unit_id`, as this school would be served it.

    Returns {"ownership": "none|fork|override", "source_curriculum_id": str,
    "owned_curriculum_id": str | None, "questions": [...]} -- see
    AnswerReviewListResponse for the question shape.
    """
    pool = _ConnAsPool(conn)

    source_curriculum_id, owned_curriculum_id = await _resolve_ownership(
        conn, pool, school_id=school_id, curriculum_id=curriculum_id, unit_id=unit_id
    )

    # ── 1. Read each set: override first, else the store under the source ──
    has_override = False
    missing_sets: list[int] = []
    # (set_number, body, key_lang, served_from)
    per_set: list[tuple[int, dict, str, str]] = []

    for set_number in _QUIZ_SET_NUMBERS:
        content_type = f"quiz_set_{set_number}"
        override_body: dict | None = None
        if owned_curriculum_id:
            override_body = await get_active_override(
                school_id, owned_curriculum_id, unit_id, lang, content_type, pool, redis
            )

        if override_body is not None:
            has_override = True
            per_set.append((set_number, override_body, lang, "override"))
            continue

        # The same English fallback serving uses (content/router.py:542-552),
        # and `key_lang` is what the identity is hashed with -- hashing with the
        # REQUESTED language would mint a French id for English questions and
        # split one item's statistics across two identities
        # (`get_quiz_answer_key` carries the same rule).
        body = None
        key_lang = lang
        for filename, file_lang in (
            (f"{content_type}_{lang}.json", lang),
            (f"{content_type}_en.json", "en"),
        ):
            try:
                body = await get_content_file(
                    source_curriculum_id, unit_id, filename, redis, storage
                )
                key_lang = file_lang
                break
            except FileNotFoundError:
                continue
        if body is None:
            # Not every unit has three sets -- but "no quiz at all", "the store
            # refused placeholder content" and "the read failed" all land here
            # and all return 200 with an empty list, which a reviewer cannot
            # tell apart. Say which.
            missing_sets.append(set_number)
            continue
        per_set.append((set_number, body, key_lang, "store"))

    if missing_sets:
        log.info(
            "answer_review_sets_missing",
            school_id=school_id,
            curriculum_id=source_curriculum_id,
            unit_id=unit_id,
            lang=lang,
            missing_sets=missing_sets,
        )

    ownership = "override" if has_override else ("fork" if owned_curriculum_id else "none")

    # ── 2. Build the question list + collect stable ids for the joins ──────
    questions: list[dict] = []
    stable_ids: list[str] = []
    for set_number, body, key_lang, served_from in per_set:
        for question in body.get("questions") or []:
            if not isinstance(question, dict) or not question.get("question_id"):
                # One malformed row must not take the other twenty with it:
                # `_parse_quiz_answer_key` skips these too, so a listing that
                # 500s here would hide a unit the grader serves happily.
                log.warning(
                    "answer_review_question_skipped",
                    curriculum_id=source_curriculum_id,
                    unit_id=unit_id,
                    set_number=set_number,
                    reason="not a question object with a question_id",
                )
                continue

            text = question.get("question_text") or ""
            options = [o for o in (question.get("options") or []) if isinstance(o, dict)]
            correct_option = question.get("correct_option")
            # `_parse_quiz_answer_key` logs `quiz_answer_key_unresolvable` and
            # DROPS a question whose correct_option names no existing option --
            # nobody is graded on it. Rendering "correct: C" beside options A, B
            # and D with no signal is precisely the defect a reviewer opens this
            # page to find.
            resolves = any(o.get("option_id") == correct_option for o in options)
            sid = stable_question_id(source_curriculum_id, unit_id, key_lang, text)
            stable_ids.append(sid)
            questions.append(
                {
                    "stable_question_id": sid,
                    "set_number": set_number,
                    "question_id": question["question_id"],
                    "question_text": text,
                    "options": [
                        {"option_id": o.get("option_id"), "text": o.get("text") or ""}
                        for o in options
                    ],
                    "correct_option": correct_option,
                    "correct_option_resolves": resolves,
                    "served_from": served_from,
                    "_correct_text": _correct_option_text(options, correct_option),
                    "flag_count": 0,
                    "validated": None,
                }
            )

    result = {
        "ownership": ownership,
        "source_curriculum_id": source_curriculum_id,
        "owned_curriculum_id": owned_curriculum_id,
        "questions": questions,
    }
    if not stable_ids:
        return result

    # ── 3. Left-join this school's validations ──────────────────────────────
    validation_rows = await conn.fetch(
        """
        SELECT stable_question_id, correct_text, validated_by, validated_at
        FROM question_validations
        WHERE school_id = $1 AND stable_question_id = ANY($2::text[])
        """,
        school_id,
        stable_ids,
    )
    validations = {r["stable_question_id"]: r for r in validation_rows}

    # ── 4. Left-join flag counts, scoped to THIS school's own students ─────
    #
    # A membership predicate, not a JOIN: `school_enrolments` is UNIQUE
    # (school_id, student_email) and NOT on (school_id, student_id), so one
    # person under two addresses at one school is two rows and a JOIN counts
    # every flag twice. Aggregate the child table before joining (#623/#625).
    # `status = 'active'` scopes it the way every sibling in reports/service.py
    # does.
    flag_rows = await conn.fetch(
        """
        SELECT f.stable_question_id, COUNT(*) AS flags
        FROM feedback f
        WHERE f.stable_question_id = ANY($2::text[])
          AND f.student_id IN (
                SELECT student_id FROM school_enrolments
                WHERE school_id = $1 AND status = 'active' AND student_id IS NOT NULL)
        GROUP BY 1
        """,
        school_id,
        stable_ids,
    )
    flag_counts = {r["stable_question_id"]: r["flags"] for r in flag_rows}

    for question in questions:
        sid = question["stable_question_id"]
        question["flag_count"] = flag_counts.get(sid, 0)
        current_correct_text = question.pop("_correct_text")
        validation = validations.get(sid)
        if validation is None:
            question["validated"] = None
        else:
            question["validated"] = {
                "by": str(validation["validated_by"]),
                "at": validation["validated_at"].isoformat(),
                "stale": validation["correct_text"] != current_correct_text,
            }

    return result
