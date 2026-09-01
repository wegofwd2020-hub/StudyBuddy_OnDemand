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


# ── Checking a token without consuming it ─────────────────────────────────────
#
# The reset page gated on the token being PRESENT, never on it being valid, so an
# expired link rendered "Set new password" identically to a good one and the
# failure only surfaced after the form was filled in. A tester reported that
# twice as "the link still worked hours later". The link did not work — nothing
# on screen said so. These tests cover the endpoint that lets the page ask.


async def _check(client: AsyncClient, token: str) -> bool:
    r = await client.post("/api/v1/auth/reset-password/check", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()["valid"]


@pytest.mark.asyncio
async def test_check_reports_a_live_token_as_valid(client: AsyncClient):
    school = await _register_school(client, "Check School A", "admin-ca@reset-test.example.com")
    email = "teach-ca@reset-test.example.com"
    await _provision_teacher(client, school["school_id"], school["access_token"], "Cay", email)

    _, local_mock, _ = await _forgot(client, email)
    assert await _check(client, local_mock.call_args.args[2]) is True


@pytest.mark.asyncio
async def test_check_reports_an_unknown_token_as_invalid(client: AsyncClient):
    """The negative direction. Without this, an endpoint hardcoded to `true`
    passes the valid-token test above and ships the original bug intact."""
    assert await _check(client, "definitely-not-a-real-token") is False


@pytest.mark.asyncio
async def test_check_does_not_consume_the_token(client: AsyncClient):
    """The whole point of a separate endpoint.

    `/auth/reset-password` burns the token as part of answering, so checking via
    that path would destroy the token the student came to use — the check would
    cause the very failure it reports. Checking twice and THEN resetting proves
    the check is read-only.
    """
    school = await _register_school(client, "Check School B", "admin-cb@reset-test.example.com")
    email = "stud-cb@reset-test.example.com"
    await _provision_student(client, school["school_id"], school["access_token"], "Cee Bee", email)

    _, local_mock, _ = await _forgot(client, email)
    token = local_mock.call_args.args[2]

    assert await _check(client, token) is True
    assert await _check(client, token) is True

    rp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": _NEW_PW}
    )
    assert rp.status_code == 200, rp.text
    ok = await client.post("/api/v1/auth/login", json={"email": email, "password": _NEW_PW})
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_check_reports_a_spent_token_as_invalid(client: AsyncClient):
    """Reset is single-use, so a second click on the same emailed link must show
    the expired screen rather than a form that cannot succeed."""
    school = await _register_school(client, "Check School C", "admin-cc@reset-test.example.com")
    email = "teach-cc@reset-test.example.com"
    await _provision_teacher(client, school["school_id"], school["access_token"], "Cee Cee", email)

    _, local_mock, _ = await _forgot(client, email)
    token = local_mock.call_args.args[2]

    assert await _check(client, token) is True
    rp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": _NEW_PW}
    )
    assert rp.status_code == 200, rp.text

    assert await _check(client, token) is False


@pytest.mark.asyncio
async def test_check_agrees_with_reset_on_a_malformed_payload(client: AsyncClient, fake_redis):
    """A key can exist holding something this flow cannot act on. `reset_password`
    treats that as invalid; if the check disagreed the page would render a form
    guaranteed to fail on submit — the original bug with one extra step."""
    await fake_redis.set("local_pw_reset:junk-payload-token", "parent:whoever")

    assert await _check(client, "junk-payload-token") is False
    rp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "junk-payload-token", "new_password": _NEW_PW},
    )
    assert rp.status_code == 400


@pytest.mark.asyncio
async def test_check_never_reveals_who_the_token_belongs_to(client: AsyncClient):
    """A leaked reset link must not double as a PII lookup: the response is a
    bare boolean, with no email, name, user id or user type anywhere in it."""
    school = await _register_school(client, "Check School D", "admin-cd@reset-test.example.com")
    email = "stud-cd@reset-test.example.com"
    await _provision_student(client, school["school_id"], school["access_token"], "Dee", email)

    _, local_mock, _ = await _forgot(client, email)
    r = await client.post(
        "/api/v1/auth/reset-password/check",
        json={"token": local_mock.call_args.args[2]},
    )
    assert r.status_code == 200
    assert r.json() == {"valid": True}
    body = r.text.lower()
    for leak in ("stud-cd", "dee", "student", "teacher", school["school_id"]):
        assert leak.lower() not in body, f"response leaked {leak!r}"
