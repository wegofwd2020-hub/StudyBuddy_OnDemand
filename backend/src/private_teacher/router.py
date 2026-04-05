"""
backend/src/private_teacher/router.py

Private teacher auth, subscription, and student-teacher access endpoints.

Routes (all prefixed /api/v1 in main.py):

  Auth (no bearer):
    POST /auth/private-teacher/register  → PrivateTeacherAuthResponse (201)
    POST /auth/private-teacher/login     → PrivateTeacherAuthResponse (200)

  Private teacher management (requires private_teacher JWT):
    GET    /private-teacher/me                         → PrivateTeacherProfile
    GET    /private-teacher/subscription               → TeacherSubscriptionStatus
    POST   /private-teacher/subscription/checkout      → TeacherCheckoutResponse
    DELETE /private-teacher/subscription               → TeacherCancelResponse

  Student-teacher access (requires student JWT):
    GET    /subscription/teacher-access                → AvailableTeachersResponse
    POST   /subscription/teacher-access/checkout       → TeacherAccessCheckoutResponse
    DELETE /subscription/teacher-access/{teacher_id}  → {status}

  Admin (requires admin JWT with school:manage permission):
    GET /admin/private-teachers  → {teachers: [...], total: int}
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.auth.dependencies import get_current_admin, get_current_private_teacher, get_current_student
from src.auth.service import create_internal_jwt, hash_password, verify_password
from src.core.db import get_db
from src.core.permissions import ROLE_PERMISSIONS
from src.core.redis_client import get_redis
from src.private_teacher.schemas import (
    AvailableTeachersResponse,
    PrivateTeacherAuthResponse,
    PrivateTeacherLoginRequest,
    PrivateTeacherProfile,
    PrivateTeacherRegisterRequest,
    TeacherAccessCheckoutRequest,
    TeacherAccessCheckoutResponse,
    TeacherCancelResponse,
    TeacherCheckoutRequest,
    TeacherCheckoutResponse,
    TeacherSubscriptionStatus,
)
from src.private_teacher.service import (
    cancel_student_teacher_access_db,
    create_student_teacher_access_checkout,
    create_teacher_checkout_session,
    get_available_teachers,
    get_private_teacher_by_email,
    get_private_teacher_by_id,
    get_teacher_subscription_status,
    list_admin_private_teachers,
    register_private_teacher,
)
from src.utils.logger import get_logger
from config import settings

log = get_logger("private_teacher")
router = APIRouter(tags=["private-teacher"])


# ── Admin RBAC helper (mirrors src/admin/router.py pattern) ──────────────────


def _require(permission: str):
    """Admin auth + permission check in one chained dependency."""

    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" not in perms and permission not in perms:
            log.warning(
                "permission_denied",
                role=role,
                required=permission,
                actor_id=admin.get("admin_id"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin

    return dep


# ── POST /auth/private-teacher/register ──────────────────────────────────────


@router.post(
    "/auth/private-teacher/register",
    response_model=PrivateTeacherAuthResponse,
    status_code=201,
)
async def register(
    request: Request,
    body: PrivateTeacherRegisterRequest,
) -> PrivateTeacherAuthResponse:
    """Register a new private teacher account and return a JWT."""
    cid = getattr(request.state, "correlation_id", "")

    password_hash = await hash_password(body.password)

    async with get_db(request) as conn:
        try:
            teacher = await register_private_teacher(
                conn, body.email, body.name, password_hash
            )
        except ValueError as exc:
            if str(exc) == "email_taken":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "Email is already registered.",
                        "correlation_id": cid,
                    },
                )
            raise

    token = create_internal_jwt(
        {
            "teacher_id": teacher["teacher_id"],
            "role": "private_teacher",
            "account_status": "active",
        },
        settings.JWT_SECRET,
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    log.info("private_teacher_registered", teacher_id=teacher["teacher_id"])
    return PrivateTeacherAuthResponse(token=token, teacher_id=teacher["teacher_id"])


# ── POST /auth/private-teacher/login ─────────────────────────────────────────


@router.post(
    "/auth/private-teacher/login",
    response_model=PrivateTeacherAuthResponse,
    status_code=200,
)
async def login(
    request: Request,
    body: PrivateTeacherLoginRequest,
) -> PrivateTeacherAuthResponse:
    """Authenticate a private teacher and return a JWT."""
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        teacher = await get_private_teacher_by_email(conn, body.email)

    if not teacher:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Invalid email or password.",
                "correlation_id": cid,
            },
        )

    if not await verify_password(body.password, teacher["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Invalid email or password.",
                "correlation_id": cid,
            },
        )

    token = create_internal_jwt(
        {
            "teacher_id": teacher["teacher_id"],
            "role": "private_teacher",
            "account_status": teacher["account_status"],
        },
        settings.JWT_SECRET,
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    log.info("private_teacher_login", teacher_id=teacher["teacher_id"])
    return PrivateTeacherAuthResponse(token=token, teacher_id=teacher["teacher_id"])


# ── GET /private-teacher/me ───────────────────────────────────────────────────


@router.get(
    "/private-teacher/me",
    response_model=PrivateTeacherProfile,
    status_code=200,
)
async def get_profile(
    request: Request,
    teacher: Annotated[dict, Depends(get_current_private_teacher)],
) -> PrivateTeacherProfile:
    """Return the authenticated private teacher's profile."""
    cid = getattr(request.state, "correlation_id", "")
    teacher_id = teacher["teacher_id"]

    async with get_db(request) as conn:
        row = await get_private_teacher_by_id(conn, teacher_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Teacher not found.",
                "correlation_id": cid,
            },
        )

    return PrivateTeacherProfile(
        teacher_id=row["teacher_id"],
        email=row["email"],
        name=row["name"],
        account_status=row["account_status"],
        created_at=row["created_at"].isoformat(),
    )


# ── GET /private-teacher/subscription ────────────────────────────────────────


@router.get(
    "/private-teacher/subscription",
    response_model=TeacherSubscriptionStatus,
    status_code=200,
)
async def get_subscription(
    request: Request,
    teacher: Annotated[dict, Depends(get_current_private_teacher)],
) -> TeacherSubscriptionStatus:
    """Return the authenticated private teacher's subscription status."""
    async with get_db(request) as conn:
        data = await get_teacher_subscription_status(conn, teacher["teacher_id"])
    return TeacherSubscriptionStatus(**data)


# ── POST /private-teacher/subscription/checkout ───────────────────────────────


@router.post(
    "/private-teacher/subscription/checkout",
    response_model=TeacherCheckoutResponse,
    status_code=200,
)
async def teacher_checkout(
    request: Request,
    body: TeacherCheckoutRequest,
    teacher: Annotated[dict, Depends(get_current_private_teacher)],
) -> TeacherCheckoutResponse:
    """Create a Stripe Checkout Session for the teacher's chosen plan."""
    cid = getattr(request.state, "correlation_id", "")

    if body.plan not in ("basic", "pro"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "detail": "plan must be 'basic' or 'pro'.",
                "correlation_id": cid,
            },
        )

    try:
        url = await create_teacher_checkout_session(
            teacher["teacher_id"], body.plan, body.success_url, body.cancel_url
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": cid,
            },
        )

    return TeacherCheckoutResponse(checkout_url=url)


# ── DELETE /private-teacher/subscription ─────────────────────────────────────


@router.delete(
    "/private-teacher/subscription",
    response_model=TeacherCancelResponse,
    status_code=200,
)
async def cancel_teacher_subscription(
    request: Request,
    teacher: Annotated[dict, Depends(get_current_private_teacher)],
) -> TeacherCancelResponse:
    """Cancel the teacher's Stripe subscription at the end of the billing period."""
    cid = getattr(request.state, "correlation_id", "")
    teacher_id = teacher["teacher_id"]

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id FROM teacher_subscriptions
            WHERE teacher_id = $1 AND status IN ('active', 'trialing')
            LIMIT 1
            """,
            __import__("uuid").UUID(teacher_id),
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_active_subscription",
                "detail": "No active subscription found.",
                "correlation_id": cid,
            },
        )

    stripe_sub_id = row["stripe_subscription_id"]
    if stripe_sub_id and settings.STRIPE_SECRET_KEY:
        try:
            import stripe  # type: ignore

            stripe.api_key = settings.STRIPE_SECRET_KEY
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        except Exception as exc:
            log.error("teacher_cancel_stripe_error teacher_id=%s error=%s", teacher_id, exc)

    return TeacherCancelResponse(status="cancelled_at_period_end")


# ── GET /subscription/teacher-access ─────────────────────────────────────────


@router.get(
    "/subscription/teacher-access",
    response_model=AvailableTeachersResponse,
    status_code=200,
)
async def list_available_teachers(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> AvailableTeachersResponse:
    """Return a list of private teachers with active subscriptions."""
    async with get_db(request) as conn:
        teachers = await get_available_teachers(conn)
    return AvailableTeachersResponse(teachers=teachers)


# ── POST /subscription/teacher-access/checkout ───────────────────────────────


@router.post(
    "/subscription/teacher-access/checkout",
    response_model=TeacherAccessCheckoutResponse,
    status_code=200,
)
async def student_teacher_access_checkout(
    request: Request,
    body: TeacherAccessCheckoutRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> TeacherAccessCheckoutResponse:
    """Create a Stripe Checkout Session for the student to access a teacher's content."""
    cid = getattr(request.state, "correlation_id", "")
    student_id = str(student["student_id"])

    try:
        url = await create_student_teacher_access_checkout(
            student_id, body.teacher_id, body.success_url, body.cancel_url
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": cid,
            },
        )

    return TeacherAccessCheckoutResponse(checkout_url=url)


# ── DELETE /subscription/teacher-access/{teacher_id} ─────────────────────────


@router.delete(
    "/subscription/teacher-access/{teacher_id}",
    status_code=200,
)
async def cancel_student_teacher_access(
    request: Request,
    teacher_id: str,
    student: Annotated[dict, Depends(get_current_student)],
) -> dict:
    """Cancel the student's access to a private teacher's content."""
    cid = getattr(request.state, "correlation_id", "")
    student_id = str(student["student_id"])
    redis = get_redis(request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id FROM student_teacher_access
            WHERE student_id = $1 AND teacher_id = $2 AND status = 'active'
            """,
            __import__("uuid").UUID(student_id),
            __import__("uuid").UUID(teacher_id),
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "No active teacher access found.",
                "correlation_id": cid,
            },
        )

    stripe_sub_id = row["stripe_subscription_id"]
    if stripe_sub_id and settings.STRIPE_SECRET_KEY:
        try:
            import stripe  # type: ignore

            stripe.api_key = settings.STRIPE_SECRET_KEY
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        except Exception as exc:
            log.error(
                "student_teacher_cancel_stripe_error student_id=%s error=%s", student_id, exc
            )

    async with get_db(request) as conn:
        await cancel_student_teacher_access_db(conn, redis, stripe_sub_id or "")

    return {"status": "cancelled"}


# ── GET /admin/private-teachers ───────────────────────────────────────────────


@router.get(
    "/admin/private-teachers",
    status_code=200,
)
async def admin_list_private_teachers(
    request: Request,
    admin: Annotated[dict, Depends(_require("school:manage"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> dict:
    """List all private teachers with subscription info. Requires school:manage permission."""
    async with get_db(request) as conn:
        result = await list_admin_private_teachers(conn, page, page_size, search)
    return result
