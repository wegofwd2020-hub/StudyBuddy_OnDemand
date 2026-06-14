"""
tests/test_feedback_464.py

Regression test for feedback #464 — Unit Progress "Time".

The per-unit lesson-time aggregation joined lesson_views directly to
progress_sessions, so each lesson view was multiplied by the number of quiz
sessions for that unit and SUM(duration) over-counted (one 5-minute view with
two quiz attempts reported 10m). Pre-aggregating lesson_views per unit fixes it.

(The "always 0m" reported on the demo is a separate instrumentation issue —
lesson_views.duration_s is NULL when the fire-and-forget lesson-end write never
lands. These tests cover the aggregation correctness, which is what the backend
controls; the third case documents the NULL-duration behaviour.)
"""

from __future__ import annotations

import uuid

import pytest

from src.analytics.service import get_student_metrics


async def _student(db_conn, sid: uuid.UUID) -> None:
    await db_conn.execute(
        "INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status) "
        "VALUES ($1, $2, $3, $4, 8, 'en', 'active')",
        sid,
        f"auth0|test-{sid.hex[:18]}",
        "Time Tester",
        f"time-{sid.hex[:8]}@test.invalid",
    )


async def _view(db_conn, sid: uuid.UUID, unit_id: str, duration_s: int | None) -> None:
    await db_conn.execute(
        "INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s, ended_at) "
        "VALUES ($1, $2, 'default-2026-g8', $3, NOW())",
        sid,
        unit_id,
        duration_s,
    )


async def _session(db_conn, sid: uuid.UUID, unit_id: str, attempt: int) -> None:
    await db_conn.execute(
        "INSERT INTO progress_sessions "
        "(student_id, unit_id, curriculum_id, grade, subject, attempt_number, score, total_questions, completed, passed) "
        "VALUES ($1, $2, 'default-2026-g8', 8, 'G8-MATH', $3, 6, 8, TRUE, TRUE)",
        sid,
        unit_id,
        attempt,
    )


@pytest.mark.asyncio
async def test_per_unit_time_not_multiplied_by_session_count(db_conn):
    """One 300s lesson view + two quiz attempts → 5m, not 10m (no double-count)."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _view(db_conn, sid, "G8-MATH-001", 300)
    await _session(db_conn, sid, "G8-MATH-001", attempt=1)
    await _session(db_conn, sid, "G8-MATH-001", attempt=2)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-001")
    assert unit["total_time_minutes"] == 5.0
    assert unit["lessons_viewed"] == 1


@pytest.mark.asyncio
async def test_per_unit_time_sums_multiple_views(db_conn):
    """Two distinct views (180s + 120s) over one unit → 5m total."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _view(db_conn, sid, "G8-MATH-002", 180)
    await _view(db_conn, sid, "G8-MATH-002", 120)
    await _session(db_conn, sid, "G8-MATH-002", attempt=1)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-002")
    assert unit["total_time_minutes"] == 5.0
    assert unit["lessons_viewed"] == 2


@pytest.mark.asyncio
async def test_per_unit_time_zero_when_duration_unrecorded(db_conn):
    """A lesson view whose duration was never written (NULL) contributes 0m."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _view(db_conn, sid, "G8-MATH-003", None)
    await _session(db_conn, sid, "G8-MATH-003", attempt=1)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-003")
    assert unit["total_time_minutes"] == 0.0
