"""
backend/src/school/subscription_router.py

School subscription endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST   /schools/{school_id}/subscription/checkout  — initiate Stripe checkout
  GET    /schools/{school_id}/subscription            — view subscription + seat usage
  DELETE /schools/{school_id}/subscription            — cancel (at period end)

Auth: teacher or school_admin JWT.  school_id in path must match JWT school_id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.school.subscription_service import (
    cancel_school_stripe_subscription,
    cancel_school_subscription_db,
    create_school_checkout_session,
    expire_school_entitlement_cache,
    get_school_subscription_status,
)
from src.utils.logger import get_logger

log = get_logger("school.subscription")
router = APIRouter(tags=["school-subscription"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class SchoolCheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in ("starter", "professional", "enterprise"):
            raise ValueError("plan must be 'starter', 'professional', or 'enterprise'")
        return v


class SchoolCheckoutResponse(BaseModel):
    checkout_url: str


class SchoolSubscriptionStatusResponse(BaseModel):
    plan: str
    status: str | None = None
    max_students: int = 0
    max_teachers: int = 0
    seats_used_students: int = 0
    seats_used_teachers: int = 0
    current_period_end: str | None = None


class SchoolSubscriptionCancelResponse(BaseModel):
    status: str
    current_period_end: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_school_match(teacher: dict, school_id: str, request: Request) -> None:
    """Raise 403 if the JWT school_id does not match the path school_id."""
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot access subscription for a different school.",
                "correlation_id": _cid(request),
            },
        )


# ── POST /schools/{school_id}/subscription/checkout ──────────────────────────


@router.post(
    "/schools/{school_id}/subscription/checkout",
    response_model=SchoolCheckoutResponse,
    status_code=200,
)
async def school_subscription_checkout(
    school_id: str,
    body: SchoolCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolCheckoutResponse:
    """
    Create a Stripe Checkout Session for a school subscription.

    Returns the Stripe-hosted checkout URL.
    On success, Stripe calls POST /subscription/webhook with checkout.session.completed.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can initiate subscription checkout.",
                "correlation_id": _cid(request),
            },
        )

    try:
        url = await create_school_checkout_session(
            school_id=school_id,
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
        log.error("school_checkout_error school_id=%s error=%s", school_id, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create checkout session.",
                "correlation_id": _cid(request),
            },
        )

    return SchoolCheckoutResponse(checkout_url=url)


# ── GET /schools/{school_id}/subscription ────────────────────────────────────


@router.get(
    "/schools/{school_id}/subscription",
    response_model=SchoolSubscriptionStatusResponse,
    status_code=200,
)
async def school_subscription_status(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolSubscriptionStatusResponse:
    """Return the school subscription plan, status, and seat usage."""
    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        data = await get_school_subscription_status(conn, school_id)

    return SchoolSubscriptionStatusResponse(**data)


# ── DELETE /schools/{school_id}/subscription ──────────────────────────────────


@router.delete(
    "/schools/{school_id}/subscription",
    response_model=SchoolSubscriptionCancelResponse,
    status_code=200,
)
async def school_subscription_cancel(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolSubscriptionCancelResponse:
    """
    Cancel the school's subscription at the end of the current billing period.

    Access is retained until current_period_end.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can cancel the subscription.",
                "correlation_id": _cid(request),
            },
        )

    redis = get_redis(request)

    async with get_db(request) as conn:
        import uuid as _uuid
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id, current_period_end
            FROM school_subscriptions
            WHERE school_id = $1 AND status IN ('active', 'trialing', 'past_due')
            """,
            _uuid.UUID(school_id),
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_active_subscription",
                "detail": "No active school subscription found.",
                "correlation_id": _cid(request),
            },
        )

    stripe_sub_id = row["stripe_subscription_id"]
    current_period_end = row["current_period_end"]

    try:
        await cancel_school_stripe_subscription(stripe_sub_id)
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
        log.error("school_cancel_stripe_error school_id=%s error=%s", school_id, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not cancel subscription.",
                "correlation_id": _cid(request),
            },
        )

    await expire_school_entitlement_cache(redis, school_id)

    return SchoolSubscriptionCancelResponse(
        status="cancelled_at_period_end",
        current_period_end=current_period_end.isoformat() if current_period_end else None,
    )
