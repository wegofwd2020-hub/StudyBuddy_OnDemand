"""
backend/src/demo/teacher_router.py

Demo teacher endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /demo/teacher/request               — submit email → receive verification link
  GET  /demo/teacher/verify/{token}        — verify email → create account + receive credentials
  POST /demo/teacher/auth/login            — email + password → JWT (role=demo_teacher)
  POST /demo/teacher/auth/logout           — invalidate demo teacher JWT (Redis blacklist)
  POST /demo/teacher/verify/resend         — resend verification email (cooldown enforced)

Auth model:
  Demo teachers receive a JWT with role="demo_teacher" signed with JWT_SECRET.
  No refresh token — demo accounts are short-lived (48h by default).
  Logout blacklists the JTI in Redis for the remainder of the token's TTL.

Rate limiting:
  POST /demo/teacher/request       — 3 per IP per hour  (Redis: demo_teacher_req:{ip})
  POST /demo/teacher/verify/resend — cooldown per email (Redis: demo_teacher_resend:{email})
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
    send_demo_teacher_credentials_email_task,
    send_demo_teacher_verification_email_task,
)
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.demo.schemas import DemoLoginInput, DemoLoginResponse, DemoRequestInput, DemoResendInput
from src.demo.teacher_service import (
    _generate_demo_teacher_password,
    count_active_demo_teachers,
    create_demo_teacher_and_account,
    create_demo_teacher_request,
    create_demo_teacher_verification,
    get_active_demo_teacher_account_by_email,
    get_demo_teacher_account_for_login,
    get_pending_teacher_verification_by_email,
    get_teacher_verification_by_token,
    mark_teacher_request_verified,
    mark_teacher_verification_used,
    replace_teacher_verification_token,
    update_demo_teacher_last_login,
)
from src.utils.logger import get_logger

log = get_logger("demo.teacher")
router = APIRouter(tags=["demo-teacher"])

_bearer = HTTPBearer(auto_error=True)

_REQ_RATE_PREFIX = "demo_teacher_req:"
_RESEND_COOLDOWN_PREFIX = "demo_teacher_resend:"
_BLACKLIST_PREFIX = "demo_teacher_blacklist:"

_REQ_RATE_LIMIT = 3
_REQ_RATE_WINDOW = 3600  # 1 hour


# ── POST /demo/teacher/request ────────────────────────────────────────────────


@router.post("/demo/teacher/request", status_code=200)
async def request_teacher_demo(body: DemoRequestInput, request: Request):
    """
    Submit an email address to request a teacher demo account.

    Sends a verification link to the provided email.
    Rate-limited to 3 requests per IP per hour.
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{_REQ_RATE_PREFIX}{client_ip}"
    count_raw = await redis.get(rate_key)
    count = int(count_raw) if count_raw else 0
    if count >= _REQ_RATE_LIMIT:
        log.warning("demo_teacher_request_rate_limited", ip=client_ip, email=body.email)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many demo requests. Please try again in an hour.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        existing = await get_active_demo_teacher_account_by_email(conn, body.email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "demo_already_active",
                    "detail": "A teacher demo account for this email is already active.",
                    "correlation_id": cid,
                },
            )

        pending = await get_pending_teacher_verification_by_email(conn, body.email)
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
        request_id = await create_demo_teacher_request(conn, body.email, client_ip, user_agent)
        token = await create_demo_teacher_verification(conn, request_id, body.email)

    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, _REQ_RATE_WINDOW)
    await pipe.execute()

    try:
        send_demo_teacher_verification_email_task.delay(body.email, token)
    except Exception as exc:
        log.error(
            "demo_teacher_verification_email_dispatch_failed",
            email=body.email,
            error=str(exc),
        )

    log.info("demo_teacher_request_created", email=body.email, ip=client_ip)
    return {"message": "Verification email sent. Please check your inbox."}


# ── GET /demo/teacher/verify/{token} ─────────────────────────────────────────


@router.get("/demo/teacher/verify/{token}", status_code=200)
async def verify_demo_teacher_email(token: str, request: Request):
    """
    Verify a teacher email address via the token from the verification link.

    Creates the demo teacher account and emails login credentials.
    """
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        row = await get_teacher_verification_by_token(conn, token)

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

        # Advisory lock key for demo teacher capacity (pre-computed stable int for
        # "demo_teacher_verify_capacity").
        DEMO_TEACHER_LOCK_KEY = 1_742_381_905

        email = row["email"]
        request_id = row["request_id"]
        plain_password = _generate_demo_teacher_password()
        password_hash = await hash_password(plain_password)

        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock($1)", DEMO_TEACHER_LOCK_KEY)

            active_count = await count_active_demo_teachers(conn)
            if active_count >= settings.DEMO_TEACHER_MAX_ACTIVE:
                log.warning("demo_teacher_max_active_reached", count=active_count)
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "demo_capacity_reached",
                        "detail": "All teacher demo slots are currently occupied. Please try again later.",
                        "correlation_id": cid,
                    },
                )

            await create_demo_teacher_and_account(
                conn,
                request_id=request_id,
                email=email,
                password_hash=password_hash,
            )
            await mark_teacher_verification_used(conn, row["verif_id"])
            await mark_teacher_request_verified(conn, request_id)

    try:
        send_demo_teacher_credentials_email_task.delay(email, plain_password)
    except Exception as exc:
        log.error(
            "demo_teacher_credentials_email_dispatch_failed",
            email=email,
            error=str(exc),
        )

    log.info("demo_teacher_account_created", email=email)
    return {
        "message": "Account created. Login credentials have been sent to your email."
    }


# ── POST /demo/teacher/auth/login ─────────────────────────────────────────────


@router.post("/demo/teacher/auth/login", response_model=DemoLoginResponse)
async def demo_teacher_login(body: DemoLoginInput, request: Request):
    """
    Authenticate a demo teacher with email + password.

    Returns a short-lived JWT (role=demo_teacher).
    """
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        account = await get_demo_teacher_account_for_login(conn, body.email)

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

        await update_demo_teacher_last_login(conn, account["id"])
        expires_at = account["expires_at"]

    expires_at_aware = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    remaining_minutes = int((expires_at_aware - datetime.now(UTC)).total_seconds() / 60)
    token_ttl = min(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, remaining_minutes)
    if token_ttl <= 0:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Demo teacher account has expired.",
                "correlation_id": cid,
            },
        )

    token = create_internal_jwt(
        payload={
            "teacher_id": str(account["teacher_id"]),
            "school_id": None,
            "role": "demo_teacher",
            "account_status": "active",
            "demo_account_id": str(account["id"]),
            "demo_expires_at": expires_at_aware.isoformat(),
        },
        secret=settings.JWT_SECRET,
        expire_minutes=token_ttl,
    )

    log.info("demo_teacher_login_success", email=body.email)
    return DemoLoginResponse(access_token=token, demo_expires_at=expires_at_aware)


# ── POST /demo/teacher/auth/logout ────────────────────────────────────────────


@router.post("/demo/teacher/auth/logout", status_code=200)
async def demo_teacher_logout(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
):
    """
    Log out a demo teacher by blacklisting the JWT JTI in Redis.
    """
    cid = getattr(request.state, "correlation_id", "")
    token = credentials.credentials

    try:
        payload = verify_internal_jwt(token, settings.JWT_SECRET)
    except HTTPException:
        return {"message": "Logged out."}

    if payload.get("role") != "demo_teacher":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Demo teacher token required.",
                "correlation_id": cid,
            },
        )

    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
        redis = get_redis(request)
        await redis.set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=ttl)

    log.info("demo_teacher_logout", teacher_id=payload.get("teacher_id"))
    return {"message": "Logged out."}


# ── POST /demo/teacher/verify/resend ─────────────────────────────────────────


@router.post("/demo/teacher/verify/resend", status_code=200)
async def resend_demo_teacher_verification(body: DemoResendInput, request: Request):
    """
    Resend the teacher verification email to a pending demo request.

    Enforces a per-email cooldown (default 5 minutes).
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

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
        pending = await get_pending_teacher_verification_by_email(conn, body.email)
        if pending is None:
            return {"message": "If a pending verification exists, it has been resent."}

        new_token = await replace_teacher_verification_token(
            conn, pending["request_id"], body.email
        )

    await redis.set(
        cooldown_key,
        "1",
        ex=settings.DEMO_RESEND_COOLDOWN_MINUTES * 60,
    )

    send_demo_teacher_verification_email_task.delay(body.email, new_token)

    log.info("demo_teacher_verification_resent", email=body.email)
    return {"message": "If a pending verification exists, it has been resent."}
