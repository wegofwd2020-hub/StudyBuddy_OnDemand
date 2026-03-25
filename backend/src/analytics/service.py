"""
backend/src/analytics/service.py

Lesson analytics business logic.

lesson_views table lifecycle:
  start_lesson_view() — INSERT row, returns view_id (called by mobile on lesson open)
  end_lesson_view()   — UPDATE row with duration_s, audio_played, experiment_viewed, ended_at

Ownership:
  verify_view_owner() — raises LookupError/PermissionError (same pattern as progress sessions)
"""

from __future__ import annotations

import asyncpg

from src.utils.logger import get_logger

log = get_logger("analytics")


async def start_lesson_view(
    conn: asyncpg.Connection,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
) -> dict:
    """
    Open a new lesson view row.

    Returns {view_id}.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO lesson_views (student_id, unit_id, curriculum_id)
        VALUES ($1, $2, $3)
        RETURNING view_id::text
        """,
        student_id,
        unit_id,
        curriculum_id,
    )
    return {"view_id": row["view_id"]}


async def verify_view_owner(
    conn: asyncpg.Connection,
    view_id: str,
    student_id: str,
) -> dict:
    """
    Check that the lesson view exists and belongs to this student.

    Returns the row on success.
    Raises LookupError if not found, PermissionError if owned by another student.
    """
    row = await conn.fetchrow(
        "SELECT student_id::text, ended_at FROM lesson_views WHERE view_id = $1",
        view_id,
    )
    if row is None:
        raise LookupError(f"lesson view {view_id} not found")
    if str(row["student_id"]) != str(student_id):
        raise PermissionError("view belongs to another student")
    return dict(row)


async def end_lesson_view(
    conn: asyncpg.Connection,
    view_id: str,
    duration_s: int,
    audio_played: bool,
    experiment_viewed: bool,
) -> dict:
    """
    Close a lesson view row.

    Sets ended_at = NOW() and records duration/flags.
    Returns {view_id, duration_s}.
    """
    row = await conn.fetchrow(
        """
        UPDATE lesson_views
        SET ended_at          = NOW(),
            duration_s        = $2,
            audio_played      = $3,
            experiment_viewed = $4
        WHERE view_id = $1
        RETURNING view_id::text, duration_s
        """,
        view_id,
        duration_s,
        audio_played,
        experiment_viewed,
    )
    return {"view_id": row["view_id"], "duration_s": row["duration_s"]}
