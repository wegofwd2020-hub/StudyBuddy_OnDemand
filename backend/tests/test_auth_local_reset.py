"""
backend/tests/test_auth_local_reset.py

Self-serve password reset for local (school-provisioned) users — issue #444.

POST /auth/forgot-password now branches: for a local user it issues a one-time
token (Redis, 1 hr TTL) and emails a reset link; for everyone else it falls back
to the Auth0 hosted flow. POST /auth/reset-password consumes the token, sets the
new password, clears first_login, and burns the token (single-use).

Provisioning happy paths use real DB state via /schools/register +
/schools/{id}/teachers|students (same strategy as test_auth_universal_login.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

_PW = "SecureTestPwd1!"
_NEW_PW = "BrandNewPassword9!"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _provision_teacher(
    client: AsyncClient, school_id: str, token: str, name: str, email: str
) -> str:
    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock) as m:
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": name, "email": email},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    a = m.call_args
    return a.args[2] if len(a.args) >= 3 else a.kwargs["password"]


async def _provision_student(
    client: AsyncClient, school_id: str, token: str, name: str, email: str
) -> str:
    with patch("src.email.service.send_welcome_student_email", new_callable=AsyncMock) as m:
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": name, "email": email, "grade": 8},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    a = m.call_args
    return a.args[2] if len(a.args) >= 3 else a.kwargs["password"]


async def _forgot(client: AsyncClient, email: str):
    """Trigger forgot-password with both downstream senders patched.

    Returns (response, local_email_mock, auth0_mock). When the email belongs to a
    local user the reset token is local_email_mock.call_args.args[2].
    """
    with (
        patch("src.auth.router.send_local_reset_link_email", new_callable=AsyncMock) as local_mock,
        patch("src.auth.router.trigger_auth0_password_reset", new_callable=AsyncMock) as auth0_mock,
    ):
        r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    return r, local_mock, auth0_mock


# ── Forgot-password branching ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forgot_password_local_user_issues_token_and_emails_link(
    client: AsyncClient, fake_redis
):
    """A local teacher gets a tokenised reset link, not the dead-end Auth0 flow."""
    school = await _register_school(client, "Reset School A", "admin-a@reset-test.example.com")
    email = "teach-a@reset-test.example.com"
    await _provision_teacher(client, school["school_id"], school["access_token"], "Tay", email)

    r, local_mock, auth0_mock = await _forgot(client, email)

    assert r.status_code == 200
    local_mock.assert_awaited_once()
    auth0_mock.assert_not_awaited()  # local users never hit the Auth0 path

    token = local_mock.call_args.args[2]
    stored = await fake_redis.get(f"local_pw_reset:{token}")
    assert stored is not None
    assert stored.decode().startswith("teacher:")


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_falls_back_to_auth0(client: AsyncClient):
    """No local account → Auth0 hosted flow, still always 200, no local email."""
    r, local_mock, auth0_mock = await _forgot(client, "nobody@nowhere.invalid")

    assert r.status_code == 200
    local_mock.assert_not_awaited()
    auth0_mock.assert_awaited_once()


# ── Reset-password ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_password_completes_and_allows_login(client: AsyncClient):
    """End-to-end: forgot → reset → log in with the new password (old one fails)."""
    school = await _register_school(client, "Reset School B", "admin-b@reset-test.example.com")
    email = "stud-b@reset-test.example.com"
    old_pw = await _provision_student(
        client, school["school_id"], school["access_token"], "Sam", email
    )

    _, local_mock, _ = await _forgot(client, email)
    token = local_mock.call_args.args[2]

    rp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": _NEW_PW}
    )
    assert rp.status_code == 200, rp.text

    # New password works...
    ok = await client.post("/api/v1/auth/login", json={"email": email, "password": _NEW_PW})
    assert ok.status_code == 200, ok.text
    # ...and self-serve reset clears first_login (deliberate password choice).
    assert ok.json()["first_login"] is False

    # Old emailed password no longer works.
    bad = await client.post("/api/v1/auth/login", json={"email": email, "password": old_pw})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    """An unknown/expired token is rejected with 400."""
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "definitely-not-a-real-token", "new_password": _NEW_PW},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_token_is_single_use(client: AsyncClient):
    """A token works once; a replay is rejected."""
    school = await _register_school(client, "Reset School C", "admin-c@reset-test.example.com")
    email = "teach-c@reset-test.example.com"
    await _provision_teacher(client, school["school_id"], school["access_token"], "Cee", email)

    _, local_mock, _ = await _forgot(client, email)
    token = local_mock.call_args.args[2]

    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": _NEW_PW}
    )
    assert first.status_code == 200, first.text

    replay = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "AnotherPass123!"}
    )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_rejects_short_password(client: AsyncClient):
    """Schema enforces the ≥12 char policy before any token lookup."""
    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": "whatever", "new_password": "short"}
    )
    assert r.status_code == 422
