"""
tests/test_notifications.py

Tests for push notification endpoints.

Coverage:
  - POST /notifications/token   — register FCM token, upsert idempotency
  - DELETE /notifications/token — deregister token
  - GET  /notifications/preferences — returns defaults if no row
  - PUT  /notifications/preferences — upserts + returns updated values
  - GET  /notifications/preferences — returns updated values after PUT
  - Unauthenticated requests return 401
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
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
        f"auth0|notif-{student_id[:8]}",
        f"Notif Student {student_id[:6]}",
        f"notif-{student_id[:6]}@test.invalid",
    )


def _student_id_from_token(token: str) -> str:
    from jose import jwt as _jwt
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    return payload["student_id"]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_token_returns_200(client, db_conn, student_token):
    """POST /notifications/token registers a token and returns token_id + platform."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.post(
        "/api/v1/notifications/token",
        json={"device_token": "fcm-token-abc123", "platform": "android"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token_id" in data
    assert data["platform"] == "android"


@pytest.mark.asyncio
async def test_register_token_upsert_idempotent(client, db_conn, student_token):
    """Registering the same device_token twice returns the same token_id."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    payload = {"device_token": "fcm-idempotent-token", "platform": "ios"}
    headers = {"Authorization": f"Bearer {student_token}"}

    r1 = await client.post("/api/v1/notifications/token", json=payload, headers=headers)
    r2 = await client.post("/api/v1/notifications/token", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["token_id"] == r2.json()["token_id"]


@pytest.mark.asyncio
async def test_register_token_invalid_platform_returns_422(client, db_conn, student_token):
    """Invalid platform value triggers schema validation error."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.post(
        "/api/v1/notifications/token",
        json={"device_token": "fcm-token", "platform": "windows"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_deregister_token(client, db_conn, student_token):
    """DELETE /notifications/token removes the token and returns ok."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    payload = {"device_token": "fcm-to-delete", "platform": "android"}
    headers = {"Authorization": f"Bearer {student_token}"}

    await client.post("/api/v1/notifications/token", json=payload, headers=headers)
    r = await client.request("DELETE", "/api/v1/notifications/token", json=payload, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_preferences_returns_defaults(client, db_conn, student_token):
    """GET /notifications/preferences returns all-true defaults when no row exists."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.get(
        "/api/v1/notifications/preferences",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["streak_reminders"] is True
    assert data["weekly_summary"] is True
    assert data["quiz_nudges"] is True


@pytest.mark.asyncio
async def test_update_and_get_preferences(client, db_conn, student_token):
    """PUT /notifications/preferences persists values; GET returns them."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    headers = {"Authorization": f"Bearer {student_token}"}
    new_prefs = {"streak_reminders": False, "weekly_summary": True, "quiz_nudges": False}

    r_put = await client.put("/api/v1/notifications/preferences", json=new_prefs, headers=headers)
    assert r_put.status_code == 200
    assert r_put.json()["streak_reminders"] is False
    assert r_put.json()["quiz_nudges"] is False

    r_get = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert r_get.status_code == 200
    assert r_get.json()["streak_reminders"] is False
    assert r_get.json()["quiz_nudges"] is False
    assert r_get.json()["weekly_summary"] is True


@pytest.mark.asyncio
async def test_notifications_require_auth(client):
    """All notification endpoints return 401 without a JWT."""
    r1 = await client.post("/api/v1/notifications/token", json={"device_token": "t", "platform": "ios"})
    r2 = await client.get("/api/v1/notifications/preferences")
    r3 = await client.put("/api/v1/notifications/preferences", json={"streak_reminders": True, "weekly_summary": True, "quiz_nudges": True})
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
