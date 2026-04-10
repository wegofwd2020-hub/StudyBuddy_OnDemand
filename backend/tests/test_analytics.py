"""
tests/test_analytics.py

Tests for lesson analytics endpoints.

Coverage:
  - POST /analytics/lesson/start — creates lesson_views row, returns view_id
  - POST /analytics/lesson/end   — dispatches Celery task, returns immediately
  - Ownership enforcement: student B cannot end student A's view
  - 409 on double-end attempt
  - Unauthenticated requests return 401
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

# ── Deterministic test IDs (Rule 9) ──────────────────────────────────────────
_NONEXISTENT_VIEW_ID = "c9000000-0000-0000-0000-000000000001"

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token


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
        f"auth0|analytics-{student_id[:8]}",
        f"Analytics Student {student_id[:6]}",
        f"analytics-{student_id[:6]}@test.invalid",
    )


def _student_id_from_token(token: str) -> str:
    from jose import jwt as _jwt
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    return payload["student_id"]


async def _start_view(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/api/v1/analytics/lesson/start",
        json={"unit_id": "G8-MATH-001", "curriculum_id": "default-2026-g8"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lesson_start_returns_201(client, db_conn, student_token):
    """POST /analytics/lesson/start creates a view and returns view_id."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    data = await _start_view(client, student_token)
    assert "view_id" in data
    # Verify it's a valid UUID
    uuid.UUID(data["view_id"])


@pytest.mark.asyncio
async def test_lesson_end_fires_and_returns_200(client, db_conn, student_token):
    """POST /analytics/lesson/end dispatches Celery task and returns 200 immediately."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    view_data = await _start_view(client, student_token)
    view_id = view_data["view_id"]

    with patch("src.auth.tasks.celery_app.send_task", return_value=None) as mock_send:
        r = await client.post(
            "/api/v1/analytics/lesson/end",
            json={"view_id": view_id, "duration_s": 120, "audio_played": True, "experiment_viewed": False},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert r.status_code == 200, r.text
        mock_send.assert_called_once()
        task_name = mock_send.call_args[0][0]
        assert task_name == "src.auth.tasks.write_lesson_end_task"

    data = r.json()
    assert data["view_id"] == view_id
    assert data["duration_s"] == 120


@pytest.mark.asyncio
async def test_lesson_end_ownership_enforced(client, db_conn):
    """Student B cannot end student A's lesson view."""
    token_a = make_student_token()
    token_b = make_student_token()
    student_a = _student_id_from_token(token_a)
    student_b = _student_id_from_token(token_b)

    await _insert_student(client, student_a)
    await _insert_student(client, student_b)

    # Student A starts a view
    view_data = await _start_view(client, token_a)
    view_id = view_data["view_id"]

    # Student B tries to end it
    r = await client.post(
        "/api/v1/analytics/lesson/end",
        json={"view_id": view_id, "duration_s": 60, "audio_played": False},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


@pytest.mark.asyncio
async def test_lesson_end_invalid_view_id_returns_400(client, db_conn, student_token):
    """Non-UUID view_id returns 400."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.post(
        "/api/v1/analytics/lesson/end",
        json={"view_id": "not-a-uuid", "duration_s": 60},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_view_id"


@pytest.mark.asyncio
async def test_lesson_end_nonexistent_view_returns_404(client, db_conn, student_token):
    """Unknown view_id returns 404."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.post(
        "/api/v1/analytics/lesson/end",
        json={"view_id": _NONEXISTENT_VIEW_ID, "duration_s": 60},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "view_not_found"


@pytest.mark.asyncio
async def test_lesson_end_double_end_returns_409(client, db_conn, student_token):
    """Ending a view that has already ended returns 409."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    view_data = await _start_view(client, student_token)
    view_id = view_data["view_id"]

    # Manually mark as ended in the DB
    pool = client._transport.app.state.pool
    await pool.execute(
        "UPDATE lesson_views SET ended_at = NOW() WHERE view_id = $1",
        uuid.UUID(view_id),
    )

    r = await client.post(
        "/api/v1/analytics/lesson/end",
        json={"view_id": view_id, "duration_s": 60},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "view_already_ended"


@pytest.mark.asyncio
async def test_analytics_require_auth(client):
    """All analytics endpoints return 401 without a JWT."""
    r1 = await client.post("/api/v1/analytics/lesson/start", json={"unit_id": "x", "curriculum_id": "y"})
    r2 = await client.post("/api/v1/analytics/lesson/end", json={"view_id": _NONEXISTENT_VIEW_ID, "duration_s": 60})
    assert r1.status_code == 401
    assert r2.status_code == 401
