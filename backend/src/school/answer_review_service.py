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

import json

from src.content.service import (
    get_active_override,
    get_content_file,
    get_school_fork_for_source,
    resolve_content_curriculum,
)
from src.core.cache_keys import override_key
from src.core.question_identity import stable_question_id
from src.core.question_identity import stable_question_id as stable_question_id_of
from src.core.storage import StorageBackend
from src.utils.logger import get_logger

log = get_logger("school.answer_review")

_QUIZ_SET_NUMBERS = (1, 2, 3)


class QuestionNotInUnit(LookupError):
    """The supplied `stable_question_id` is in no quiz set of this unit.

    `stable_question_id` is a hash the caller hands us and `question_validations`
    has no foreign key that could reject it, so without this the upsert would
    happily record a tick against a question that does not exist here — one the
    listing can never show and nobody can ever clear.
    """


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


async def _resolve_unit_quiz_sets(
    conn,
    pool,
    storage: StorageBackend,
    redis,
    *,
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    lang: str,
) -> tuple[str, str | None, bool, list[tuple[int, dict, str, str]]]:
    """Resolve ownership and read every quiz set's BODY the way serving does.

    Returns (source_curriculum_id, owned_curriculum_id, has_override, per_set)
    where per_set is [(set_number, body, key_lang, served_from)].

    Split out of `list_unit_answers` so `correct_answer` can reuse it: a
    correction needs the whole body (it writes a new version of it), not only
    the question summary the listing projects. Deriving the body a second time
    would be a second resolution of "what is this school served", and the two
    would drift — silently, because the one that drifted is the one that writes.
    """
    source_curriculum_id, owned_curriculum_id = await _resolve_ownership(
        conn, pool, school_id=school_id, curriculum_id=curriculum_id, unit_id=unit_id
    )

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

    return source_curriculum_id, owned_curriculum_id, has_override, per_set


def _questions_from_sets(
    per_set: list[tuple[int, dict, str, str]],
    *,
    source_curriculum_id: str,
    unit_id: str,
) -> list[dict]:
    """Project the resolved bodies onto the question shape the page reads.

    The `stable_question_id` is minted HERE and nowhere else in this module, so
    the listing, the tick and the correction cannot disagree about which
    question they are talking about.
    """
    questions: list[dict] = []
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
            questions.append(
                {
                    "stable_question_id": sid,
                    "set_number": set_number,
                    # Private to this module: the language the body was actually
                    # read in, which a correction must write its new version
                    # under. Stripped before the response is built.
                    "_key_lang": key_lang,
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

    return questions


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

    (
        source_curriculum_id,
        owned_curriculum_id,
        has_override,
        per_set,
    ) = await _resolve_unit_quiz_sets(
        conn,
        pool,
        storage,
        redis,
        school_id=school_id,
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        lang=lang,
    )
    ownership = "override" if has_override else ("fork" if owned_curriculum_id else "none")
    questions = _questions_from_sets(
        per_set, source_curriculum_id=source_curriculum_id, unit_id=unit_id
    )
    for question in questions:
        question.pop("_key_lang", None)

    result = {
        "ownership": ownership,
        "source_curriculum_id": source_curriculum_id,
        "owned_curriculum_id": owned_curriculum_id,
        "questions": questions,
    }
    stable_ids = [q["stable_question_id"] for q in questions]
    if not stable_ids:
        return result

    # ── Left-join this school's validations ─────────────────────────────────
    #
    # The reviewer's NAME comes with the row, resolved in SQL the way every
    # sibling content endpoint resolves it (`t.name AS last_edited_by_name`,
    # school/router.py). Without it the page can only show a `teachers` UUID at
    # a reader who cannot resolve it — the roster endpoint is school_admin-only
    # while this page is open to any curriculum-capable teacher. LEFT, not
    # INNER: a join that misses must cost the name, never the question.
    validation_rows = await conn.fetch(
        """
        SELECT qv.stable_question_id, qv.correct_text, qv.validated_by,
               qv.validated_at, t.name AS validated_by_name
        FROM question_validations qv
        LEFT JOIN teachers t ON t.teacher_id = qv.validated_by
        WHERE qv.school_id = $1 AND qv.stable_question_id = ANY($2::text[])
        """,
        school_id,
        stable_ids,
    )
    validations = {r["stable_question_id"]: r for r in validation_rows}

    # ── Left-join flag counts, scoped to THIS school's own students ────────
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
                "by_name": validation["validated_by_name"],
                "at": validation["validated_at"].isoformat(),
                "stale": validation["correct_text"] != current_correct_text,
            }

    return result


async def validate_answer(
    conn,
    storage: StorageBackend,
    redis,
    *,
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    lang: str,
    stable_question_id: str,
    teacher_id: str,
) -> dict:
    """Record that this school has checked `stable_question_id`'s answer.

    Returns {"validated_by": str, "validated_at": str (ISO), "correct_text": str}.
    Raises `QuestionNotInUnit` when the id is in no set of this unit.

    The question is resolved through `list_unit_answers` — the same path the
    page read it from — rather than by re-deriving it here. Two derivations of
    one identity drift apart silently, and this one has to agree with the
    listing exactly: the tick it writes is read back by that listing's
    left-join, and a row written under an id the listing does not mint is
    invisible forever.

    `correct_text` is a SNAPSHOT, not a key: the listing calls a tick stale once
    the current correct option's text no longer matches it. Stored with the same
    normalisation `_correct_option_text` applies, because the comparison is
    string equality.

    NOTE: the signature takes `storage`/`redis` on top of the `conn` the plan
    named, because resolving through the listing means reading the content
    store and the override cache. Resolving without them would mean a second,
    parallel derivation — the thing this function exists to avoid.
    """
    listing = await list_unit_answers(
        conn,
        storage,
        redis,
        school_id=school_id,
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        lang=lang,
    )
    matches = sorted(
        (q for q in listing["questions"] if q["stable_question_id"] == stable_question_id),
        key=lambda q: q["set_number"],
    )
    if not matches:
        raise QuestionNotInUnit(stable_question_id)

    # One identity can span several sets (the hash covers the stem, not the set
    # number — question_identity.py). Normally they carry the same answer, and
    # then there is nothing to choose. When they DISAGREE the sets are keyed
    # differently for one question, which is itself the defect a reviewer is
    # here to find: snapshot the lowest set's answer deterministically and say
    # so, rather than picking whichever the dict happened to yield first. The
    # listing still judges staleness per set, so the disagreement stays visible.
    distinct = {_correct_option_text(q["options"], q["correct_option"]) for q in matches}
    correct_text = _correct_option_text(matches[0]["options"], matches[0]["correct_option"])
    if len(distinct) > 1:
        log.warning(
            "answer_review_validate_sets_disagree",
            school_id=school_id,
            curriculum_id=listing["source_curriculum_id"],
            unit_id=unit_id,
            stable_question_id=stable_question_id,
            sets=[q["set_number"] for q in matches],
            snapshot=correct_text,
        )

    return await _upsert_validation(
        conn,
        school_id=school_id,
        stable_question_id=stable_question_id,
        correct_text=correct_text,
        teacher_id=teacher_id,
    )


async def _upsert_validation(
    conn,
    *,
    school_id: str,
    stable_question_id: str,
    correct_text: str,
    teacher_id: str,
) -> dict:
    """Record (school, question) -> the answer text vouched for, and by whom.

    Shared by `validate_answer` and `correct_answer` because the design says a
    correction re-validates automatically, by the reviewer who made it — and a
    second copy of this upsert would be a second chance to snapshot a different
    text, which is precisely the comparison the `stale` flag is made of.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO question_validations
            (school_id, stable_question_id, correct_text, validated_by, validated_at)
        VALUES ($1::UUID, $2, $3, $4::UUID, now())
        ON CONFLICT (school_id, stable_question_id) DO UPDATE
            SET correct_text = EXCLUDED.correct_text,
                validated_by = EXCLUDED.validated_by,
                validated_at = now()
        RETURNING validated_by::TEXT AS validated_by, validated_at
        """,
        school_id,
        stable_question_id,
        correct_text,
        teacher_id,
    )

    return {
        "validated_by": row["validated_by"],
        "validated_at": row["validated_at"].isoformat(),
        "correct_text": correct_text,
    }


# ── Correcting an answer ──────────────────────────────────────────────────────


class ForkConfirmationRequired(RuntimeError):
    """The school has no copy of this curriculum, so correcting one answer would
    create an adoption, a fork and an import — and repoint the whole grade at the
    fork. The design (§3) makes that explicit rather than silent: the reviewer
    confirms once per curriculum, not once per question."""


class OptionNotInQuestion(ValueError):
    """`correct_option` names no option this question actually has.

    Exactly the defect `_parse_quiz_answer_key` logs as
    `quiz_answer_key_unresolvable` and the listing surfaces as
    `correct_option_resolves: false` — writing one here would be creating the
    thing this page exists to find.
    """


class CorrectionInvariantError(RuntimeError):
    """The body about to be written differs from the served one in more than
    that question's `correct_option`.

    Belt and braces over a deep copy that changes one field, and deliberately
    fatal: this endpoint publishes straight to students with no review step, so
    "something else changed" must roll the transaction back rather than ship.
    Same guard shape as `scripts/rebalance_quiz_options.py::_verify`.
    """


def _verify_only_correct_option_changed(
    original: dict, corrected: dict, *, question_ids: set[str]
) -> None:
    """Every field of the body must be identical except `correct_option` on the
    named questions."""
    orig_top = {k: v for k, v in original.items() if k != "questions"}
    new_top = {k: v for k, v in corrected.items() if k != "questions"}
    if orig_top != new_top:
        raise CorrectionInvariantError("non-question fields changed")

    orig_qs = original.get("questions") or []
    new_qs = corrected.get("questions") or []
    if len(orig_qs) != len(new_qs):
        raise CorrectionInvariantError("the question list changed length")

    for orig_q, new_q in zip(orig_qs, new_qs, strict=True):
        if not isinstance(orig_q, dict) or not isinstance(new_q, dict):
            if orig_q != new_q:
                raise CorrectionInvariantError("a non-question entry changed")
            continue
        if orig_q.get("question_id") != new_q.get("question_id"):
            raise CorrectionInvariantError("question order changed")
        stripped_orig = {k: v for k, v in orig_q.items() if k != "correct_option"}
        stripped_new = {k: v for k, v in new_q.items() if k != "correct_option"}
        if stripped_orig != stripped_new:
            # Includes `question_text` — the stable_question_id's only input.
            # Changing it here would orphan every recorded answer and flag.
            raise CorrectionInvariantError("a question changed beyond its correct option")
        if orig_q.get("question_id") not in question_ids:
            if orig_q.get("correct_option") != new_q.get("correct_option"):
                raise CorrectionInvariantError("a question that was not targeted was re-keyed")


class CurriculumNotAdoptable(ValueError):
    """The curriculum is not a platform OOB package, so the school cannot take a
    copy of it — the same refusal `adopt_curriculum` gives."""


async def _ensure_adoption(
    conn, *, school_id: str, source_curriculum_id: str, teacher_id: str
) -> tuple[str, bool]:
    """(adoption_id, created). Same rules and same INSERT as `adopt_curriculum`.

    Deliberately the same 422 gate as that endpoint (`is_default` AND
    `owner_type = 'platform'`): a curriculum that cannot be adopted through the
    library cannot be forked through this side door either, or the two would
    disagree about what a school is allowed to own.
    """
    pkg = await conn.fetchrow(
        "SELECT curriculum_id, grade, is_default, owner_type FROM curricula "
        "WHERE curriculum_id = $1",
        source_curriculum_id,
    )
    if not pkg or not pkg["is_default"] or pkg["owner_type"] != "platform":
        raise CurriculumNotAdoptable(source_curriculum_id)

    existing = await conn.fetchval(
        "SELECT adoption_id FROM school_adopted_curricula "
        "WHERE school_id = $1 AND curriculum_id = $2",
        school_id,
        source_curriculum_id,
    )
    if existing:
        return str(existing), False

    adoption_id = await conn.fetchval(
        """
        INSERT INTO school_adopted_curricula
            (school_id, curriculum_id, grade, adopted_by, notes)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING adoption_id
        """,
        school_id,
        source_curriculum_id,
        pkg["grade"],
        teacher_id,
        "Adopted automatically when a reviewer corrected a quiz answer (#762).",
    )
    return str(adoption_id), True


async def correct_answer(
    conn,
    storage: StorageBackend,
    redis,
    *,
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    lang: str,
    stable_question_id: str,
    correct_option: str,
    confirm_fork: bool,
    teacher_id: str,
) -> dict:
    """Change WHICH option is correct for one question, in this school's copy.

    Returns {"ownership_before", "created": {adoption, fork, import},
    "override_id", "override_ids", "grade_repointed", "sets_corrected",
    "old_correct_text", "new_correct_text", "validated_at"}.

    Raises `QuestionNotInUnit` (404), `OptionNotInQuestion` (422),
    `ForkConfirmationRequired` (409) or `CurriculumNotAdoptable` (422).

    RULING — one question, several sets. A `stable_question_id` spans quiz sets
    (it hashes the stem, not the set number), so a unit can hold three BODIES
    for one question. A correction fixes the answer in EVERY set the question
    appears in. The set a student sits is chosen by the server's rotation
    (`pin_session_quiz_set`, once per attempt), so correcting only the set the
    reviewer happened to be shown would leave the same question misgraded on the
    next attempt — and "the corrected answer is what grades" could not be said
    at all. It also keeps `question_validations`' single `correct_text` snapshot
    honest, since after this the sets agree.

    RULING — language. The new version is written under the language the body
    was actually READ in (`_key_lang`), not the one requested. Requesting `fr`
    where only `_en` files exist reads English (serving falls back the same
    way), and storing that English body as a French override would be a
    translation nobody wrote. Consequence, stated rather than hidden: a school
    whose students read `fr` while the content is English-only is corrected for
    the English readers; the `fr` grading path reads the store's `_en` file and
    does not see the override. Content is English-only today.

    Everything after the reads happens in ONE transaction, so a failure cannot
    leave a school with a fork and no correction in it.
    """
    from src.school.unit_import import import_unit_overrides

    pool = _ConnAsPool(conn)

    (
        source_curriculum_id,
        owned_curriculum_id,
        has_override,
        per_set,
    ) = await _resolve_unit_quiz_sets(
        conn,
        pool,
        storage,
        redis,
        school_id=school_id,
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        lang=lang,
    )
    ownership_before = "override" if has_override else ("fork" if owned_curriculum_id else "none")

    questions = _questions_from_sets(
        per_set, source_curriculum_id=source_curriculum_id, unit_id=unit_id
    )
    matches = sorted(
        (q for q in questions if q["stable_question_id"] == stable_question_id),
        key=lambda q: q["set_number"],
    )
    if not matches:
        raise QuestionNotInUnit(stable_question_id)

    # Refuse BEFORE anything is created: a 422 that has already adopted a
    # curriculum and repointed a grade is not a refusal.
    for question in matches:
        if not any(o["option_id"] == correct_option for o in question["options"]):
            raise OptionNotInQuestion(
                f"{correct_option!r} is not an option of question "
                f"{question['question_id']!r} in set {question['set_number']}"
            )

    if ownership_before == "none" and not confirm_fork:
        raise ForkConfirmationRequired(source_curriculum_id)

    old_correct_text = _correct_option_text(matches[0]["options"], matches[0]["correct_option"])
    new_correct_text = _correct_option_text(matches[0]["options"], correct_option)

    bodies = {set_number: body for set_number, body, _key_lang, _src in per_set}
    created = {"adoption": False, "fork": False, "import": False}
    grade_repointed = False
    override_ids: list[str] = []
    sets_corrected: list[int] = []

    async with conn.transaction():
        if ownership_before != "override":
            # Take the school's own copy first. `_assert_school_owns_curriculum`
            # refuses platform ids outright, so everything below operates on the
            # FORK id and never on the id in the path.
            adoption_id, created["adoption"] = await _ensure_adoption(
                conn,
                school_id=school_id,
                source_curriculum_id=source_curriculum_id,
                teacher_id=teacher_id,
            )
            imported = await import_unit_overrides(
                conn,
                storage,
                school_id=school_id,
                adoption_id=adoption_id,
                unit_id=unit_id,
                teacher_id=teacher_id,
                lang=matches[0]["_key_lang"],
            )
            owned_curriculum_id = imported["forked_curriculum_id"]
            created["fork"] = imported["fork_created"]
            created["import"] = any(not o.skipped for o in imported["overrides"])
            grade_repointed = imported["grade_repointed"]

        for question in matches:
            set_number = question["set_number"]
            content_type = f"quiz_set_{set_number}"
            write_lang = question["_key_lang"]
            original = bodies[set_number]

            corrected = json.loads(json.dumps(original))
            targeted: set[str] = set()
            for candidate in corrected.get("questions") or []:
                if not isinstance(candidate, dict) or not candidate.get("question_id"):
                    continue
                sid = stable_question_id_of(
                    source_curriculum_id, unit_id, write_lang, candidate.get("question_text") or ""
                )
                if sid == stable_question_id:
                    candidate["correct_option"] = correct_option
                    targeted.add(candidate["question_id"])
            _verify_only_correct_option_changed(original, corrected, question_ids=targeted)

            latest = await conn.fetchrow(
                """
                SELECT override_id, version_number, bundle_id
                FROM unit_content_overrides
                WHERE curriculum_id = $1 AND unit_id = $2
                  AND lang = $3 AND content_type = $4
                ORDER BY version_number DESC
                LIMIT 1
                FOR UPDATE
                """,
                owned_curriculum_id,
                unit_id,
                write_lang,
                content_type,
            )
            override_id = await conn.fetchval(
                """
                INSERT INTO unit_content_overrides
                    (school_id, curriculum_id, unit_id, lang, content_type,
                     bundle_id, content_source, source_override_id, body,
                     last_edited_by, review_status, version_number)
                VALUES ($1, $2, $3, $4, $5,
                        $6, 'teacher_authored', $7, $8,
                        $9, 'approved', $10)
                RETURNING override_id
                """,
                school_id,
                owned_curriculum_id,
                unit_id,
                write_lang,
                content_type,
                latest["bundle_id"] if latest else None,
                latest["override_id"] if latest else None,
                corrected,
                teacher_id,
                (latest["version_number"] + 1) if latest else 1,
            )

            # `approve_unit_content`'s upsert (school/router.py), NOT
            # `revert_unit_override`'s: that one omits school_id and conflicts on
            # the wrong key (#803), so it would either fail or overwrite another
            # school's pointer.
            await conn.execute(
                """
                INSERT INTO unit_content_active_versions
                    (school_id, curriculum_id, unit_id, lang,
                     content_type, override_id, activated_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (school_id, curriculum_id, unit_id, lang, content_type)
                DO UPDATE SET override_id  = EXCLUDED.override_id,
                              activated_by = EXCLUDED.activated_by,
                              activated_at = now()
                """,
                school_id,
                owned_curriculum_id,
                unit_id,
                write_lang,
                content_type,
                override_id,
                teacher_id,
            )
            override_ids.append(str(override_id))
            sets_corrected.append(set_number)

        # The correction re-validates, by the reviewer who made it (design §2).
        # Inside the transaction: a tick vouching for an answer that was rolled
        # back is worse than no tick.
        validation = await _upsert_validation(
            conn,
            school_id=school_id,
            stable_question_id=stable_question_id,
            correct_text=new_correct_text,
            teacher_id=teacher_id,
        )

    # AFTER the commit, and it is not optional: `get_active_override` caches the
    # previous body — or a JSON-null miss sentinel — for an hour, so without
    # this the correction reaches nobody until the TTL expires. Spec decision 3
    # is "a correction is live immediately" (#806, fixed for the approve
    # endpoint in school/router.py as well).
    for set_number in sets_corrected:
        question = next(q for q in matches if q["set_number"] == set_number)
        await redis.delete(
            override_key(
                school_id,
                owned_curriculum_id,
                unit_id,
                question["_key_lang"],
                f"quiz_set_{set_number}",
            )
        )

    log.info(
        "answer_review_corrected",
        school_id=school_id,
        curriculum_id=source_curriculum_id,
        owned_curriculum_id=owned_curriculum_id,
        unit_id=unit_id,
        stable_question_id=stable_question_id,
        ownership_before=ownership_before,
        sets_corrected=sets_corrected,
        created=created,
        grade_repointed=grade_repointed,
    )

    return {
        "ownership_before": ownership_before,
        "created": created,
        # The lowest corrected set's version, chosen deterministically for the
        # same reason `validate_answer` snapshots the lowest set's answer.
        "override_id": override_ids[0],
        "override_ids": override_ids,
        "owned_curriculum_id": owned_curriculum_id,
        "grade_repointed": grade_repointed,
        "sets_corrected": sets_corrected,
        "old_correct_text": old_correct_text,
        "new_correct_text": new_correct_text,
        "validated_at": validation["validated_at"],
    }
