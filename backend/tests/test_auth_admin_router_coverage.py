"""
tests/test_auth_admin_router_coverage.py

Targeted coverage of src/auth/admin_router.py — next-round PR B of #261.

Covers the branches at 0% on main:
  - L117                  — admin_login suspended 403
  - L180-205              — admin_refresh body (happy, 401 invalid token,
                             401 inactive user)
  - L233-239              — admin_forgot_password success branch
                             (reset token stored for existing admin)
  - L258-289              — admin_reset_password body (happy path,
                             invalid-token 400)
"""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.auth.service import hash_password


async def _create_admin(
    client: AsyncClient,
    *,
    account_status: str = "active",
    email_suffix: str | None = None,
) -> dict:
    pool = client._transport.app.state.pool
    suffix = email_suffix or uuid.uuid4().hex[:8]
    email = f"admincov_{suffix}@example.com"
    password = "correct-horse-battery-staple-1!"
    hashed = await hash_password(password)
    row = await pool.fetchrow(
        """
        INSERT INTO admin_users (email, password_hash, role, account_status)
        VALUES ($1, $2, 'product_admin', $3)
        RETURNING admin_user_id, email
        """,
        email,
        hashed,
        account_status,
    )
    return {
        "admin_user_id": str(row["admin_user_id"]),
        "email": email,
        "password": password,
    }


# ── admin_login suspended branch ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_login_suspended_returns_403(client: AsyncClient, fake_redis):
    """Suspended admin on valid creds → 403 account_suspended (L117)."""
    client._transport.app.state.redis = fake_redis
    admin = await _create_admin(client, account_status="suspended")

    r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin["email"], "password": admin["password"]},
    )

    assert r.status_code == 403
    assert r.json()["error"] == "account_suspended"


# ── admin_refresh ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_refresh_happy_path(client: AsyncClient, fake_redis):
    client._transport.app.state.redis = fake_redis
    admin = await _create_admin(client)

    # Install a refresh token → admin_id mapping in fake redis.
    refresh_token = "admin-rt-happy-99"
    rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await fake_redis.set(f"admin_refresh:{rt_hash}", admin["admin_user_id"])

    r = await client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert r.status_code == 200, r.text
    assert "token" in r.json()


@pytest.mark.asyncio
async def test_admin_refresh_invalid_token_returns_401(client: AsyncClient, fake_redis):
    client._transport.app.state.redis = fake_redis

    r = await client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": "not-in-redis"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_admin_refresh_inactive_user_returns_401(client: AsyncClient, fake_redis):
    """Refresh token valid but admin_users.account_status != 'active' → 401."""
    client._transport.app.state.redis = fake_redis
    admin = await _create_admin(client, account_status="suspended")

    refresh_token = "admin-rt-inactive-99"
    rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await fake_redis.set(f"admin_refresh:{rt_hash}", admin["admin_user_id"])

    r = await client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert r.status_code == 401


# ── admin_forgot_password success branch ──────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_forgot_password_stores_reset_token_for_existing_admin(
    client: AsyncClient, fake_redis
):
    """Existing admin → reset token stored in Redis with 1h TTL."""
    client._transport.app.state.redis = fake_redis
    admin = await _create_admin(client)

    r = await client.post(
        "/api/v1/admin/auth/forgot-password",
        json={"email": admin["email"]},
    )

    assert r.status_code == 200

    # At least one admin_reset:* key exists in redis pointing at this admin.
    keys: list[str] = []
    async for k in fake_redis.scan_iter(match="admin_reset:*"):
        keys.append(k if isinstance(k, str) else k.decode())
    assert keys, "expected at least one admin_reset:* key in fakeredis"

    found = False
    for k in keys:
        val = await fake_redis.get(k)
        if val == admin["admin_user_id"] or val == admin["admin_user_id"].encode():
            found = True
            break
    assert found, f"no admin_reset key mapped to admin_id={admin['admin_user_id']}"


@pytest.mark.asyncio
async def test_admin_forgot_password_nonexistent_email_still_200(
    client: AsyncClient, fake_redis
):
    """Unknown email → still 200 (non-enumeration) but no token stored."""
    client._transport.app.state.redis = fake_redis

    r = await client.post(
        "/api/v1/admin/auth/forgot-password",
        json={"email": "nobody-unknown@example.com"},
    )

    assert r.status_code == 200


# ── admin_reset_password ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_reset_password_happy_path(client: AsyncClient, fake_redis):
    """Valid reset token → password updated; token deleted after use."""
    client._transport.app.state.redis = fake_redis
    admin = await _create_admin(client)

    reset_token = "reset-tok-happy-99"
    await fake_redis.set(f"admin_reset:{reset_token}", admin["admin_user_id"])

    new_pw = "new-secure-password-2026!"

    with patch("src.auth.tasks.write_audit_log_task.delay", return_value=None):
        r = await client.post(
            "/api/v1/admin/auth/reset-password",
            json={"token": reset_token, "new_password": new_pw},
        )

    assert r.status_code == 200, r.text
    # Token deleted after use.
    assert await fake_redis.get(f"admin_reset:{reset_token}") is None

    # Password actually changed: the new password must verify.
    from src.auth.service import verify_password

    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT password_hash FROM admin_users WHERE admin_user_id = $1",
        admin["admin_user_id"],
    )
    assert await verify_password(new_pw, row["password_hash"])


@pytest.mark.asyncio
async def test_admin_reset_password_invalid_token_returns_400(
    client: AsyncClient, fake_redis
):
    client._transport.app.state.redis = fake_redis

    r = await client.post(
        "/api/v1/admin/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "new-secure-password-2026!"},
    )

    assert r.status_code == 400
    assert r.json()["error"] == "bad_request"
