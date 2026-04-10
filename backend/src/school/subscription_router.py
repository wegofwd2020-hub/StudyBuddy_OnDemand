"""
backend/src/school/subscription_router.py

School subscription endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST   /schools/{school_id}/subscription/checkout  — initiate Stripe checkout
  GET    /schools/{school_id}/subscription            — view subscription + seat usage
  DELETE /schools/{school_id}/subscription            — cancel (at period end)

  Phase G — retention billing:
  POST   /schools/{school_id}/curriculum/versions/{curriculum_id}/renewal-checkout
         — create a one-time Stripe payment to renew a curriculum version
  POST   /schools/{school_id}/storage/checkout
         — create a one-time Stripe payment to purchase storage add-on (5/10/25 GB)

  #106 — pay-per-build:
  POST   /schools/{school_id}/pipeline/extra-build-checkout
         — $15 one-time Stripe payment for one extra grade build credit

  #107 — credit bundles:
  POST   /schools/{school_id}/pipeline/credits-checkout
         — one-time Stripe payment for 3/10/25 build credits ($39/$119/$269)

Auth: school_admin JWT only for billing endpoints.  school_id in path must match JWT.
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
    create_credits_bundle_checkout_session,
    create_extra_build_checkout_session,
    create_renewal_checkout_session,
    create_school_checkout_session,
    create_storage_checkout_session,
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


class RenewalCheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str


class StorageCheckoutRequest(BaseModel):
    gb_package: int
    success_url: str
    cancel_url: str

    @field_validator("gb_package")
    @classmethod
    def valid_package(cls, v: int) -> int:
        if v not in (5, 10, 25):
            raise ValueError("gb_package must be 5, 10, or 25")
        return v


class ExtraBuildCheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str


class CreditsBundleCheckoutRequest(BaseModel):
    bundle_size: int          # 3, 10, or 25
    success_url: str
    cancel_url: str

    @field_validator("bundle_size")
    @classmethod
    def valid_bundle(cls, v: int) -> int:
        if v not in (3, 10, 25):
            raise ValueError("bundle_size must be 3, 10, or 25")
        return v


class SchoolSubscriptionStatusResponse(BaseModel):
    plan: str
    status: str | None = None
    max_students: int = 0
    max_teachers: int = 0
    seats_used_students: int = 0
    seats_used_teachers: int = 0
    current_period_end: str | None = None
    # Build allowance (Option A — absorbed into plan)
    builds_included: int = 0          # -1 = unlimited (Enterprise)
    builds_used: int = 0
    builds_remaining: int = 0         # -1 = unlimited
    builds_period_end: str | None = None
    # Rollover credit balance (Options B/C — never expires)
    builds_credits_balance: int = 0


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


# ── POST /schools/{school_id}/curriculum/versions/{curriculum_id}/renewal-checkout


@router.post(
    "/schools/{school_id}/curriculum/versions/{curriculum_id}/renewal-checkout",
    response_model=SchoolCheckoutResponse,
    status_code=200,
)
async def curriculum_renewal_checkout(
    school_id: str,
    curriculum_id: str,
    body: RenewalCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolCheckoutResponse:
    """
    Create a Stripe Checkout Session (mode=payment) to pay for curriculum renewal.

    On successful payment, Stripe delivers a checkout.session.completed webhook with
    product_type='curriculum_renewal' in metadata.  The webhook handler then calls
    handle_curriculum_renewal_payment() to extend expires_at by 1 year.

    This endpoint validates that the curriculum exists and belongs to this school
    before creating the Stripe session.  It does NOT renew the curriculum immediately
    — renewal is applied by the webhook to ensure payment was received first.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can initiate renewal checkout.",
                "correlation_id": _cid(request),
            },
        )

    # Verify curriculum belongs to school and is renewable.
    async with get_db(request) as conn:
        cur = await conn.fetchrow(
            """
            SELECT curriculum_id, grade, retention_status
            FROM curricula
            WHERE curriculum_id = $1
              AND school_id = $2::uuid
              AND owner_type = 'school'
            """,
            curriculum_id, school_id,
        )

    if cur is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Curriculum version not found.",
                "correlation_id": _cid(request),
            },
        )

    if cur["retention_status"] == "purged":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_purged",
                "detail": (
                    "This curriculum version has been permanently purged and "
                    "cannot be renewed. Upload a new curriculum JSON and rebuild."
                ),
                "correlation_id": _cid(request),
            },
        )

    try:
        url = await create_renewal_checkout_session(
            school_id=school_id,
            curriculum_id=curriculum_id,
            grade=cur["grade"],
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
        log.error(
            "renewal_checkout_error school_id=%s curriculum_id=%s error=%s",
            school_id, curriculum_id, exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create renewal checkout session.",
                "correlation_id": _cid(request),
            },
        )

    log.info(
        "renewal_checkout_created school_id=%s curriculum_id=%s grade=%d",
        school_id, curriculum_id, cur["grade"],
    )
    return SchoolCheckoutResponse(checkout_url=url)


# ── POST /schools/{school_id}/storage/checkout ────────────────────────────────


@router.post(
    "/schools/{school_id}/storage/checkout",
    response_model=SchoolCheckoutResponse,
    status_code=200,
)
async def storage_addon_checkout(
    school_id: str,
    body: StorageCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolCheckoutResponse:
    """
    Create a Stripe Checkout Session (mode=payment) to purchase a storage add-on.

    gb_package must be 5, 10, or 25 — maps to the corresponding Stripe price ID.
    On successful payment, the webhook increments school_storage_quotas.purchased_gb.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can purchase storage add-ons.",
                "correlation_id": _cid(request),
            },
        )

    try:
        url = await create_storage_checkout_session(
            school_id=school_id,
            gb_package=body.gb_package,
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
        log.error(
            "storage_checkout_error school_id=%s gb=%d error=%s",
            school_id, body.gb_package, exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create storage checkout session.",
                "correlation_id": _cid(request),
            },
        )

    log.info(
        "storage_checkout_created school_id=%s gb_package=%d",
        school_id, body.gb_package,
    )
    return SchoolCheckoutResponse(checkout_url=url)


# ── POST /schools/{school_id}/pipeline/extra-build-checkout (#106) ────────────


@router.post(
    "/schools/{school_id}/pipeline/extra-build-checkout",
    response_model=SchoolCheckoutResponse,
    status_code=200,
)
async def extra_build_checkout(
    school_id: str,
    body: ExtraBuildCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolCheckoutResponse:
    """
    Create a Stripe Checkout Session (mode=payment) for one extra grade build.

    Price: $15.  Adds 1 credit to builds_credits_balance on payment, which can
    be consumed the next time the school triggers a pipeline build beyond their
    plan allowance.

    Only school_admin may initiate this purchase.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can purchase extra builds.",
                "correlation_id": _cid(request),
            },
        )

    try:
        url = await create_extra_build_checkout_session(
            school_id=school_id,
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
        log.error("extra_build_checkout_error school_id=%s error=%s", school_id, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create extra build checkout session.",
                "correlation_id": _cid(request),
            },
        )

    log.info("extra_build_checkout_created school_id=%s", school_id)
    return SchoolCheckoutResponse(checkout_url=url)


# ── POST /schools/{school_id}/pipeline/credits-checkout (#107) ────────────────


@router.post(
    "/schools/{school_id}/pipeline/credits-checkout",
    response_model=SchoolCheckoutResponse,
    status_code=200,
)
async def credits_bundle_checkout(
    school_id: str,
    body: CreditsBundleCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolCheckoutResponse:
    """
    Create a Stripe Checkout Session (mode=payment) for a build credit bundle.

    bundle_size must be 3, 10, or 25 (priced at $39 / $119 / $269).
    Credits roll over — they never expire.
    On payment, builds_credits_balance is incremented by bundle_size.

    Only school_admin may initiate this purchase.
    """
    _assert_school_match(teacher, school_id, request)

    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can purchase credit bundles.",
                "correlation_id": _cid(request),
            },
        )

    try:
        url = await create_credits_bundle_checkout_session(
            school_id=school_id,
            bundle_size=body.bundle_size,
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
        log.error(
            "credits_bundle_checkout_error school_id=%s bundle_size=%d error=%s",
            school_id, body.bundle_size, exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "stripe_error",
                "detail": "Could not create credits checkout session.",
                "correlation_id": _cid(request),
            },
        )

    log.info(
        "credits_bundle_checkout_created school_id=%s bundle_size=%d",
        school_id, body.bundle_size,
    )
    return SchoolCheckoutResponse(checkout_url=url)
