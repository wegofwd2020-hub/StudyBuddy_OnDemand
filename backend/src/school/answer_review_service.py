"""
backend/src/school/answer_review_service.py

Quiz answer review (#762) — list every quiz question of a unit for a school
reviewer, with its correct answer, this school's validation state, and how
many of this school's own students flagged it.

Resolution mirrors serving/grading EXACTLY (`resolve_quiz_answer_key`,
content/service.py:810-841) so a reviewer always reviews what is actually
served, and a `stable_question_id` computed here matches the one already
recorded against `progress_answers` / `feedback` for the same question:

  - an active override answers a set  -> that set's questions are identified
    using the curriculum_id the override itself is keyed by (the school's own
    fork id) -- the grader does the same when an override wins;
  - no override for a set             -> read the content store under the
    resolved OOB source curriculum, and identify those questions using THAT
    (swapped) id -- the grader does the same when it falls through to the
    store.

Deliberately takes a single `conn` (acquired via `get_db(request)` in the
router, not `Depends(get_db)` -- see Epic 15's bug) rather than a pool. The
shared content-service helpers (`get_active_override`, `resolve_content_curriculum`,
`get_fork_source_curriculum`) all take a `pool` because they acquire their own
connection and stamp a specific school's RLS context onto it. `_ConnAsPool`
adapts the single connection to that `pool.acquire()` shape so this module
reuses those helpers verbatim instead of re-deriving their SQL.
"""

from __future__ import annotations

from src.content.service import (
    get_active_override,
    get_content_file,
    resolve_content_curriculum,
)
from src.core.question_identity import stable_question_id
from src.core.storage import StorageBackend

_QUIZ_SET_NUMBERS = (1, 2, 3)


class _ConnAsPool:
    """Adapts a single asyncpg Connection to `pool.acquire()`.

    `pool.acquire()` is called (not awaited) and the result used as an async
    context manager -- exactly what asyncpg's real Pool.acquire() returns.
    Returning `self` from both `acquire()` and `__aenter__` satisfies that
    shape without a second connection: the caller already owns this one via
    `get_db(request)`, and the shared helpers only ever read.
    """

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc_info):
        return False


def _correct_option_text(options: list[dict], correct_option: str | None) -> str:
    """The correct option's normalised text -- same normalisation
    `_parse_quiz_answer_key` uses (content/service.py:718), so a staleness
    comparison against a stored `question_validations.correct_text` means
    what it says."""
    for option in options:
        if option.get("option_id") == correct_option:
            return " ".join((option.get("text") or "").split())
    return ""


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

    Returns {"ownership": "none|fork|override", "serving_curriculum_id": str,
    "questions": [...]} -- see AnswerReviewListResponse for the question shape.
    """
    pool = _ConnAsPool(conn)

    # ── 1. Is curriculum_id a fork this school owns? ────────────────────────
    row = await conn.fetchrow(
        "SELECT owner_type, school_id, source_curriculum_id FROM curricula "
        "WHERE curriculum_id = $1",
        curriculum_id,
    )
    fork_curriculum_id: str | None = None
    if row and row["owner_type"] == "school" and str(row["school_id"]) == str(school_id):
        fork_curriculum_id = curriculum_id

    if fork_curriculum_id:
        source_curriculum_id, _subject = await resolve_content_curriculum(
            unit_id, fork_curriculum_id, school_id, pool
        )
    else:
        source_curriculum_id = curriculum_id

    # ── 2. Read each set: override first, else the store under the source ──
    has_override = False
    per_set: list[tuple[int, dict, str]] = []  # (set_number, body, stable_cid)

    for set_number in _QUIZ_SET_NUMBERS:
        content_type = f"quiz_set_{set_number}"
        override_body: dict | None = None
        if fork_curriculum_id:
            override_body = await get_active_override(
                school_id, fork_curriculum_id, unit_id, lang, content_type, pool, redis
            )

        if override_body is not None:
            has_override = True
            per_set.append((set_number, override_body, fork_curriculum_id))
            continue

        body = None
        for filename in (f"{content_type}_{lang}.json", f"{content_type}_en.json"):
            try:
                body = await get_content_file(
                    source_curriculum_id, unit_id, filename, redis, storage
                )
                break
            except FileNotFoundError:
                continue
        if body is None:
            continue  # this set doesn't exist for this unit -- not every unit has 3
        per_set.append((set_number, body, source_curriculum_id))

    ownership = "override" if has_override else ("fork" if fork_curriculum_id else "none")

    # ── 3. Build the question list + collect stable ids for the joins ──────
    questions: list[dict] = []
    stable_ids: list[str] = []
    for set_number, body, stable_cid in per_set:
        for question in body.get("questions", []):
            qid = question.get("question_id")
            text = question.get("question_text") or ""
            options = question.get("options", [])
            correct_option = question.get("correct_option")
            sid = stable_question_id(stable_cid, unit_id, lang, text)
            stable_ids.append(sid)
            questions.append(
                {
                    "stable_question_id": sid,
                    "set_number": set_number,
                    "question_id": qid,
                    "question_text": text,
                    "options": [
                        {"option_id": o.get("option_id"), "text": o.get("text") or ""}
                        for o in options
                    ],
                    "correct_option": correct_option,
                    "_correct_text": _correct_option_text(options, correct_option),
                    "flag_count": 0,
                    "validated": None,
                }
            )

    if not stable_ids:
        return {
            "ownership": ownership,
            "serving_curriculum_id": source_curriculum_id,
            "questions": [],
        }

    # ── 4. Left-join this school's validations ──────────────────────────────
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

    # ── 5. Left-join flag counts, scoped to THIS school's own students ─────
    flag_rows = await conn.fetch(
        """
        SELECT f.stable_question_id, COUNT(*) AS flags
        FROM feedback f
        JOIN school_enrolments se ON se.student_id = f.student_id AND se.school_id = $1
        WHERE f.stable_question_id = ANY($2::text[])
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

    return {
        "ownership": ownership,
        "serving_curriculum_id": source_curriculum_id,
        "questions": questions,
    }
