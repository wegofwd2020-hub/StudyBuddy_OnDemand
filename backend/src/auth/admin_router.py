"""
backend/src/auth/admin_router.py

Admin authentication routes (internal product team — local bcrypt track).

Routes:
  POST /admin/auth/login           — bcrypt verify → admin JWT
  POST /admin/auth/refresh         — admin refresh token → new JWT
  POST /admin/auth/forgot-password — one-time reset token in Redis (always 200)
  POST /admin/auth/reset-password  — consume token, set new password

All prefixed with /api/v1 in main.py.
"""

from __future__ import annotations

import secrets
import uuid

from config import settings
from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.schemas import (
    AdminForgotPasswordRequest,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminResetPasswordRequest,
    RefreshRequest,
    RefreshResponse,
)
from src.auth.service import (
    _hash_refresh_token,
    create_admin_jwt,
    generate_refresh_token,
    hash_password,
    verify_password,
)
from src.core.db import get_db
from src.core.events import emit_event, write_audit_log
from src.core.observability import auth_failures_total
from src.core.rate_limit import ip_auth_rate_limit
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("admin_auth")
router = APIRouter(tags=["admin-auth"])

_ADMIN_REFRESH_TTL = settings.ADMIN_JWT_EXPIRE_MINUTES * 60 * 24  # 24 hours for admin refresh
_RESET_TOKEN_TTL = 3600  # 1 hour
_LOCKOUT_ATTEMPTS = 5
_LOCKOUT_TTL = 900  # 15 minutes


# ── Admin login ───────────────────────────────────────────────────────────────


@router.post("/admin/auth/login", response_model=AdminLoginResponse)
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    _: None = Depends(ip_auth_rate_limit),
):
    """
    Authenticate an internal admin user with email + password.

    Lockout: 5 failures → 423 Locked for 15 minutes (Redis-backed).
    bcrypt verify runs in thread pool executor (non-blocking).
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)
    ip = request.client.host if request.client else "unknown"

    lockout_key = f"login_attempts:{body.email}"
    attempts_raw = await redis.get(lockout_key)
    attempts = int(attempts_raw) if attempts_raw else 0

    if attempts >= _LOCKOUT_ATTEMPTS:
        ttl = await redis.ttl(lockout_key)
        retry_after = max(ttl, 0)
        raise HTTPException(
            status_code=423,
            headers={"Retry-After": str(retry_after)},
            detail={
                "error": "rate_limited",
                "detail": f"Too many failed attempts. Retry after {retry_after} seconds.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        admin = await conn.fetchrow(
            """
            SELECT admin_user_id, email, password_hash, role, account_status
            FROM admin_users
            WHERE email = $1 AND account_status != 'deleted'
            """,
            str(body.email),
        )

    if admin is None or not await verify_password(body.password, admin["password_hash"]):
        auth_failures_total.labels(reason="bad_credentials").inc()
        # Increment lockout counter.
        pipe = redis.pipeline()
        pipe.incr(lockout_key)
        pipe.expire(lockout_key, _LOCKOUT_TTL)
        await pipe.execute()
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Invalid email or password.",
                "correlation_id": cid,
            },
        )

    if admin["account_status"] == "suspended":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_suspended",
                "detail": "Account suspended.",
                "correlation_id": cid,
            },
        )

    # Successful login — clear lockout counter.
    await redis.delete(lockout_key)

    # Update last_login_at.
    async with get_db(request) as conn:
        await conn.execute(
            "UPDATE admin_users SET last_login_at = NOW() WHERE admin_user_id = $1",
            admin["admin_user_id"],
        )

    admin_id = str(admin["admin_user_id"])
    token = create_admin_jwt(
        {
            "admin_id": admin_id,
            "role": admin["role"],
        }
    )

    # Issue refresh token for admin.
    refresh = generate_refresh_token()
    await redis.set(
        f"admin_refresh:{_hash_refresh_token(refresh)}",
        admin_id,
        ex=_ADMIN_REFRESH_TTL,
    )

    emit_event("auth", "admin_login", admin_id=admin_id, role=admin["role"])
    write_audit_log("admin_login", "admin", admin["admin_user_id"], ip_address=ip)

    return AdminLoginResponse(token=token, admin_id=admin["admin_user_id"])


# ── Admin refresh ─────────────────────────────────────────────────────────────


@router.post("/admin/auth/refresh", response_model=RefreshResponse)
async def admin_refresh(body: RefreshRequest, request: Request):
    """Exchange an admin refresh token for a new admin JWT."""
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    key = f"admin_refresh:{_hash_refresh_token(body.refresh_token)}"
    admin_id_bytes = await redis.get(key)
    if not admin_id_bytes:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Invalid or expired refresh token.",
                "correlation_id": cid,
            },
        )

    admin_id: str = admin_id_bytes.decode() if isinstance(admin_id_bytes, bytes) else admin_id_bytes

    async with get_db(request) as conn:
        admin = await conn.fetchrow(
            "SELECT admin_user_id, role, account_status FROM admin_users WHERE admin_user_id = $1",
            admin_id,
        )

    if not admin or admin["account_status"] != "active":
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Admin user not found or inactive.",
                "correlation_id": cid,
            },
        )

    token = create_admin_jwt(
        {
            "admin_id": str(admin["admin_user_id"]),
            "role": admin["role"],
        }
    )
    return RefreshResponse(token=token)


# ── Forgot password (always 200) ──────────────────────────────────────────────


@router.post("/admin/auth/forgot-password")
async def admin_forgot_password(
    body: AdminForgotPasswordRequest,
    request: Request,
    _: None = Depends(ip_auth_rate_limit),
):
    """
    Store a one-time reset token in Redis (TTL 1 hr).

    Always returns 200 — different responses leak registered emails.
    The reset link/token would normally be emailed; for Phase 1 it is
    returned in the logs only (email integration is Phase 2+).
    """
    redis = get_redis(request)

    async with get_db(request) as conn:
        admin = await conn.fetchrow(
            "SELECT admin_user_id FROM admin_users WHERE email = $1 AND account_status = 'active'",
            str(body.email),
        )

    if admin:
        reset_token = secrets.token_urlsafe(32)
        await redis.set(
            f"admin_reset:{reset_token}",
            str(admin["admin_user_id"]),
            ex=_RESET_TOKEN_TTL,
        )
        log.info(
            "admin_reset_token_issued",
            admin_id=str(admin["admin_user_id"]),
            # Do NOT log the token itself in production.
        )

    return {}


# ── Reset password ────────────────────────────────────────────────────────────


@router.post("/admin/auth/reset-password")
async def admin_reset_password(
    body: AdminResetPasswordRequest,
    request: Request,
    _: None = Depends(ip_auth_rate_limit),
):
    """Consume a one-time reset token and set a new password."""
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    key = f"admin_reset:{body.token}"
    admin_id_bytes = await redis.get(key)
    if not admin_id_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "detail": "Invalid or expired reset token.",
                "correlation_id": cid,
            },
        )

    admin_id: str = admin_id_bytes.decode() if isinstance(admin_id_bytes, bytes) else admin_id_bytes

    new_hash = await hash_password(body.new_password)

    async with get_db(request) as conn:
        await conn.execute(
            "UPDATE admin_users SET password_hash = $1 WHERE admin_user_id = $2",
            new_hash,
            admin_id,
        )

    # Delete the one-use token.
    await redis.delete(key)

    emit_event("auth", "admin_password_reset", admin_id=admin_id)
    write_audit_log("admin_password_reset", "admin", uuid.UUID(admin_id))
    return {}
