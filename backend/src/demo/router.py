"""
backend/src/demo/router.py

Demo student endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /demo/request               — submit email → receive verification link
  GET  /demo/verify/{token}        — verify email → create account + receive credentials
  POST /demo/auth/login            — email + password → JWT
  POST /demo/auth/logout           — invalidate demo JWT (client-side + Redis blacklist)
  POST /demo/verify/resend         — resend verification email (cooldown enforced)

Auth model:
  Demo students receive a JWT with role="demo_student" signed with JWT_SECRET.
  No refresh token — demo accounts are short-lived (24h by default).
  Logout blacklists the JTI in Redis for the remainder of the token's TTL.

Rate limiting:
  POST /demo/request  — 3 per IP per hour  (Redis: demo_req:{ip})
  POST /demo/verify/resend — cooldown per email (Redis: demo_resend:{email})
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from config import settings
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.service import (
    create_internal_jwt,
    hash_password,
    verify_internal_jwt,
    verify_password,
)
from src.auth.tasks import (
    send_demo_credentials_email_task,
    send_demo_verification_email_task,
)
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.demo.schemas import DemoLoginInput, DemoLoginResponse, DemoRequestInput, DemoResendInput
from src.demo.service import (
    _generate_demo_password,
    count_active_demos,
    create_demo_request,
    create_demo_student_and_account,
    create_demo_verification,
    get_active_demo_account_by_email,
    get_demo_account_for_login,
    get_pending_verification_by_email,
    get_verification_by_token,
    mark_request_verified,
    mark_verification_used,
    replace_verification_token,
    update_last_login,
)
from src.utils.logger import get_logger

log = get_logger("demo")
router = APIRouter(tags=["demo"])

_bearer = HTTPBearer(auto_error=True)

# Redis key helpers
_REQ_RATE_PREFIX = "demo_req:"
_RESEND_COOLDOWN_PREFIX = "demo_resend:"
_BLACKLIST_PREFIX = "demo_blacklist:"

_REQ_RATE_LIMIT = 3          # max requests per IP per window
_REQ_RATE_WINDOW = 3600      # 1 hour in seconds


# ── POST /demo/request ────────────────────────────────────────────────────────


@router.post("/demo/request", status_code=200)
async def request_demo(body: DemoRequestInput, request: Request):
    """
    Submit an email address to request a demo account.

    Sends a verification link to the provided email.
    Rate-limited to 3 requests per IP per hour.
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    # ── IP rate limiting ──
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{_REQ_RATE_PREFIX}{client_ip}"
    count_raw = await redis.get(rate_key)
    count = int(count_raw) if count_raw else 0
    if count >= _REQ_RATE_LIMIT:
        log.warning("demo_request_rate_limited", ip=client_ip, email=body.email)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many demo requests. Please try again in an hour.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        # ── Block if account already active for this email ──
        existing = await get_active_demo_account_by_email(conn, body.email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "demo_already_active",
                    "detail": "A demo account for this email is already active.",
                    "correlation_id": cid,
                },
            )

        # ── Block if verification is already pending (not expired, not used) ──
        pending = await get_pending_verification_by_email(conn, body.email)
        if pending:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "verification_pending",
                    "detail": "A verification email was already sent. Please check your inbox or use the resend option.",
                    "correlation_id": cid,
                },
            )

        user_agent = request.headers.get("user-agent")
        request_id = await create_demo_request(conn, body.email, client_ip, user_agent)
        token = await create_demo_verification(conn, request_id, body.email)

    # ── Increment rate limit counter ──
    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, _REQ_RATE_WINDOW)
    await pipe.execute()

    # ── Fire verification email task (fire-and-forget) ──
    send_demo_verification_email_task.delay(body.email, token)

    log.info("demo_request_created", email=body.email, ip=client_ip)
    return {"message": "Verification email sent. Please check your inbox."}


# ── GET /demo/verify/{token} ──────────────────────────────────────────────────


@router.get("/demo/verify/{token}", status_code=200)
async def verify_demo_email(token: str, request: Request):
    """
    Verify an email address via the token from the verification link.

    Creates the demo student account and emails login credentials.
    """
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        row = await get_verification_by_token(conn, token)

        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "token_not_found",
                    "detail": "Verification token is invalid.",
                    "correlation_id": cid,
                },
            )

        if row["used_at"] is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "token_already_used",
                    "detail": "This verification link has already been used.",
                    "correlation_id": cid,
                },
            )

        if row["expires_at"] < datetime.now(UTC):
            raise HTTPException(
                status_code=410,
                detail={
                    "error": "token_expired",
                    "detail": "This verification link has expired. Please request a new demo.",
                    "correlation_id": cid,
                },
            )

        if row["request_status"] == "verified":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_verified",
                    "detail": "This demo request has already been verified.",
                    "correlation_id": cid,
                },
            )

        # ── Check DEMO_MAX_ACTIVE cap ──
        active_count = await count_active_demos(conn)
        if active_count >= settings.DEMO_MAX_ACTIVE:
            log.warning("demo_max_active_reached", count=active_count)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "demo_capacity_reached",
                    "detail": "All demo slots are currently occupied. Please try again later.",
                    "correlation_id": cid,
                },
            )

        # ── Create student + account ──
        email = row["email"]
        request_id = row["request_id"]
        plain_password = _generate_demo_password()
        password_hash = await hash_password(plain_password)

        await create_demo_student_and_account(
            conn,
            request_id=request_id,
            email=email,
            from_password=plain_password,
            password_hash=password_hash,
        )
        await mark_verification_used(conn, row["verif_id"])
        await mark_request_verified(conn, request_id)

    # ── Fire credentials email task ──
    send_demo_credentials_email_task.delay(email, plain_password)

    log.info("demo_account_created", email=email)
    return {
        "message": "Account created. Login credentials have been sent to your email."
    }


# ── POST /demo/auth/login ─────────────────────────────────────────────────────


@router.post("/demo/auth/login", response_model=DemoLoginResponse)
async def demo_login(body: DemoLoginInput, request: Request):
    """
    Authenticate a demo student with email + password.

    Returns a short-lived JWT (role=demo_student).
    No refresh token — demo accounts are short-lived.
    """
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        account = await get_demo_account_for_login(conn, body.email)

        if account is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthenticated",
                    "detail": "Invalid credentials or account not found.",
                    "correlation_id": cid,
                },
            )

        password_ok = await verify_password(body.password, account["password_hash"])
        if not password_ok:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthenticated",
                    "detail": "Invalid credentials or account not found.",
                    "correlation_id": cid,
                },
            )

        await update_last_login(conn, account["id"])
        expires_at = account["expires_at"]

    # JWT TTL: lesser of 15 min or remaining demo lifetime
    expires_at_aware = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    remaining_minutes = int((expires_at_aware - datetime.now(UTC)).total_seconds() / 60)
    token_ttl = min(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, remaining_minutes)
    if token_ttl <= 0:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Demo account has expired.",
                "correlation_id": cid,
            },
        )

    token = create_internal_jwt(
        payload={
            "student_id": str(account["student_id"]),
            "grade": 8,
            "locale": "en",
            "role": "demo_student",
            "account_status": "active",
            "demo_account_id": str(account["id"]),
            "demo_expires_at": expires_at_aware.isoformat(),
        },
        secret=settings.JWT_SECRET,
        expire_minutes=token_ttl,
    )

    log.info("demo_login_success", email=body.email)
    return DemoLoginResponse(access_token=token, demo_expires_at=expires_at_aware)


# ── POST /demo/auth/logout ────────────────────────────────────────────────────


@router.post("/demo/auth/logout", status_code=200)
async def demo_logout(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
):
    """
    Log out a demo student by blacklisting the JWT JTI in Redis.

    The blacklist TTL matches the token's remaining lifetime so the key
    auto-expires without a background sweep.
    """
    cid = getattr(request.state, "correlation_id", "")
    token = credentials.credentials

    try:
        payload = verify_internal_jwt(token, settings.JWT_SECRET)
    except HTTPException:
        # Already invalid — logout is a no-op
        return {"message": "Logged out."}

    if payload.get("role") != "demo_student":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Demo student token required.",
                "correlation_id": cid,
            },
        )

    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
        redis = get_redis(request)
        await redis.set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=ttl)

    log.info("demo_logout", student_id=payload.get("student_id"))
    return {"message": "Logged out."}


# ── POST /demo/verify/resend ──────────────────────────────────────────────────


@router.post("/demo/verify/resend", status_code=200)
async def resend_demo_verification(body: DemoResendInput, request: Request):
    """
    Resend the verification email to a pending demo request.

    Enforces a per-email cooldown (default 5 minutes).
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    # ── Check cooldown ──
    cooldown_key = f"{_RESEND_COOLDOWN_PREFIX}{body.email}"
    if await redis.exists(cooldown_key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "resend_cooldown",
                "detail": f"Please wait {settings.DEMO_RESEND_COOLDOWN_MINUTES} minutes before resending.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        pending = await get_pending_verification_by_email(conn, body.email)
        if pending is None:
            # Return 200 to avoid leaking whether the email is registered
            return {"message": "If a pending verification exists, it has been resent."}

        new_token = await replace_verification_token(
            conn, pending["request_id"], body.email
        )

    # ── Set cooldown ──
    await redis.set(
        cooldown_key,
        "1",
        ex=settings.DEMO_RESEND_COOLDOWN_MINUTES * 60,
    )

    send_demo_verification_email_task.delay(body.email, new_token)

    log.info("demo_verification_resent", email=body.email)
    return {"message": "If a pending verification exists, it has been resent."}
