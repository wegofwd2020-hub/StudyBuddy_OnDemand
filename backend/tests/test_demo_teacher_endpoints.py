"""
backend/tests/test_demo_teacher_endpoints.py

Tests for demo teacher endpoints:
  POST /demo/teacher/request
  GET  /demo/teacher/verify/{token}
  POST /demo/teacher/auth/login
  POST /demo/teacher/auth/logout
  POST /demo/teacher/verify/resend

Strategy:
  - Happy paths use real DB state created via API calls.
  - Edge-case states (expired/used tokens, capacity) use service-layer mocks.
  - Celery tasks are always patched — no live workers needed.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_demo_teacher_token, make_student_token

# ── Helpers ───────────────────────────────────────────────────────────────────


@contextmanager
def _patch_teacher_celery():
    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            return_value=None,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield


@contextmanager
def _capture_teacher_verification_token():
    captured: list[str] = []

    def _delay(email: str, token: str) -> None:
        captured.append(token)

    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            side_effect=_delay,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield lambda: captured[-1] if captured else None


def _make_asyncpg_record(**fields) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: fields[key]
    mock.get = lambda key, default=None: fields.get(key, default)
    for k, v in fields.items():
        setattr(mock, k, v)
    return mock


# ── POST /demo/teacher/request ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_request_success(client: AsyncClient):
    """Valid email returns 200 and confirmation message."""
    with _patch_teacher_celery():
        r = await client.post(
            "/api/v1/demo/teacher/request",
            json={"email": "teacher-req-ok@example.com"},
        )
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_teacher_request_invalid_email(client: AsyncClient):
    """Non-email string is rejected with 422."""
    r = await client.post(
        "/api/v1/demo/teacher/request", json={"email": "not-an-email"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_teacher_request_duplicate_pending(client: AsyncClient):
    """Second request for same email while verification pending returns 409."""
    email = "teacher-dup-pending@example.com"
    with _patch_teacher_celery():
        r1 = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r1.status_code == 200

    with _patch_teacher_celery():
        r2 = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r2.status_code == 409
    assert r2.json()["error"] == "verification_pending"


@pytest.mark.asyncio
async def test_teacher_request_duplicate_active_account(client: AsyncClient):
    """Request for email with an active demo teacher account returns 409."""
    email = "teacher-dup-active@example.com"

    with _capture_teacher_verification_token() as get_token:
        r = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_teacher_celery():
        rv = await client.get(f"/api/v1/demo/teacher/verify/{token}")
    assert rv.status_code == 200

    with _patch_teacher_celery():
        r2 = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r2.status_code == 409
    assert r2.json()["error"] == "demo_already_active"


@pytest.mark.asyncio
async def test_teacher_request_rate_limited(client: AsyncClient):
    """Fourth request from same IP within window returns 429."""
    for i in range(3):
        with _patch_teacher_celery():
            r = await client.post(
                "/api/v1/demo/teacher/request",
                json={"email": f"teacher-rl{i}@example.com"},
            )
        assert r.status_code == 200

    with _patch_teacher_celery():
        r = await client.post(
            "/api/v1/demo/teacher/request",
            json={"email": "teacher-rl4@example.com"},
        )
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


# ── GET /demo/teacher/verify/{token} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_verify_invalid_token(client: AsyncClient):
    """Unknown token returns 404."""
    r = await client.get("/api/v1/demo/teacher/verify/does-not-exist-token")
    assert r.status_code == 404
    assert r.json()["error"] == "token_not_found"


@pytest.mark.asyncio
async def test_teacher_verify_already_used(client: AsyncClient):
    """Already-used token returns 409 (service layer mock)."""
    used_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="teacher-used@example.com",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=datetime.now(UTC) - timedelta(minutes=5),
        request_status="verified",
    )

    with patch(
        "src.demo.teacher_router.get_teacher_verification_by_token",
        AsyncMock(return_value=used_row),
    ):
        r = await client.get("/api/v1/demo/teacher/verify/used-token")
    assert r.status_code == 409
    assert r.json()["error"] == "token_already_used"


@pytest.mark.asyncio
async def test_teacher_verify_expired_token(client: AsyncClient):
    """Expired token returns 410 (service layer mock)."""
    expired_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="teacher-expired@example.com",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        used_at=None,
        request_status="pending",
    )

    with patch(
        "src.demo.teacher_router.get_teacher_verification_by_token",
        AsyncMock(return_value=expired_row),
    ):
        r = await client.get("/api/v1/demo/teacher/verify/expired-token")
    assert r.status_code == 410
    assert r.json()["error"] == "token_expired"


@pytest.mark.asyncio
async def test_teacher_verify_already_verified(client: AsyncClient):
    """Token with request_status='verified' (but not used_at set) returns 409."""
    already_verified_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="teacher-already-verified@example.com",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
        request_status="verified",
    )

    with patch(
        "src.demo.teacher_router.get_teacher_verification_by_token",
        AsyncMock(return_value=already_verified_row),
    ):
        r = await client.get("/api/v1/demo/teacher/verify/already-verified-token")
    assert r.status_code == 409
    assert r.json()["error"] == "already_verified"


@pytest.mark.asyncio
async def test_teacher_verify_capacity_limit(client: AsyncClient):
    """Returns 503 when DEMO_TEACHER_MAX_ACTIVE cap is reached."""
    valid_row = _make_asyncpg_record(
        verif_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        email="teacher-capacity@example.com",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
        request_status="pending",
    )

    with (
        patch(
            "src.demo.teacher_router.get_teacher_verification_by_token",
            AsyncMock(return_value=valid_row),
        ),
        patch(
            "src.demo.teacher_router.count_active_demo_teachers",
            AsyncMock(return_value=9999),
        ),
    ):
        r = await client.get("/api/v1/demo/teacher/verify/capped-token")
    assert r.status_code == 503
    assert r.json()["error"] == "demo_capacity_reached"


@pytest.mark.asyncio
async def test_teacher_verify_success(client: AsyncClient):
    """Valid token creates a demo teacher account."""
    email = "teacher-verify-ok@example.com"

    with _capture_teacher_verification_token() as get_token:
        r = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_teacher_celery():
        rv = await client.get(f"/api/v1/demo/teacher/verify/{token}")
    assert rv.status_code == 200
    assert "message" in rv.json()


# ── POST /demo/teacher/auth/login ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_login_success(client: AsyncClient):
    """Full flow: request → verify → login returns JWT with role=demo_teacher."""
    email = "teacher-login-flow@example.com"

    with _capture_teacher_verification_token() as get_token:
        await client.post("/api/v1/demo/teacher/request", json={"email": email})
    verif_token = get_token()

    credentials_captured: list[tuple] = []

    def _capture_creds(email_arg: str, password_arg: str) -> None:
        credentials_captured.append((email_arg, password_arg))

    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            return_value=None,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            side_effect=_capture_creds,
        ),
    ):
        await client.get(f"/api/v1/demo/teacher/verify/{verif_token}")

    assert credentials_captured, "Credentials email task was not called"
    _, password = credentials_captured[0]

    r = await client.post(
        "/api/v1/demo/teacher/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "demo_expires_at" in data


@pytest.mark.asyncio
async def test_teacher_login_wrong_password(client: AsyncClient):
    """Wrong password returns 401."""
    email = "teacher-login-wrong-pw@example.com"

    with _capture_teacher_verification_token() as get_token:
        await client.post("/api/v1/demo/teacher/request", json={"email": email})
    token = get_token()
    with _patch_teacher_celery():
        await client.get(f"/api/v1/demo/teacher/verify/{token}")

    r = await client.post(
        "/api/v1/demo/teacher/auth/login",
        json={"email": email, "password": "definitely-wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_teacher_login_unknown_email(client: AsyncClient):
    """Unknown email returns 401."""
    r = await client.post(
        "/api/v1/demo/teacher/auth/login",
        json={"email": "nobody-teacher@example.com", "password": "anypass"},
    )
    assert r.status_code == 401


# ── POST /demo/teacher/auth/logout ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_logout_success(client: AsyncClient):
    """Valid demo_teacher token is accepted and logout returns 200."""
    token = make_demo_teacher_token()
    r = await client.post(
        "/api/v1/demo/teacher/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out."


@pytest.mark.asyncio
async def test_teacher_logout_jti_blacklisted(client: AsyncClient, fake_redis):
    """After logout the JWT JTI is blacklisted in Redis."""
    from jose import jwt as jose_jwt

    from tests.helpers.token_factory import TEST_JWT_SECRET

    token = make_demo_teacher_token()
    payload = jose_jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
    jti = payload["jti"]

    r = await client.post(
        "/api/v1/demo/teacher/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    exists = await fake_redis.exists(f"demo_teacher_blacklist:{jti}")
    assert exists == 1


@pytest.mark.asyncio
async def test_teacher_logout_no_token(client: AsyncClient):
    """Missing Bearer token returns 401."""
    r = await client.post("/api/v1/demo/teacher/auth/logout")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_teacher_logout_wrong_role_rejected(client: AsyncClient):
    """Regular student token on /demo/teacher/auth/logout returns 403."""
    token = make_student_token()
    r = await client.post(
        "/api/v1/demo/teacher/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_teacher_logout_invalid_token_returns_200(client: AsyncClient):
    """Malformed/invalid token gracefully returns 200 (no info leak)."""
    r = await client.post(
        "/api/v1/demo/teacher/auth/logout",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert r.status_code == 200


# ── POST /demo/teacher/verify/resend ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_resend_no_pending_verification(client: AsyncClient):
    """Resend for an email with no pending verification returns 200 (no info leak)."""
    with _patch_teacher_celery():
        r = await client.post(
            "/api/v1/demo/teacher/verify/resend",
            json={"email": "nobody-teacher@example.com"},
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_teacher_resend_success(client: AsyncClient):
    """Resend for email with a pending verification succeeds."""
    email = "teacher-resend-ok@example.com"
    with _patch_teacher_celery():
        r = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r.status_code == 200

    with _patch_teacher_celery():
        r2 = await client.post(
            "/api/v1/demo/teacher/verify/resend", json={"email": email}
        )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_teacher_resend_cooldown(client: AsyncClient, fake_redis):
    """Second resend within cooldown window returns 429."""
    email = "teacher-resend-cd@example.com"
    await fake_redis.set(f"demo_teacher_resend:{email}", "1", ex=300)

    with _patch_teacher_celery():
        r = await client.post(
            "/api/v1/demo/teacher/verify/resend", json={"email": email}
        )
    assert r.status_code == 429
    assert r.json()["error"] == "resend_cooldown"
