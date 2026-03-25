"""
tests/test_auth.py

Tests for auth endpoints:
  - POST /api/v1/auth/exchange (mock Auth0 token)
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - POST /api/v1/auth/forgot-password
  - POST /api/v1/admin/auth/login
  - Admin lockout after 5 failures
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token, make_admin_token


# ── Auth0 exchange helpers ────────────────────────────────────────────────────

def _mock_auth0_claims(
    sub: str | None = None,
    email: str = "alice@example.com",
    name: str = "Alice",
    grade: int = 8,
    locale: str = "en",
) -> dict:
    return {
        "sub": sub or f"auth0|{uuid.uuid4()}",
        "email": email,
        "name": name,
        "https://studybuddy.app/grade": grade,
        "locale": locale,
        "aud": "test-student-client-id",
    }


# ── Student exchange ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_exchange_creates_student(client: AsyncClient):
    """POST /auth/exchange with valid Auth0 token creates student and returns JWT."""
    claims = _mock_auth0_claims()

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        response = await client.post(
            "/api/v1/auth/exchange",
            json={"id_token": "fake.auth0.token"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "token" in data
    assert "refresh_token" in data
    assert "student_id" in data
    assert data["student"]["grade"] == 8
    assert data["student"]["locale"] == "en"


@pytest.mark.asyncio
async def test_auth_exchange_upserts_on_second_login(client: AsyncClient):
    """Second login with same auth0 sub upserts the student (no duplicate error)."""
    sub = f"auth0|{uuid.uuid4()}"
    claims = _mock_auth0_claims(sub=sub, email="bob@example.com")

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        r1 = await client.post("/api/v1/auth/exchange", json={"id_token": "fake1"})
        r2 = await client.post("/api/v1/auth/exchange", json={"id_token": "fake1"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # student_id should be the same on both logins.
    assert r1.json()["student_id"] == r2.json()["student_id"]


@pytest.mark.asyncio
async def test_auth_exchange_under13_blocked_pending(client: AsyncClient):
    """Under-13 student (requires_parental_consent=true) is blocked with 403 account_pending."""
    sub = f"auth0|{uuid.uuid4()}"
    claims = {
        **_mock_auth0_claims(sub=sub, email="young@example.com", grade=5),
        "https://studybuddy.app/requires_parental_consent": True,
    }

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        r = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "account_pending"


@pytest.mark.asyncio
async def test_auth_exchange_suspended_account(client: AsyncClient, fake_redis):
    """POST /auth/exchange with a suspended student returns 403."""
    sub = f"auth0|{uuid.uuid4()}"
    claims = _mock_auth0_claims(sub=sub, email="suspended@example.com")

    # First, create the account.
    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        r = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})
    assert r.status_code == 200

    student_id = r.json()["student_id"]

    # Directly set account_status to suspended in DB and add to Redis suspended set.
    pool = client._transport.app.state.pool
    await pool.execute(
        "UPDATE students SET account_status = 'suspended' WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    await fake_redis.set(f"suspended:{student_id}", "1")

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        r2 = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})

    assert r2.status_code == 403
    assert r2.json()["error"] == "account_suspended"


# ── Refresh ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_refresh_valid(client: AsyncClient):
    """POST /auth/refresh with valid refresh token returns a new JWT."""
    claims = _mock_auth0_claims(email="refresh_test@example.com")

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        exchange = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})

    refresh_token = exchange.json()["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_auth_refresh_invalid_token(client: AsyncClient):
    """POST /auth/refresh with unknown token returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token-xyz"},
    )
    assert response.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_logout_deletes_refresh_token(client: AsyncClient):
    """POST /auth/logout deletes the refresh token; subsequent refresh fails."""
    claims = _mock_auth0_claims(email="logout_test@example.com")

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        exchange = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})

    refresh_token = exchange.json()["refresh_token"]

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 200

    # Refresh after logout should fail.
    retry = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert retry.status_code == 401


# ── Forgot password (always 200) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_existing_email(client: AsyncClient):
    """POST /auth/forgot-password always returns 200 even for existing emails."""
    with patch("src.auth.router.trigger_auth0_password_reset", AsyncMock(return_value=None)):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "someuser@example.com"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(client: AsyncClient):
    """POST /auth/forgot-password always returns 200 even for unknown emails."""
    with patch("src.auth.router.trigger_auth0_password_reset", AsyncMock(return_value=None)):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@nowhere.invalid"},
        )
    assert response.status_code == 200


# ── Admin login ───────────────────────────────────────────────────────────────

@pytest.fixture
async def admin_user(client: AsyncClient):
    """Create an admin user in the test DB and return their credentials."""
    pool = client._transport.app.state.pool
    from src.auth.service import hash_password
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "correct-horse-battery-staple-1!"
    hashed = await hash_password(password)
    row = await pool.fetchrow(
        """
        INSERT INTO admin_users (email, password_hash, role, account_status)
        VALUES ($1, $2, 'product_admin', 'active')
        RETURNING admin_user_id, email
        """,
        email,
        hashed,
    )
    return {"admin_user_id": str(row["admin_user_id"]), "email": email, "password": password}


@pytest.mark.asyncio
async def test_admin_login_valid(client: AsyncClient, admin_user):
    """POST /admin/auth/login with valid credentials returns a JWT."""
    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "token" in data
    assert "admin_id" in data


@pytest.mark.asyncio
async def test_admin_login_wrong_password(client: AsyncClient, admin_user):
    """POST /admin/auth/login with wrong password returns 401."""
    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "password": "wrongpassword123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_lockout_after_5_failures(client: AsyncClient, admin_user):
    """Admin login is locked after 5 consecutive failures (returns 423)."""
    for i in range(5):
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": admin_user["email"], "password": f"wrong{i}"},
        )
        assert r.status_code == 401

    # 6th attempt should be locked.
    r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "password": "wrongagain"},
    )
    assert r.status_code == 423
    assert "Retry-After" in r.headers


@pytest.mark.asyncio
async def test_admin_login_lockout_reset_on_success(client: AsyncClient, admin_user, fake_redis):
    """Successful login resets the lockout counter."""
    # Simulate 3 failed attempts.
    await fake_redis.set(f"login_attempts:{admin_user['email']}", "3", ex=900)

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert response.status_code == 200

    # Counter should be gone.
    count = await fake_redis.get(f"login_attempts:{admin_user['email']}")
    assert count is None


# ── Student JWT on admin endpoint ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_student_token_rejected_on_admin_endpoint(client: AsyncClient, student_token):
    """A student JWT must never grant access to admin endpoints."""
    response = await client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": "any"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    # The refresh endpoint takes a body, not the student token; this should fail at
    # the refresh token lookup (401), not a 403. Verify student token can't be used
    # to access an admin-only action by checking account endpoint.
    # Test account endpoint which requires admin JWT.
    response = await client.patch(
        f"/api/v1/account/students/{uuid.uuid4()}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    # Student token uses JWT_SECRET not ADMIN_JWT_SECRET → jose decode will fail
    assert response.status_code in (401, 403)
