"""
backend/src/teacher/subscription_router.py

Independent teacher subscription endpoints (#57, #105).

Routes (all prefixed /api/v1 in main.py):
  POST   /teachers/{teacher_id}/subscription/checkout  — start Stripe checkout
  GET    /teachers/{teacher_id}/subscription            — status + seat usage
  PATCH  /teachers/{teacher_id}/subscription/plan      — upgrade / downgrade plan
  DELETE /teachers/{teacher_id}/subscription            — cancel at period end

Auth: teacher JWT required.  teacher_id in path must match JWT.
      Only teachers with school_id IS NULL may subscribe (school-affiliated
      teachers are covered by their school's plan).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.pricing import VALID_TEACHER_PLAN_IDS
from src.teacher.subscription_service import (
    cancel_teacher_stripe_subscription,
    cancel_teacher_subscription_db,
    create_teacher_checkout_session,
    get_teacher_subscription_status,
    upgrade_teacher_plan,
)
from src.utils.logger import get_logger

log = get_logger("teacher.subscription")
router = APIRouter(tags=["teacher-subscription"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class TeacherCheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in VALID_TEACHER_PLAN_IDS:
            raise ValueError(f"plan must be one of {sorted(VALID_TEACHER_PLAN_IDS)}")
        return v


class TeacherCheckoutResponse(BaseModel):
    checkout_url: str


class TeacherSubscriptionStatusResponse(BaseModel):
    plan: str
    status: str | None = None
    max_students: int = 0
    seats_used_students: int = 0
    current_period_end: str | None = None
    over_quota: bool = False
    over_quota_since: str | None = None


class TeacherPlanUpgradeRequest(BaseModel):
    new_plan: str

    @field_validator("new_plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in VALID_TEACHER_PLAN_IDS:
            raise ValueError(f"plan must be one of {sorted(VALID_TEACHER_PLAN_IDS)}")
        return v


class TeacherPlanUpgradeResponse(BaseModel):
    plan: str
    max_students: int
    over_quota: bool = False


class TeacherSubscriptionCancelResponse(BaseModel):
    status: str
    current_period_end: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_teacher_match(teacher: dict, teacher_id: str, request: Request) -> None:
    if teacher.get("teacher_id") != teacher_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot access subscription for a different teacher.",
                "correlation_id": _cid(request),
            },
        )


def _assert_independent(teacher: dict, request: Request) -> None:
    """Reject school-affiliated teachers — their plan is covered by the school."""
    if teacher.get("school_id"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "school_affiliated",
                "detail": (
                    "This teacher is affiliated with a school. "
                    "Subscription is managed by the school admin."
                ),
                "correlation_id": _cid(request),
            },
        )


# ── POST /teachers/{teacher_id}/subscription/checkout ────────────────────────


@router.post(
    "/teachers/{teacher_id}/subscription/checkout",
    response_model=TeacherCheckoutResponse,
    status_code=200,
)
async def teacher_subscription_checkout(
    teacher_id: str,
    body: TeacherCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherCheckoutResponse:
    """
    Create a Stripe Checkout Session (mode=subscription) for an independent teacher.

    Returns the Stripe-hosted checkout URL.  On successful payment the webhook
    activates the subscription and sets teacher.teacher_plan.

    Only teachers with no school affiliation (school_id IS NULL) may use this.
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    try:
        url = await create_teacher_checkout_session(
            teacher_id=teacher_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": _cid(request),
            },
        )
    except Exception as exc:
        log.error("teacher_checkout_error teacher_id=%s error=%s", teacher_id, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create checkout session.",
                "correlation_id": _cid(request),
            },
        )

    return TeacherCheckoutResponse(checkout_url=url)


# ── GET /teachers/{teacher_id}/subscription ───────────────────────────────────


@router.get(
    "/teachers/{teacher_id}/subscription",
    response_model=TeacherSubscriptionStatusResponse,
    status_code=200,
)
async def teacher_subscription_status(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherSubscriptionStatusResponse:
    """Return current subscription plan, status, seat cap, and seats used."""
    _assert_teacher_match(teacher, teacher_id, request)

    async with get_db(request) as conn:
        status = await get_teacher_subscription_status(conn, teacher_id)

    return TeacherSubscriptionStatusResponse(**status)


# ── PATCH /teachers/{teacher_id}/subscription/plan ───────────────────────────


@router.patch(
    "/teachers/{teacher_id}/subscription/plan",
    response_model=TeacherPlanUpgradeResponse,
    status_code=200,
)
async def upgrade_teacher_subscription_plan(
    teacher_id: str,
    body: TeacherPlanUpgradeRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherPlanUpgradeResponse:
    """
    Upgrade or downgrade an independent teacher's subscription plan mid-cycle.

    Swaps the Stripe subscription price with pro-rata adjustment and updates
    the DB row.  Clears any over_quota flag — the daily Beat task re-evaluates
    within 24 h against the new max_students limit.

    Returns the new plan details immediately; the invoice for pro-rated amounts
    is issued asynchronously by Stripe.

    HTTP 404 — no active subscription found.
    HTTP 409 — requested plan is already the current plan.
    HTTP 503 — Stripe or config unavailable.
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT plan, stripe_subscription_id
            FROM teacher_subscriptions
            WHERE teacher_id = $1::uuid AND status NOT IN ('cancelled')
            """,
            teacher_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "No active subscription found.",
                "correlation_id": _cid(request),
            },
        )

    if row["plan"] == body.new_plan:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_on_plan",
                "detail": f"Already subscribed to the '{body.new_plan}' plan.",
                "correlation_id": _cid(request),
            },
        )

    if not row["stripe_subscription_id"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_stripe_subscription",
                "detail": "Subscription has no Stripe ID — cannot modify plan.",
                "correlation_id": _cid(request),
            },
        )

    try:
        async with get_db(request) as conn:
            await upgrade_teacher_plan(
                conn=conn,
                teacher_id=teacher_id,
                new_plan=body.new_plan,
                stripe_subscription_id=row["stripe_subscription_id"],
            )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": _cid(request),
            },
        )
    except Exception as exc:
        log.error(
            "teacher_plan_upgrade_error teacher_id=%s new_plan=%s error=%s",
            teacher_id, body.new_plan, exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not upgrade plan.",
                "correlation_id": _cid(request),
            },
        )

    from src.pricing import get_teacher_plan as _get_plan
    new_plan_obj = _get_plan(body.new_plan)
    log.info(
        "teacher_plan_upgraded teacher_id=%s new_plan=%s",
        teacher_id, body.new_plan,
    )
    return TeacherPlanUpgradeResponse(
        plan=body.new_plan,
        max_students=new_plan_obj.max_students,
        over_quota=False,
    )


# ── DELETE /teachers/{teacher_id}/subscription ────────────────────────────────


@router.delete(
    "/teachers/{teacher_id}/subscription",
    response_model=TeacherSubscriptionCancelResponse,
    status_code=200,
)
async def cancel_teacher_subscription(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherSubscriptionCancelResponse:
    """
    Cancel the teacher's subscription at the end of the current billing period.

    The teacher retains access until current_period_end.
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id, current_period_end
            FROM teacher_subscriptions
            WHERE teacher_id = $1::uuid AND status NOT IN ('cancelled')
            """,
            teacher_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "No active subscription found.",
                "correlation_id": _cid(request),
            },
        )

    try:
        await cancel_teacher_stripe_subscription(row["stripe_subscription_id"])
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": _cid(request),
            },
        )

    async with get_db(request) as conn:
        await cancel_teacher_subscription_db(conn, teacher_id)

    valid_until = row["current_period_end"].isoformat() if row["current_period_end"] else None
    log.info("teacher_subscription_cancelled teacher_id=%s", teacher_id)
    return TeacherSubscriptionCancelResponse(
        status="cancelled_at_period_end",
        current_period_end=valid_until,
    )
