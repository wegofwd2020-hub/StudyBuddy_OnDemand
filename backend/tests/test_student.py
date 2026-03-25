"""
tests/test_student.py

Tests for student aggregate endpoints.

Coverage:
  - GET /student/dashboard  — returns correct structure; uses Redis cache
  - GET /student/progress   — returns curriculum map structure
  - GET /student/stats      — returns stats for valid periods; rejects invalid period
  - All endpoints require valid student JWT
  - Teacher JWT rejected on student endpoints
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from tests.helpers.token_factory import make_student_token, make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _insert_student(client, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|test-{student_id[:8]}",
        f"Student {student_id[:6]}",
        f"s-{student_id[:6]}@test.invalid",
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Dashboard tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_returns_correct_structure(client, db_conn, student_token):
    """GET /student/dashboard returns the expected response shape."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    r = await client.get("/api/v1/student/dashboard", headers=_auth(student_token))
    assert r.status_code == 200
    data = r.json()

    assert "summary" in data
    assert "subject_progress" in data
    assert "recent_activity" in data
    summary = data["summary"]
    assert "units_completed" in summary
    assert "quizzes_passed" in summary
    assert "current_streak_days" in summary
    assert "total_time_minutes" in summary
    assert "avg_quiz_score" in summary


@pytest.mark.asyncio
async def test_dashboard_cached_in_redis(client, db_conn, student_token, fake_redis):
    """Second call returns cached value from Redis."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    # First call — populates cache
    r1 = await client.get("/api/v1/student/dashboard", headers=_auth(student_token))
    assert r1.status_code == 200

    # Cache should now be set
    cached = await fake_redis.get(f"dashboard:{student_id}")
    assert cached is not None

    # Second call — served from cache
    r2 = await client.get("/api/v1/student/dashboard", headers=_auth(student_token))
    assert r2.status_code == 200
    assert r2.json() == r1.json()


@pytest.mark.asyncio
async def test_dashboard_requires_student_token(client, teacher_token):
    """Teacher JWT must be rejected on /student/dashboard."""
    r = await client.get("/api/v1/student/dashboard", headers=_auth(teacher_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    """Unauthenticated request returns 403."""
    r = await client.get("/api/v1/student/dashboard")
    assert r.status_code == 403


# ── Progress map tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_progress_map_returns_correct_structure(client, db_conn, student_token):
    """GET /student/progress returns the expected response shape."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    r = await client.get("/api/v1/student/progress", headers=_auth(student_token))
    assert r.status_code == 200
    data = r.json()

    assert "curriculum_id" in data
    assert "pending_count" in data
    assert "needs_retry_count" in data
    assert isinstance(data["subjects"], list)


@pytest.mark.asyncio
async def test_progress_map_requires_student_token(client, teacher_token):
    """Teacher JWT rejected on /student/progress."""
    r = await client.get("/api/v1/student/progress", headers=_auth(teacher_token))
    assert r.status_code == 403


# ── Stats tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_7d_returns_correct_structure(client, db_conn, student_token):
    """GET /student/stats?period=7d returns stats shape with daily_activity."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    r = await client.get("/api/v1/student/stats?period=7d", headers=_auth(student_token))
    assert r.status_code == 200
    data = r.json()

    assert data["period"] == "7d"
    assert "lessons_viewed" in data
    assert "quizzes_completed" in data
    assert "quizzes_passed" in data
    assert "avg_quiz_score" in data
    assert "streak_current_days" in data
    assert "streak_longest_days" in data
    assert isinstance(data["daily_activity"], list)


@pytest.mark.asyncio
async def test_stats_30d(client, db_conn, student_token):
    """GET /student/stats?period=30d returns 200."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    r = await client.get("/api/v1/student/stats?period=30d", headers=_auth(student_token))
    assert r.status_code == 200
    assert r.json()["period"] == "30d"


@pytest.mark.asyncio
async def test_stats_all(client, db_conn, student_token):
    """GET /student/stats?period=all returns 200."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    r = await client.get("/api/v1/student/stats?period=all", headers=_auth(student_token))
    assert r.status_code == 200
    assert r.json()["period"] == "all"


@pytest.mark.asyncio
async def test_stats_invalid_period_returns_422(client, student_token):
    """Invalid period value returns 422 Unprocessable Entity."""
    r = await client.get("/api/v1/student/stats?period=invalid", headers=_auth(student_token))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_stats_requires_student_token(client, teacher_token):
    """Teacher JWT rejected on /student/stats."""
    r = await client.get("/api/v1/student/stats?period=7d", headers=_auth(teacher_token))
    assert r.status_code == 403
