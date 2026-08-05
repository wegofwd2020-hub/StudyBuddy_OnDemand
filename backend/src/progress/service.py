"""
backend/src/progress/service.py

Progress tracking business logic.

Key rules:
- attempt_number computed server-side (COUNT(*) + 1); never trusted from client.
- Progress answer writes are fire-and-forget (Celery task); 200 returned before DB write.
- Session end updates the session record synchronously (needed for the response score),
  then fires Celery tasks for streak update and view refresh.
- QUIZ_PASS_THRESHOLD = 60 % (score / total_questions >= 0.6).
"""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.core.cache_keys import (
    quiz_session_set_key,
    quiz_set_key,
)
from src.core.subjects import display_subject, resolve_subject_labels
from src.utils.logger import get_logger

log = get_logger("progress")

QUIZ_PASS_THRESHOLD = 0.60

# A quiz session is short-lived; the tally only needs to outlive the attempt.
_TALLY_TTL = 6 * 3600  # 6 hours


# ── Server-side grading state ─────────────────────────────────────────────────


async def resolve_session_quiz_set(
    redis,
    session_id: str,
    student_id: str,
    unit_id: str,
) -> int:
    """
    Return the quiz set (1-3) this session is being graded against.

    Pinned per session on first use: the per-unit rotation pointer
    (`quiz_set:{student}:{unit}`, written by get_next_quiz_set when the quiz was
    served) advances every time a quiz is fetched, so reading it fresh for every
    answer could grade later answers against a different set's key. Pin it once,
    then reuse.

    Falls back to set 1 if the rotation pointer has expired — the student is
    mid-quiz and we still have to grade them against something; set 1 is what the
    serving endpoint hands out when the pointer is absent.
    """
    pinned = await redis.get(quiz_session_set_key(session_id))
    if pinned is not None:
        try:
            return int(pinned)
        except (ValueError, TypeError):
            pass  # corrupt — re-pin below

    served = await redis.get(quiz_set_key(student_id, unit_id))
    try:
        set_number = int(served)
    except (ValueError, TypeError):
        log.warning(
            "quiz_set_pointer_missing_defaulting_to_1",
            extra={"session_id": session_id, "unit_id": unit_id},
        )
        set_number = 1

    if not 1 <= set_number <= 3:
        set_number = 1

    await redis.set(quiz_session_set_key(session_id), str(set_number), ex=_TALLY_TTL)
    return set_number


async def tally_answer(redis, session_id: str, question_id: str, correct: bool) -> None:
    """
    Record one graded answer against the session's per-question tally.

    Stored as a Redis HASH field (question_id → "1"/"0") rather than a counter so
    the write is idempotent: answering the same question again — which the
    skip-and-return UI (#532) makes possible — overwrites its verdict instead of
    incrementing a blind total. end_session reads this back without waiting on the
    fire-and-forget DB write (perf rule #4).
    """
    key = quiz_answers_key(session_id)
    await redis.hset(key, question_id, "1" if correct else "0")
    await redis.expire(key, _TALLY_TTL)


async def read_tally(redis, session_id: str) -> int | None:
    """
    Server-graded correct count for the session, or None if no tally exists.

    Counts the "1" fields in the per-question hash, so a question re-answered any
    number of times contributes at most once and only its latest verdict counts.
    An absent key (no answers graded, or the hash expired) returns None so the
    caller can fall back to the persisted answers.
    """
    values = await redis.hvals(quiz_answers_key(session_id))
    if not values:
        return None
    return sum(1 for v in values if (v.decode() if isinstance(v, bytes) else v) == "1")


async def count_correct_answers(conn: asyncpg.Connection, session_id: str) -> int:
    """
    Fallback score source: count graded-correct answers already persisted.

    Only used when the Redis tally is gone (restart / TTL). Because answers are
    appended (a new row per submission, no upsert) the same question can have
    several rows once revisiting is allowed, so we take only the LATEST row per
    question — matching the Redis hash's "last verdict wins" — and count the ones
    that are correct. May undercount if the fire-and-forget writes are still in
    flight, which is exactly why the Redis tally is preferred.
    """
    return (
        await conn.fetchval(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (question_id) correct
                FROM progress_answers
                WHERE session_id = $1
                ORDER BY question_id, recorded_at DESC
            ) latest
            WHERE correct IS TRUE
            """,
            session_id,
        )
        or 0
    )


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


async def compute_attempt_number(
    conn: asyncpg.Connection, student_id: str, unit_id: str, curriculum_id: str
) -> int:
    """Return COUNT of prior completed sessions + 1 for this student × unit."""
    row = await conn.fetchrow(
        """
        SELECT COUNT(*) AS cnt
        FROM progress_sessions
        WHERE student_id = $1 AND unit_id = $2 AND curriculum_id = $3
          AND completed = TRUE
        """,
        student_id,
        unit_id,
        curriculum_id,
    )
    return (row["cnt"] or 0) + 1


async def create_session(
    conn: asyncpg.Connection,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
) -> dict:
    """
    Open a new progress session.  Looks up grade + subject from curriculum_units.
    Returns the created session row.
    """
    # Fetch subject from curriculum_units and grade from curricula
    unit_row = await conn.fetchrow(
        "SELECT cu.subject, c.grade FROM curriculum_units cu"
        " LEFT JOIN curricula c ON c.curriculum_id = cu.curriculum_id"
        " WHERE cu.unit_id = $1 AND cu.curriculum_id = $2",
        unit_id,
        curriculum_id,
    )
    if unit_row is None:
        grade = 0
        subject = "unknown"
    else:
        grade = unit_row["grade"] or 0
        subject = unit_row["subject"] or "unknown"

    attempt_number = await compute_attempt_number(conn, student_id, unit_id, curriculum_id)

    row = await conn.fetchrow(
        """
        INSERT INTO progress_sessions
            (student_id, unit_id, curriculum_id, grade, subject, attempt_number)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING session_id, started_at, attempt_number
        """,
        student_id,
        unit_id,
        curriculum_id,
        grade,
        subject,
        attempt_number,
    )

    log.info(
        "session_created",
        student_id=student_id,
        unit_id=unit_id,
        session_id=str(row["session_id"]),
        attempt=attempt_number,
    )

    return {
        "session_id": str(row["session_id"]),
        "unit_id": unit_id,
        "curriculum_id": curriculum_id,
        "attempt_number": row["attempt_number"],
        "started_at": row["started_at"].isoformat(),
    }


async def verify_session_owner(
    conn: asyncpg.Connection,
    session_id: str,
    student_id: str,
) -> asyncpg.Record:
    """
    Fetch the session and verify the student owns it.
    Raises ValueError if not found or not owned.
    """
    row = await conn.fetchrow(
        "SELECT * FROM progress_sessions WHERE session_id = $1",
        session_id,
    )
    if row is None:
        raise LookupError("session_not_found")
    if str(row["student_id"]) != str(student_id):
        raise PermissionError("session_ownership_violation")
    return row


async def record_answer_sync(
    conn: asyncpg.Connection,
    session_id: str,
    question_id: str,
    student_answer: int,
    correct_answer: int,
    correct: bool,
    ms_taken: int,
    event_id: str | None,
) -> dict:
    """
    Write an answer row synchronously (called from the fire-and-forget Celery task).
    Uses ON CONFLICT DO NOTHING on event_id for offline deduplication.
    """
    if event_id:
        row = await conn.fetchrow(
            """
            INSERT INTO progress_answers
                (session_id, event_id, question_id, student_answer, correct_answer, correct, ms_taken)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING answer_id, correct
            """,
            session_id,
            event_id,
            question_id,
            student_answer,
            correct_answer,
            correct,
            ms_taken,
        )
    else:
        row = await conn.fetchrow(
            """
            INSERT INTO progress_answers
                (session_id, question_id, student_answer, correct_answer, correct, ms_taken)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING answer_id, correct
            """,
            session_id,
            question_id,
            student_answer,
            correct_answer,
            correct,
            ms_taken,
        )

    if row is None:
        # Duplicate event_id — idempotent, return a stub
        return {"answer_id": "", "correct": correct}

    return {"answer_id": str(row["answer_id"]), "correct": row["correct"]}


async def end_session(
    conn: asyncpg.Connection,
    session_id: str,
    score: int,
    total_questions: int,
) -> dict:
    """
    Mark a session as completed.  Computes passed flag.

    Score and total are clamped server-side so a malformed client payload (or a
    quiz whose question count differs from the supplied total) can never persist
    an impossible result such as 8/5 = 160%.  See feedback issue #460.
    Returns the updated session.
    """
    total_questions = max(1, total_questions)
    # A student can never score more than the number of questions, nor below zero.
    score = max(0, min(score, total_questions))
    passed = (score / total_questions) >= QUIZ_PASS_THRESHOLD

    # Assign the attempt number at COMPLETION, not at session start (#465).
    # attempt_number was computed in create_session as "completed sessions + 1",
    # but sessions are opened eagerly (one per quiz-page load), so several
    # never-completed sessions for a unit all received the same number — Progress
    # History then showed duplicate "Attempt #2" cards. Numbering completed
    # sessions in completion order makes each finished attempt uniquely sequential.
    row = await conn.fetchrow(
        """
        UPDATE progress_sessions ps
        SET score           = $1,
            total_questions = $2,
            completed       = TRUE,
            passed          = $3,
            ended_at        = NOW(),
            attempt_number  = (
                SELECT COUNT(*) + 1
                FROM progress_sessions prior
                WHERE prior.student_id   = ps.student_id
                  AND prior.unit_id      = ps.unit_id
                  AND prior.curriculum_id = ps.curriculum_id
                  AND prior.completed     = TRUE
                  AND prior.session_id <> ps.session_id
            )
        WHERE ps.session_id = $4
        RETURNING session_id, score, total_questions, passed, attempt_number, ended_at
        """,
        score,
        total_questions,
        passed,
        session_id,
    )

    if row is None:
        raise LookupError("session_not_found")

    log.info(
        "session_ended",
        session_id=session_id,
        score=score,
        total_questions=total_questions,
        passed=passed,
    )

    return {
        "session_id": str(row["session_id"]),
        "score": row["score"],
        "total_questions": row["total_questions"],
        "passed": row["passed"],
        "attempt_number": row["attempt_number"],
        "ended_at": row["ended_at"].isoformat(),
    }


async def get_raw_history(
    conn: asyncpg.Connection,
    student_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Return all sessions with answers for a student, newest first.
    """
    sessions = await conn.fetch(
        """
        SELECT session_id, unit_id, curriculum_id, grade, subject,
               started_at, ended_at, score, total_questions,
               completed, passed, attempt_number
        FROM progress_sessions
        WHERE student_id = $1
        ORDER BY started_at DESC
        LIMIT $2 OFFSET $3
        """,
        student_id,
        limit,
        offset,
    )

    total_row = await conn.fetchrow(
        "SELECT COUNT(*) AS cnt FROM progress_sessions WHERE student_id = $1",
        student_id,
    )

    # Resolve human-readable subject names (issue #462) instead of surfacing the
    # raw code / "unknown" stored on the session row.
    subject_labels = await resolve_subject_labels(conn, [s["unit_id"] for s in sessions])

    result_sessions = []
    for s in sessions:
        answers = await conn.fetch(
            """
            SELECT answer_id, question_id, student_answer, correct_answer, correct, ms_taken, recorded_at
            FROM progress_answers
            WHERE session_id = $1
            ORDER BY recorded_at
            """,
            s["session_id"],
        )
        result_sessions.append(
            {
                "session_id": str(s["session_id"]),
                "unit_id": s["unit_id"],
                "curriculum_id": s["curriculum_id"],
                "grade": s["grade"],
                "subject": display_subject(subject_labels, s["unit_id"], s["subject"]),
                "started_at": s["started_at"].isoformat(),
                "ended_at": s["ended_at"].isoformat() if s["ended_at"] else None,
                "score": s["score"],
                "total_questions": s["total_questions"],
                "completed": s["completed"],
                "passed": s["passed"],
                "attempt_number": s["attempt_number"],
                "answers": [
                    {
                        "answer_id": str(a["answer_id"]),
                        "question_id": a["question_id"],
                        "student_answer": a["student_answer"],
                        "correct_answer": a["correct_answer"],
                        "correct": a["correct"],
                        "ms_taken": a["ms_taken"],
                        "recorded_at": a["recorded_at"].isoformat(),
                    }
                    for a in answers
                ],
            }
        )

    return {
        "student_id": student_id,
        "sessions": result_sessions,
        "total": total_row["cnt"],
    }
