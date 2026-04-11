"""
backend/src/teacher/connect_router.py

Stripe Connect (Express) onboarding and earnings endpoints — Option B (#104).

Routes (all prefixed /api/v1 in app_factory.py):
  POST   /teachers/{teacher_id}/connect/onboard   — create Express account + onboarding link
  GET    /teachers/{teacher_id}/connect/status     — Connect account status
  POST   /teachers/{teacher_id}/connect/refresh    — re-generate expired onboarding link
  GET    /teachers/{teacher_id}/connect/earnings   — transfer history (from Stripe)

Auth: teacher JWT required.  teacher_id in path must match JWT.
      Only independent teachers (school_id IS NULL) may use these endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.teacher.connect_service import (
    create_connect_account,
    create_onboarding_link,
    create_student_checkout_session,
    get_connect_account,
    get_earnings,
    sync_connect_account,
)
from src.utils.logger import get_logger

log = get_logger("teacher.connect")
router = APIRouter(tags=["teacher-connect"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ConnectOnboardResponse(BaseModel):
    stripe_account_id: str
    onboarding_url: str


class ConnectStatusResponse(BaseModel):
    has_connect_account: bool
    stripe_account_id: str | None = None
    onboarding_complete: bool = False
    charges_enabled: bool = False
    payouts_enabled: bool = False


class ConnectRefreshResponse(BaseModel):
    onboarding_url: str


class EarningsItem(BaseModel):
    transfer_id: str
    amount_cents: int
    currency: str
    created: int          # Unix timestamp
    description: str


class StudentCheckoutRequest(BaseModel):
    student_id: str
    success_url: str
    cancel_url: str


class StudentCheckoutResponse(BaseModel):
    checkout_url: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_teacher_match(teacher: dict, teacher_id: str, request: Request) -> None:
    if teacher.get("teacher_id") != teacher_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot access Connect account for a different teacher.",
                "correlation_id": _cid(request),
            },
        )


def _assert_independent(teacher: dict, request: Request) -> None:
    if teacher.get("school_id"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "school_affiliated",
                "detail": (
                    "This teacher is affiliated with a school. "
                    "Revenue-share billing is only available to independent teachers."
                ),
                "correlation_id": _cid(request),
            },
        )


def _build_return_url(request: Request, teacher_id: str) -> str:
    """Derive a return URL from the request's base URL."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/teacher/billing/connect/return"


def _build_refresh_url(request: Request, teacher_id: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/teachers/{teacher_id}/connect/refresh"


# ── POST /teachers/{teacher_id}/connect/onboard ───────────────────────────────


@router.post(
    "/teachers/{teacher_id}/connect/onboard",
    response_model=ConnectOnboardResponse,
    status_code=200,
)
async def teacher_connect_onboard(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ConnectOnboardResponse:
    """
    Create a Stripe Express Connect account (if one doesn't exist) and return
    the onboarding link.

    If a Connect account already exists but onboarding is incomplete, a fresh
    onboarding link is returned for the existing account.

    On first call: creates the account and stores it in teacher_connect_accounts.
    On subsequent calls before onboarding completes: returns a fresh link.
    After onboarding: the link still works to manage payout details.
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    async with get_db(request) as conn:
        existing = await get_connect_account(conn, teacher_id)

    if existing:
        stripe_account_id = existing["stripe_account_id"]
    else:
        email = teacher.get("email", "")
        try:
            stripe_account_id = await create_connect_account(teacher_id, email)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "payment_unavailable",
                    "detail": str(exc),
                    "correlation_id": _cid(request),
                },
            )
        # Persist the new account row (pre-onboarding, capabilities not yet enabled).
        async with get_db(request) as conn:
            await sync_connect_account(
                conn, teacher_id, stripe_account_id,
                charges_enabled=False, payouts_enabled=False,
            )

    try:
        onboarding_url = await create_onboarding_link(
            teacher_id,
            stripe_account_id,
            return_url=_build_return_url(request, teacher_id),
            refresh_url=_build_refresh_url(request, teacher_id),
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

    return ConnectOnboardResponse(
        stripe_account_id=stripe_account_id,
        onboarding_url=onboarding_url,
    )


# ── GET /teachers/{teacher_id}/connect/status ─────────────────────────────────


@router.get(
    "/teachers/{teacher_id}/connect/status",
    response_model=ConnectStatusResponse,
    status_code=200,
)
async def teacher_connect_status(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ConnectStatusResponse:
    """Return the Connect account state for the teacher portal dashboard."""
    _assert_teacher_match(teacher, teacher_id, request)

    async with get_db(request) as conn:
        row = await get_connect_account(conn, teacher_id)

    if row is None:
        return ConnectStatusResponse(has_connect_account=False)

    return ConnectStatusResponse(
        has_connect_account=True,
        stripe_account_id=row["stripe_account_id"],
        onboarding_complete=row["onboarding_complete"],
        charges_enabled=row["charges_enabled"],
        payouts_enabled=row["payouts_enabled"],
    )


# ── POST /teachers/{teacher_id}/connect/refresh ───────────────────────────────


@router.post(
    "/teachers/{teacher_id}/connect/refresh",
    response_model=ConnectRefreshResponse,
    status_code=200,
)
async def teacher_connect_refresh(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ConnectRefreshResponse:
    """
    Re-generate an expired or used Stripe onboarding link.

    Stripe AccountLinks are single-use and expire after ~5 minutes.  Call this
    endpoint when the teacher is redirected back to /connect/refresh (the URL
    passed to Stripe as refresh_url).
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    async with get_db(request) as conn:
        row = await get_connect_account(conn, teacher_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "No Connect account found. Call /onboard first.",
                "correlation_id": _cid(request),
            },
        )

    try:
        onboarding_url = await create_onboarding_link(
            teacher_id,
            row["stripe_account_id"],
            return_url=_build_return_url(request, teacher_id),
            refresh_url=_build_refresh_url(request, teacher_id),
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

    return ConnectRefreshResponse(onboarding_url=onboarding_url)


# ── GET /teachers/{teacher_id}/connect/earnings ───────────────────────────────


@router.get(
    "/teachers/{teacher_id}/connect/earnings",
    response_model=list[EarningsItem],
    status_code=200,
)
async def teacher_connect_earnings(
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    limit: int = Query(default=25, ge=1, le=100),
) -> list[EarningsItem]:
    """
    Return recent Stripe Transfer objects destined for the teacher's Connect
    account.  The frontend renders these as the teacher's earnings history.
    """
    _assert_teacher_match(teacher, teacher_id, request)

    async with get_db(request) as conn:
        row = await get_connect_account(conn, teacher_id)

    if row is None or not row.get("stripe_account_id"):
        return []

    try:
        transfers = await get_earnings(row["stripe_account_id"], limit=limit)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "payment_unavailable",
                "detail": str(exc),
                "correlation_id": _cid(request),
            },
        )

    return [EarningsItem(**t) for t in transfers]


# ── POST /teachers/{teacher_id}/connect/student-checkout ──────────────────────


@router.post(
    "/teachers/{teacher_id}/connect/student-checkout",
    response_model=StudentCheckoutResponse,
    status_code=200,
)
async def teacher_connect_student_checkout(
    teacher_id: str,
    body: StudentCheckoutRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> StudentCheckoutResponse:
    """
    Create a Stripe Checkout Session for a student enrolling under an Option-B
    teacher.

    Only callable by the teacher themselves (not the student directly) — the
    teacher initiates enrollment and shares the checkout link with the student,
    or it is presented at student sign-up time.

    The session uses application_fee_percent and transfer_data so Stripe handles
    the revenue split automatically.
    """
    _assert_teacher_match(teacher, teacher_id, request)
    _assert_independent(teacher, request)

    async with get_db(request) as conn:
        row = await get_connect_account(conn, teacher_id)

    if row is None or not row.get("charges_enabled"):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "connect_not_ready",
                "detail": (
                    "Your Stripe Connect account is not yet active. "
                    "Complete onboarding before accepting student payments."
                ),
                "correlation_id": _cid(request),
            },
        )

    try:
        checkout_url = await create_student_checkout_session(
            teacher_id=teacher_id,
            student_id=body.student_id,
            stripe_account_id=row["stripe_account_id"],
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

    return StudentCheckoutResponse(checkout_url=checkout_url)
