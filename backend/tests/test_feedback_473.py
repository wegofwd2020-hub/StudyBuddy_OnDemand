"""
tests/test_feedback_473.py

Integration tests for the student Subject Breakdown chart data (#473):

1. Subjects resolve to real names derived from the unit_id prefix when the
   stored subject is the "unknown" sentinel and no curriculum_units row exists,
   so the chart no longer collapses every session into one "Unknown" bar.
2. The `period` query param (previously ignored) actually scopes the breakdown.
"""

from __future__ import annotations

import uuid

import pytest

from tests.helpers.token_factory import make_student_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _insert_student(pool, student_id: str) -> None:
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|fb473-{student_id[:8]}",
        f"Student {student_id[:6]}",
        f"fb473-{student_id[:6]}@test.invalid",
    )


async def _insert_session(pool, student_id: str, unit_id: str, days_ago: int) -> None:
    # subject stored as the "unknown" sentinel — mirrors a session created when
    # the unit could not be resolved; the fix derives the subject from unit_id.
    await pool.execute(
        """
        INSERT INTO progress_sessions
            (student_id, unit_id, curriculum_id, subject, grade,
             attempt_number, score, total_questions, completed, passed, started_at)
        VALUES ($1, $2, 'default-2026-g8', 'unknown', 8,
                1, 80, 10, true, true, NOW() - make_interval(days => $3))
        """,
        uuid.UUID(student_id),
        unit_id,
        days_ago,
    )


@pytest.mark.asyncio
async def test_subject_breakdown_resolves_names_and_respects_period(client, db_conn):
    student_id = str(uuid.uuid4())
    token = make_student_token(student_id=student_id, grade=8)
    pool = client._transport.app.state.pool

    await _insert_student(pool, student_id)
    await _insert_session(pool, student_id, "G8-SCI-001", days_ago=1)  # recent
    await _insert_session(pool, student_id, "G8-MATH-001", days_ago=20)  # older

    # period=all → both sessions; subjects resolved from unit_id, never "Unknown".
    r = await client.get("/api/v1/analytics/student/stats?period=all", headers=_auth(token))
    assert r.status_code == 200, r.text
    subjects = {b["subject"] for b in r.json()["subject_breakdown"]}
    assert subjects == {"Science", "Mathematics"}
    assert "Unknown" not in subjects

    # period=7d → only the recent (1-day-old) Science session is in scope.
    r = await client.get("/api/v1/analytics/student/stats?period=7d", headers=_auth(token))
    assert r.status_code == 200, r.text
    subjects_7d = {b["subject"] for b in r.json()["subject_breakdown"]}
    assert subjects_7d == {"Science"}
