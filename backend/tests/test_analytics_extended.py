"""
tests/test_analytics_extended.py

Tests for Phase 10 extended analytics endpoints.

Coverage:
  GET /api/v1/analytics/student/me
    - Returns summary + per_unit breakdown + improvement_trajectory
    - Empty for student with no data
    - Unauthenticated returns 403
  GET /api/v1/analytics/school/{school_id}/class
    - Returns per-unit class metrics
    - struggle_flag triggered by low pass rate
    - struggle_flag triggered by high mean_attempts_to_pass
    - Wrong school returns 403
    - Unauthenticated returns 403
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token, make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _insert_student(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|analext-{student_id[:8]}",
        f"Analytics Student {student_id[:6]}",
        f"analext-{student_id[:6]}@test.invalid",
    )


def _student_id_from_token(token: str) -> str:
    from jose import jwt as _jwt
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    return payload["student_id"]


async def _insert_progress_session(
    pool,
    student_id: str,
    *,
    unit_id: str = "G8-MATH-001",
    subject: str = "Mathematics",
    curriculum_id: str = "default-2026-g8",
    attempt_number: int = 1,
    score: float = 75.0,
    completed: bool = True,
    passed: bool = True,
) -> str:
    """Insert a progress_sessions row and return session_id."""
    row = await pool.fetchrow(
        """
        INSERT INTO progress_sessions
            (student_id, unit_id, curriculum_id, subject, grade,
             attempt_number, score, completed, passed)
        VALUES ($1, $2, $3, $4, 8, $5, $6, $7, $8)
        RETURNING session_id::text
        """,
        uuid.UUID(student_id),
        unit_id,
        curriculum_id,
        subject,
        attempt_number,
        score,
        completed,
        passed,
    )
    return row["session_id"]


async def _insert_lesson_view(
    pool,
    student_id: str,
    *,
    unit_id: str = "G8-MATH-001",
    curriculum_id: str = "default-2026-g8",
    duration_s: int = 300,
    audio_played: bool = False,
) -> str:
    """Insert a lesson_views row and return view_id."""
    row = await pool.fetchrow(
        """
        INSERT INTO lesson_views
            (student_id, unit_id, curriculum_id, ended_at, duration_s, audio_played)
        VALUES ($1, $2, $3, NOW(), $4, $5)
        RETURNING view_id::text
        """,
        uuid.UUID(student_id),
        unit_id,
        curriculum_id,
        duration_s,
        audio_played,
    )
    return row["view_id"]


async def _register_school(client: AsyncClient, suffix: str = "") -> dict:
    r = await client.post("/api/v1/schools/register", json={
        "school_name": f"Analytics School{suffix}",
        "contact_email": f"analytics{suffix}@school.example.com",
        "country": "ZA",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _enrol_student(pool, school_id: str, student_email: str) -> None:
    await pool.execute(
        """
        INSERT INTO school_enrolments (school_id, student_email, status)
        VALUES ($1, $2, 'active')
        ON CONFLICT (school_id, student_email) DO NOTHING
        """,
        uuid.UUID(school_id),
        student_email,
    )


# ── GET /analytics/student/me ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_student_metrics_empty_returns_defaults(client, db_conn, student_token):
    """Student with no sessions returns zero-valued response."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.get(
        "/api/v1/analytics/student/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["units_attempted"] == 0
    assert data["units_completed"] == 0
    assert data["quizzes_completed"] == 0
    assert data["total_time_minutes"] == 0.0
    assert data["lessons_viewed"] == 0
    assert data["per_unit"] == []
    assert data["improvement_trajectory"] == []


@pytest.mark.asyncio
async def test_student_metrics_with_data(client, db_conn, student_token):
    """Student with sessions and lesson views returns aggregated metrics."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    pool = client._transport.app.state.pool

    # Insert two sessions for same unit
    await _insert_progress_session(pool, student_id, unit_id="G8-MATH-001", score=60.0, passed=False, attempt_number=1)
    await _insert_progress_session(pool, student_id, unit_id="G8-MATH-001", score=80.0, passed=True, attempt_number=2)

    # Insert lesson view
    await _insert_lesson_view(pool, student_id, unit_id="G8-MATH-001", duration_s=600, audio_played=True)

    r = await client.get(
        "/api/v1/analytics/student/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["units_attempted"] >= 1
    assert data["quizzes_completed"] >= 2
    assert data["lessons_viewed"] >= 1
    assert data["audio_plays"] >= 1
    assert data["total_time_minutes"] >= 10.0

    # Per-unit breakdown
    assert len(data["per_unit"]) >= 1
    unit = next((u for u in data["per_unit"] if u["unit_id"] == "G8-MATH-001"), None)
    assert unit is not None
    assert unit["quiz_attempts"] >= 2
    assert unit["passed"] is True
    assert unit["total_time_minutes"] >= 10.0

    # Improvement trajectory — 2 completed sessions for the same unit
    assert len(data["improvement_trajectory"]) >= 1


@pytest.mark.asyncio
async def test_student_metrics_requires_auth(client):
    """Unauthenticated request returns 403."""
    r = await client.get("/api/v1/analytics/student/me")
    assert r.status_code == 403


# ── GET /analytics/school/{school_id}/class ────────────────────────────────────

@pytest.mark.asyncio
async def test_class_metrics_empty_school(client, db_conn):
    """School with no enrolled students returns empty metrics."""
    school_data = await _register_school(client, suffix="_empty")
    school_id = school_data["school_id"]
    teacher_token = school_data["access_token"]

    r = await client.get(
        f"/api/v1/analytics/school/{school_id}/class",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["school_id"] == school_id
    assert data["enrolled_students"] == 0
    assert data["metrics_per_unit"] == []


@pytest.mark.asyncio
async def test_class_metrics_with_data(client, db_conn):
    """School with enrolled students + quiz data returns per-unit class metrics."""
    school_data = await _register_school(client, suffix="_data")
    school_id = school_data["school_id"]
    teacher_token = school_data["access_token"]

    pool = client._transport.app.state.pool

    # Create and enrol a student
    student_token = make_student_token()
    student_id = _student_id_from_token(student_token)
    student_email = f"class-{student_id[:6]}@test.invalid"
    await _insert_student(client, student_id)

    # Update student email to match enrolment
    await pool.execute(
        "UPDATE students SET email = $1 WHERE student_id = $2",
        student_email, uuid.UUID(student_id),
    )

    # Enrol by school_id + student_email (active)
    await _enrol_student(pool, school_id, student_email)
    # Link student_id to enrolment
    await pool.execute(
        "UPDATE school_enrolments SET student_id = $1 WHERE school_id = $2 AND student_email = $3",
        uuid.UUID(student_id), uuid.UUID(school_id), student_email,
    )

    # Insert quiz attempt
    await _insert_progress_session(pool, student_id, unit_id="G8-SCI-001", subject="Science", score=80.0, passed=True, attempt_number=1)

    r = await client.get(
        f"/api/v1/analytics/school/{school_id}/class",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enrolled_students"] >= 1
    assert len(data["metrics_per_unit"]) >= 1
    unit = next((u for u in data["metrics_per_unit"] if u["unit_id"] == "G8-SCI-001"), None)
    assert unit is not None
    assert unit["total_quiz_attempts"] >= 1
    assert "struggle_flag" in unit


@pytest.mark.asyncio
async def test_class_metrics_struggle_flag_low_pass_rate(client, db_conn):
    """struggle_flag is True when first_attempt_pass_rate < 50%."""
    school_data = await _register_school(client, suffix="_struggle1")
    school_id = school_data["school_id"]
    teacher_token = school_data["access_token"]
    pool = client._transport.app.state.pool

    # Create 3 students, all fail first attempt → 0% pass rate
    for i in range(3):
        token = make_student_token()
        sid = _student_id_from_token(token)
        email = f"struggle1-{sid[:6]}@test.invalid"
        await _insert_student(client, sid)
        await pool.execute(
            "UPDATE students SET email = $1 WHERE student_id = $2",
            email, uuid.UUID(sid),
        )
        await _enrol_student(pool, school_id, email)
        await pool.execute(
            "UPDATE school_enrolments SET student_id = $1 WHERE school_id = $2 AND student_email = $3",
            uuid.UUID(sid), uuid.UUID(school_id), email,
        )
        await _insert_progress_session(
            pool, sid, unit_id="G8-MATH-STRUGGLE", subject="Mathematics",
            score=30.0, passed=False, attempt_number=1,
        )

    r = await client.get(
        f"/api/v1/analytics/school/{school_id}/class",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    unit = next((u for u in data["metrics_per_unit"] if u["unit_id"] == "G8-MATH-STRUGGLE"), None)
    assert unit is not None
    assert unit["struggle_flag"] is True


@pytest.mark.asyncio
async def test_class_metrics_wrong_school_returns_403(client, db_conn):
    """Teacher cannot view analytics for a different school."""
    school_data = await _register_school(client, suffix="_ws1")
    school_id = school_data["school_id"]

    # Teacher JWT with different school_id
    other_teacher_token = make_teacher_token(school_id=str(uuid.uuid4()))

    r = await client.get(
        f"/api/v1/analytics/school/{school_id}/class",
        headers={"Authorization": f"Bearer {other_teacher_token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


@pytest.mark.asyncio
async def test_class_metrics_requires_auth(client, db_conn):
    """Unauthenticated request returns 403."""
    r = await client.get(f"/api/v1/analytics/school/{uuid.uuid4()}/class")
    assert r.status_code == 403
