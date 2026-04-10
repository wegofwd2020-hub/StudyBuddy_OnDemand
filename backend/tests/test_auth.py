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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.core.cache import jwks_cache
from tests.helpers.token_factory import make_admin_token, make_student_token


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


# ── JWKS cache TTL and key-rotation retry ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_jwks_uses_cache(client: AsyncClient):
    """_fetch_jwks returns cached value without hitting network on second call."""
    sample_jwks = {"keys": [{"kid": "key1", "kty": "RSA", "n": "abc", "e": "AQAB"}]}

    call_count = 0

    async def _mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_jwks
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    jwks_cache.clear()
    with patch("src.auth.service.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=_mock_get))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from src.auth.service import _fetch_jwks
        await _fetch_jwks()
        await _fetch_jwks()  # second call — must hit cache, not network

    assert call_count == 1, "JWKS URL should only be fetched once; second call must use TTLCache"
    jwks_cache.clear()


@pytest.mark.asyncio
async def test_verify_auth0_token_retries_on_stale_jwks(client: AsyncClient):
    """
    If kid is not found in cached JWKS, verify_auth0_token evicts the cache
    and fetches fresh JWKS exactly once before giving up.
    """
    stale_jwks = {"keys": [{"kid": "old-key", "kty": "RSA", "n": "x", "e": "AQAB"}]}
    fresh_jwks = {"keys": [{"kid": "old-key", "kty": "RSA", "n": "x", "e": "AQAB"}]}

    fetch_count = 0

    async def _mock_get(url, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        mock_resp = MagicMock()
        mock_resp.json.return_value = fresh_jwks
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    # Seed cache with stale JWKS (different kid than the token presents)
    from config import settings as cfg
    jwks_cache[cfg.AUTH0_JWKS_URL] = stale_jwks

    # Token header claims kid="new-key" which is absent from the stale cache
    import base64, json as _json
    header = base64.urlsafe_b64encode(_json.dumps({"alg": "RS256", "kid": "new-key"}).encode()).decode().rstrip("=")
    fake_token = f"{header}.payload.sig"

    from fastapi import HTTPException
    from src.auth.service import verify_auth0_token

    with patch("src.auth.service.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=_mock_get))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await verify_auth0_token(fake_token)

    # Fresh JWKS was fetched exactly once after cache miss
    assert fetch_count == 1, "Should fetch fresh JWKS exactly once on cache miss"
    # Ended with 401 (key still not found in fresh JWKS — this is expected in the test)
    assert exc_info.value.status_code == 401
    jwks_cache.clear()


@pytest.mark.asyncio
async def test_verify_auth0_teacher_token_retries_on_stale_jwks(client: AsyncClient):
    """
    verify_auth0_teacher_token must also evict and retry on stale JWKS — same
    behaviour as the student path. Regression guard for the parity fix in #113.
    """
    stale_jwks = {"keys": [{"kid": "old-key", "kty": "RSA", "n": "x", "e": "AQAB"}]}
    fresh_jwks = {"keys": [{"kid": "old-key", "kty": "RSA", "n": "x", "e": "AQAB"}]}

    fetch_count = 0

    async def _mock_get(url, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        mock_resp = MagicMock()
        mock_resp.json.return_value = fresh_jwks
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    from config import settings as cfg
    jwks_cache[cfg.AUTH0_JWKS_URL] = stale_jwks

    import base64, json as _json
    header = base64.urlsafe_b64encode(_json.dumps({"alg": "RS256", "kid": "new-key"}).encode()).decode().rstrip("=")
    fake_token = f"{header}.payload.sig"

    from fastapi import HTTPException
    from src.auth.service import verify_auth0_teacher_token

    with patch("src.auth.service.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=_mock_get))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await verify_auth0_teacher_token(fake_token)

    assert fetch_count == 1, "Teacher path must also fetch fresh JWKS exactly once on cache miss"
    assert exc_info.value.status_code == 401
    jwks_cache.clear()
