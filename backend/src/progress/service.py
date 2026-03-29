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

from src.utils.logger import get_logger

log = get_logger("progress")

QUIZ_PASS_THRESHOLD = 0.60


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
    Returns the updated session.
    """
    passed = (score / total_questions) >= QUIZ_PASS_THRESHOLD if total_questions > 0 else False

    row = await conn.fetchrow(
        """
        UPDATE progress_sessions
        SET score           = $1,
            total_questions = $2,
            completed       = TRUE,
            passed          = $3,
            ended_at        = NOW()
        WHERE session_id = $4
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
                "subject": s["subject"],
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
