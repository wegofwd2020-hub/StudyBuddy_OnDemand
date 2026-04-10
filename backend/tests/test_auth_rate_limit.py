"""
tests/test_auth_rate_limit.py

Tests for IP-based and per-email rate limiting on auth endpoints (#116).

Covered:
  - POST /api/v1/auth/exchange          — 429 after 10 requests from same IP
  - POST /api/v1/auth/teacher/exchange  — 429 after 10 requests from same IP
  - POST /api/v1/auth/forgot-password   — 429 after 10 IP requests; Auth0 call
                                          suppressed after 5 per-email
  - POST /api/v1/admin/auth/login       — 429 after 10 requests from same IP
  - POST /api/v1/admin/auth/forgot-password — 429 after 10 requests
  - POST /api/v1/admin/auth/reset-password  — 429 after 10 requests
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
from httpx import AsyncClient

from main import app


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _exhaust_ip_limit(client: AsyncClient, url: str, json_body: dict) -> None:
    """Make 10 requests that each pass through the handler (or fail on auth,
    which is fine — we only care that the rate-limit counter increments)."""
    for _ in range(10):
        await client.post(url, json=json_body)


# ── IP limit — student exchange ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exchange_rate_limited_after_10(client: AsyncClient, fake_redis):
    """11th request from same IP on /auth/exchange → 429."""
    app.state.redis = fake_redis

    mock_claims = {
        "sub": f"auth0|{uuid.uuid4()}",
        "email": "user@example.com",
        "name": "User",
        "https://studybuddy.app/grade": 8,
        "locale": "en",
        "aud": "test-student-client-id",
    }

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=mock_claims)):
        for i in range(10):
            r = await client.post("/api/v1/auth/exchange", json={"id_token": "tok"})
            assert r.status_code != 429, f"Got 429 on request {i + 1}, expected it only on 11+"

        r = await client.post("/api/v1/auth/exchange", json={"id_token": "tok"})
        assert r.status_code == 429
        data = r.json()
        assert data["error"] == "rate_limited"


# ── IP limit — teacher exchange ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_exchange_rate_limited_after_10(client: AsyncClient, fake_redis):
    """11th request from same IP on /auth/teacher/exchange → 429."""
    app.state.redis = fake_redis

    mock_claims = {
        "sub": f"auth0|{uuid.uuid4()}",
        "email": "teacher@school.com",
        "name": "Teacher",
        "https://studybuddy.app/role": "teacher",
        "aud": "test-teacher-client-id",
    }

    with patch(
        "src.auth.router.verify_auth0_teacher_token", AsyncMock(return_value=mock_claims)
    ):
        for _ in range(10):
            await client.post("/api/v1/auth/teacher/exchange", json={"id_token": "tok"})

        r = await client.post("/api/v1/auth/teacher/exchange", json={"id_token": "tok"})
        assert r.status_code == 429
        assert r.json()["error"] == "rate_limited"


# ── IP limit — student forgot-password ────────────────────────────────────────


@pytest.mark.asyncio
async def test_forgot_password_rate_limited_after_10(client: AsyncClient, fake_redis):
    """11th IP request on /auth/forgot-password → 429."""
    app.state.redis = fake_redis

    with patch("src.auth.router.trigger_auth0_password_reset", AsyncMock()):
        for _ in range(10):
            await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": f"{uuid.uuid4()}@example.com"},
            )

        r = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "another@example.com"},
        )
        assert r.status_code == 429
        assert r.json()["error"] == "rate_limited"


@pytest.mark.asyncio
async def test_forgot_password_per_email_limit_suppresses_auth0(
    client: AsyncClient, fake_redis
):
    """
    After 5 requests for the same email the Auth0 call is suppressed,
    but the endpoint still returns 200 (non-enumeration guarantee).
    """
    app.state.redis = fake_redis
    email = "target@example.com"

    with patch(
        "src.auth.router.trigger_auth0_password_reset", AsyncMock()
    ) as mock_reset:
        # First 5 requests should call Auth0.
        for _ in range(5):
            r = await client.post(
                "/api/v1/auth/forgot-password", json={"email": email}
            )
            assert r.status_code == 200

        assert mock_reset.call_count == 5

        # Requests 6-8: IP limit not reached yet (only 5 used), but per-email
        # guard should suppress the Auth0 call.
        for _ in range(3):
            r = await client.post(
                "/api/v1/auth/forgot-password", json={"email": email}
            )
            assert r.status_code == 200  # still 200, not 429

        # Auth0 should still only have been called 5 times.
        assert mock_reset.call_count == 5


# ── IP limit — admin login ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_login_rate_limited_after_10(client: AsyncClient, fake_redis):
    """11th request on /admin/auth/login → 429."""
    app.state.redis = fake_redis

    for _ in range(10):
        await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "admin@studybuddy.app", "password": "wrong"},
        )

    r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "admin@studybuddy.app", "password": "wrong"},
    )
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


# ── IP limit — admin forgot-password ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_forgot_password_rate_limited_after_10(
    client: AsyncClient, fake_redis
):
    """11th request on /admin/auth/forgot-password → 429."""
    app.state.redis = fake_redis

    for _ in range(10):
        await client.post(
            "/api/v1/admin/auth/forgot-password",
            json={"email": f"{uuid.uuid4()}@internal.com"},
        )

    r = await client.post(
        "/api/v1/admin/auth/forgot-password",
        json={"email": "admin@internal.com"},
    )
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


# ── IP limit — admin reset-password ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_reset_password_rate_limited_after_10(
    client: AsyncClient, fake_redis
):
    """11th request on /admin/auth/reset-password → 429."""
    app.state.redis = fake_redis

    for _ in range(10):
        await client.post(
            "/api/v1/admin/auth/reset-password",
            json={"token": "bad-token", "new_password": "NewPass123!"},
        )

    r = await client.post(
        "/api/v1/admin/auth/reset-password",
        json={"token": "bad-token", "new_password": "NewPass123!"},
    )
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


# ── Rate limit resets per test (fresh fake_redis) ─────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_counter_is_isolated_per_test(client: AsyncClient, fake_redis):
    """
    Each test gets a fresh fakeredis, so the counter starts at 0.
    A single request should never be rate-limited.
    """
    app.state.redis = fake_redis

    mock_claims = {
        "sub": f"auth0|{uuid.uuid4()}",
        "email": "fresh@example.com",
        "name": "Fresh",
        "https://studybuddy.app/grade": 8,
        "locale": "en",
        "aud": "test-student-client-id",
    }

    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=mock_claims)):
        r = await client.post("/api/v1/auth/exchange", json={"id_token": "tok"})
        assert r.status_code == 200
