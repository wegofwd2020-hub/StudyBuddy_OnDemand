"""
backend/tests/test_demo_endpoints.py

Tests for issue #34 — Demo student endpoints:
  POST /demo/request
  GET  /demo/verify/{token}
  POST /demo/auth/login
  POST /demo/auth/logout
  POST /demo/verify/resend

Strategy:
  - Endpoint tests that need DB state use sequential API calls (data written via pool
    is immediately visible to subsequent requests — no isolation issue).
  - Edge-case states (expired/used tokens) that cannot be created via the API use
    service-layer mocks via patch().
  - Direct db_conn inserts are only used where auto-commit semantics are required
    (tests that call the pool directly via client.app.state.pool.acquire()).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_demo_student_token

# ── Helpers ───────────────────────────────────────────────────────────────────

_EMAIL = "demo-endpoint-test@example.com"


@contextmanager
def _patch_celery():
    """Patch both demo email tasks so no Celery workers are needed."""
    with (
        patch(
            "src.demo.router.send_demo_verification_email_task.delay",
            return_value=None,
        ),
        patch(
            "src.demo.router.send_demo_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield


@contextmanager
def _capture_verification_token():
    """
    Patch the verification email task and capture the token argument.

    Usage:
        with _capture_verification_token() as get_token:
            await client.post("/api/v1/demo/request", ...)
        token = get_token()
    """
    captured: list[str] = []

    def _delay(email: str, token: str) -> None:
        captured.append(token)

    with (
        patch("src.demo.router.send_demo_verification_email_task.delay", side_effect=_delay),
        patch("src.demo.router.send_demo_credentials_email_task.delay", return_value=None),
    ):
        yield lambda: captured[-1] if captured else None


def _make_asyncpg_record(**fields) -> MagicMock:
    """Create a MagicMock that behaves like an asyncpg Record for the given fields."""
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: fields[key]
    mock.get = lambda key, default=None: fields.get(key, default)
    for k, v in fields.items():
        setattr(mock, k, v)
    return mock


# ── POST /demo/request ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_request_success(client: AsyncClient):
    """Valid email returns 200 and a confirmation message."""
    with _patch_celery():
        r = await client.post(
            "/api/v1/demo/request", json={"email": "req-success@example.com"}
        )
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_demo_request_invalid_email(client: AsyncClient):
    """Non-email string is rejected with 422."""
    r = await client.post("/api/v1/demo/request", json={"email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_demo_request_duplicate_pending(client: AsyncClient):
    """Second request for the same email while verification is pending returns 409."""
    email = "dup-pending@example.com"
    with _patch_celery():
        r1 = await client.post("/api/v1/demo/request", json={"email": email})
    assert r1.status_code == 200

    # Second request — same email, verification still pending
    with _patch_celery():
        r2 = await client.post("/api/v1/demo/request", json={"email": email})
    assert r2.status_code == 409
    assert r2.json()["error"] == "verification_pending"


@pytest.mark.asyncio
async def test_demo_request_duplicate_active_account(client: AsyncClient):
    """Request for email with an active demo account returns 409."""
    email = "dup-active@example.com"

    # Full flow: request → capture token → verify (creates active account)
    with _capture_verification_token() as get_token:
        r = await client.post("/api/v1/demo/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_celery():
        rv = await client.get(f"/api/v1/demo/verify/{token}")
    assert rv.status_code == 200

    # Now requesting again should hit the active-account guard
    with _patch_celery():
        r2 = await client.post("/api/v1/demo/request", json={"email": email})
    assert r2.status_code == 409
    assert r2.json()["error"] == "demo_already_active"


@pytest.mark.asyncio
async def test_demo_request_rate_limited(client: AsyncClient):
    """Fourth request from the same IP within the window returns 429."""
    # Fill the rate-limit bucket with 3 successful requests
    for i in range(3):
        with _patch_celery():
            r = await client.post(
                "/api/v1/demo/request", json={"email": f"rl{i}@example.com"}
            )
        assert r.status_code == 200

    # 4th request should be blocked
    with _patch_celery():
        r = await client.post(
            "/api/v1/demo/request", json={"email": "rl4@example.com"}
        )
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


# ── GET /demo/verify/{token} ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_verify_invalid_token(client: AsyncClient):
    """Unknown token returns 404."""
    r = await client.get("/api/v1/demo/verify/does-not-exist-token")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_demo_verify_expired_token(client: AsyncClient):
    """Expired token returns 410 (service layer mock)."""
    from datetime import UTC, datetime, timedelta

    expired_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="expired@example.com",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        used_at=None,
        request_status="pending",
    )

    with patch(
        "src.demo.router.get_verification_by_token",
        AsyncMock(return_value=expired_row),
    ):
        r = await client.get("/api/v1/demo/verify/some-valid-looking-token")
    assert r.status_code == 410
    assert r.json()["error"] == "token_expired"


@pytest.mark.asyncio
async def test_demo_verify_already_used(client: AsyncClient):
    """Already-used token returns 409 (service layer mock)."""
    from datetime import UTC, datetime, timedelta

    used_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="used@example.com",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=datetime.now(UTC) - timedelta(minutes=5),
        request_status="verified",
    )

    with patch(
        "src.demo.router.get_verification_by_token",
        AsyncMock(return_value=used_row),
    ):
        r = await client.get("/api/v1/demo/verify/used-token")
    assert r.status_code == 409
    assert r.json()["error"] == "token_already_used"


@pytest.mark.asyncio
async def test_demo_verify_success(client: AsyncClient):
    """Valid token (from a prior POST /demo/request) creates a demo account."""
    email = "verify-success@example.com"

    with _capture_verification_token() as get_token:
        r = await client.post("/api/v1/demo/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_celery():
        rv = await client.get(f"/api/v1/demo/verify/{token}")
    assert rv.status_code == 200
    assert "message" in rv.json()


@pytest.mark.asyncio
async def test_demo_verify_capacity_limit(client: AsyncClient):
    """Returns 503 when DEMO_MAX_ACTIVE cap is reached (service layer mock)."""
    from datetime import UTC, datetime, timedelta

    email = "capacity@example.com"

    valid_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email=email,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
        request_status="pending",
    )

    with (
        patch(
            "src.demo.router.get_verification_by_token",
            AsyncMock(return_value=valid_row),
        ),
        patch("src.demo.router.count_active_demos", AsyncMock(return_value=9999)),
    ):
        r = await client.get("/api/v1/demo/verify/capped-token")

    assert r.status_code == 503
    assert r.json()["error"] == "demo_capacity_reached"


# ── POST /demo/auth/login ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_login_success(client: AsyncClient):
    """Full flow: request → verify → login returns JWT with role=demo_student."""
    email = "login-flow@example.com"

    # Step 1: request
    with _capture_verification_token() as get_token:
        await client.post("/api/v1/demo/request", json={"email": email})
    token = get_token()

    # Step 2: verify (creates account + sends credentials)
    credentials_captured: list[tuple] = []

    def _capture_creds(email_arg: str, password_arg: str) -> None:
        credentials_captured.append((email_arg, password_arg))

    with (
        patch("src.demo.router.send_demo_verification_email_task.delay", return_value=None),
        patch(
            "src.demo.router.send_demo_credentials_email_task.delay",
            side_effect=_capture_creds,
        ),
    ):
        await client.get(f"/api/v1/demo/verify/{token}")

    assert credentials_captured, "Credentials email task was not called"
    _, password = credentials_captured[0]

    # Step 3: login
    r = await client.post(
        "/api/v1/demo/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "demo_expires_at" in data


@pytest.mark.asyncio
async def test_demo_login_wrong_password(client: AsyncClient):
    """Wrong password returns 401 without revealing whether email exists."""
    email = "login-wrong-pw@example.com"

    with _capture_verification_token() as get_token:
        await client.post("/api/v1/demo/request", json={"email": email})
    token = get_token()
    with _patch_celery():
        await client.get(f"/api/v1/demo/verify/{token}")

    r = await client.post(
        "/api/v1/demo/auth/login",
        json={"email": email, "password": "definitely-wrong-pw"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_demo_login_unknown_email(client: AsyncClient):
    """Unknown email returns 401."""
    r = await client.post(
        "/api/v1/demo/auth/login",
        json={"email": "nobody@example.com", "password": "anypass"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_demo_login_expired_account(client: AsyncClient):
    """Expired demo account (no active row in DB) returns 401."""
    # No account exists for this email → treated same as unknown
    r = await client.post(
        "/api/v1/demo/auth/login",
        json={"email": "expired-gone@example.com", "password": "anypass"},
    )
    assert r.status_code == 401


# ── POST /demo/auth/logout ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_logout_success(client: AsyncClient):
    """Valid demo_student token is blacklisted and logout returns 200."""
    token = make_demo_student_token()
    r = await client.post(
        "/api/v1/demo/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out."


@pytest.mark.asyncio
async def test_demo_logout_token_rejected_after_logout(client: AsyncClient, fake_redis):
    """After logout the JWT JTI is blacklisted in Redis."""
    from jose import jwt as jose_jwt

    from tests.helpers.token_factory import TEST_JWT_SECRET

    token = make_demo_student_token()
    payload = jose_jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
    jti = payload["jti"]

    # Call logout
    r = await client.post(
        "/api/v1/demo/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    # Verify the JTI was blacklisted
    exists = await fake_redis.exists(f"demo_blacklist:{jti}")
    assert exists == 1


@pytest.mark.asyncio
async def test_demo_logout_no_token(client: AsyncClient):
    """Missing Bearer token returns 401."""
    r = await client.post("/api/v1/demo/auth/logout")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_demo_logout_non_demo_token_rejected(client: AsyncClient):
    """Regular student token on /demo/auth/logout returns 403."""
    from tests.helpers.token_factory import make_student_token

    token = make_student_token()
    r = await client.post(
        "/api/v1/demo/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ── POST /demo/verify/resend ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_resend_no_pending_verification(client: AsyncClient):
    """Resend for an email with no pending verification always returns 200 (no info leak)."""
    with _patch_celery():
        r = await client.post(
            "/api/v1/demo/verify/resend", json={"email": "nobody@example.com"}
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_demo_resend_success(client: AsyncClient):
    """Resend for email with a pending verification succeeds."""
    email = "resend-ok@example.com"
    with _patch_celery():
        r = await client.post("/api/v1/demo/request", json={"email": email})
    assert r.status_code == 200

    with _patch_celery():
        r2 = await client.post("/api/v1/demo/verify/resend", json={"email": email})
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_demo_resend_cooldown(client: AsyncClient, fake_redis):
    """Second resend within cooldown window returns 429."""
    email = "resend-cd@example.com"
    await fake_redis.set(f"demo_resend:{email}", "1", ex=300)

    with _patch_celery():
        r = await client.post("/api/v1/demo/verify/resend", json={"email": email})
    assert r.status_code == 429
    assert r.json()["error"] == "resend_cooldown"
