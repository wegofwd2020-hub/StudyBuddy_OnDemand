"""
backend/src/auth/dependencies.py

FastAPI dependencies for extracting and validating the current user from
the Authorization: Bearer header.

Three separate dependencies enforce the two-track auth model:
  get_current_student — verifies JWT_SECRET; rejects teacher/admin tokens
  get_current_teacher — verifies JWT_SECRET; rejects student/admin tokens
  get_current_admin   — verifies ADMIN_JWT_SECRET; rejects student/teacher tokens

Each dependency also:
  - Checks Redis for suspended:{id} key (no DB query on hot path)
  - Checks account_status field in the JWT payload
  - Stores the payload on request.state.jwt_payload (used by require_permission)
"""

from __future__ import annotations

from typing import Annotated

from config import settings
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.service import verify_internal_jwt
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("dependencies")

_bearer = HTTPBearer(auto_error=True)


def _get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


async def get_current_student(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    """
    Verify a student JWT and return the decoded payload.

    Raises:
        401 — missing / invalid / expired token
        403 — account suspended or pending
    """
    cid = _get_correlation_id(request)
    payload = verify_internal_jwt(credentials.credentials, settings.JWT_SECRET)

    role = payload.get("role", "")
    if role not in ("student", "demo_student"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Student token required.",
                "correlation_id": cid,
            },
        )

    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "detail": "student_id missing from token.",
                "correlation_id": cid,
            },
        )

    # Check Redis suspension key (no TTL — key must be explicitly deleted).
    redis = get_redis(request)
    if await redis.exists(f"suspended:{student_id}"):
        log.warning("student_suspended", student_id=student_id)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_suspended",
                "detail": "Your account has been suspended.",
                "correlation_id": cid,
            },
        )

    # For demo students: check logout blacklist (JTI blacklisted on explicit logout).
    if role == "demo_student":
        jti = payload.get("jti")
        if jti and await redis.exists(f"demo_blacklist:{jti}"):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthenticated",
                    "detail": "Token has been revoked.",
                    "correlation_id": cid,
                },
            )

    account_status = payload.get("account_status", "active")
    if account_status == "pending":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_pending",
                "detail": "Account is pending email verification.",
                "correlation_id": cid,
            },
        )
    if account_status == "deleted":
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Account has been deleted.",
                "correlation_id": cid,
            },
        )

    request.state.jwt_payload = payload
    return payload


async def get_current_teacher(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    """
    Verify a teacher JWT and return the decoded payload.
    Teacher and school_admin roles are both issued via /auth/teacher/exchange.
    """
    cid = _get_correlation_id(request)
    payload = verify_internal_jwt(credentials.credentials, settings.JWT_SECRET)

    role = payload.get("role", "")
    if role not in ("teacher", "school_admin"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Teacher or school_admin token required.",
                "correlation_id": cid,
            },
        )

    teacher_id = payload.get("teacher_id")
    if not teacher_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "detail": "teacher_id missing from token.",
                "correlation_id": cid,
            },
        )

    redis = get_redis(request)
    if await redis.exists(f"suspended:{teacher_id}"):
        log.warning("teacher_suspended", teacher_id=teacher_id)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_suspended",
                "detail": "Your account has been suspended.",
                "correlation_id": cid,
            },
        )

    account_status = payload.get("account_status", "active")
    if account_status in ("pending",):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_pending",
                "detail": "Account pending verification.",
                "correlation_id": cid,
            },
        )

    request.state.jwt_payload = payload
    return payload


async def get_current_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    """
    Verify an admin JWT (signed with ADMIN_JWT_SECRET) and return the payload.
    Admin tokens must never be accepted on student/teacher endpoints.
    """
    cid = _get_correlation_id(request)
    payload = verify_internal_jwt(credentials.credentials, settings.ADMIN_JWT_SECRET)

    role = payload.get("role", "")
    if role not in ("developer", "tester", "product_admin", "super_admin"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Admin token required.",
                "correlation_id": cid,
            },
        )

    request.state.jwt_payload = payload
    return payload
