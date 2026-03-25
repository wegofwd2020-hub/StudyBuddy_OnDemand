"""
backend/src/subscription/router.py

Subscription and payment endpoints.

Routes (all prefixed /api/v1 in main.py):
  GET    /subscription/status    → SubscriptionStatusResponse
  POST   /subscription/checkout  → CheckoutResponse
  POST   /subscription/webhook   → 200  (Stripe webhook — no JWT required)
  DELETE /subscription           → CancelResponse

Security:
  GET/POST/DELETE subscription routes require a valid student JWT.
  POST /subscription/webhook validates the Stripe signature instead of JWT.
  Webhook always returns 200 to Stripe even on processing errors (avoids retries
  for events we've already logged as errors).

Idempotency:
  Webhook handler checks stripe_events table before processing.
  Returns 200 immediately if already processed.

Performance:
  Stripe API calls are made synchronously (Stripe SDK is sync).
  For production load, consider wrapping in run_in_executor.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.auth.dependencies import get_current_student
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.subscription.schemas import (
    CancelResponse,
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionStatusResponse,
)
from src.subscription.service import (
    activate_subscription,
    already_processed,
    cancel_stripe_subscription,
    cancel_subscription_db,
    create_checkout_session,
    expire_entitlement_cache,
    get_subscription_status,
    handle_payment_failed,
    log_stripe_event,
    update_subscription_status,
)
from src.utils.logger import get_logger

log = get_logger("subscription")
router = APIRouter(tags=["subscription"])


# ── GET /subscription/status ──────────────────────────────────────────────────

@router.get("/subscription/status", response_model=SubscriptionStatusResponse, status_code=200)
async def subscription_status(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> SubscriptionStatusResponse:
    """Return the current subscription plan and status for the authenticated student."""
    student_id = student["student_id"]

    async with get_db(request) as conn:
        data = await get_subscription_status(conn, student_id)

    return SubscriptionStatusResponse(**data)


# ── POST /subscription/checkout ───────────────────────────────────────────────

@router.post("/subscription/checkout", response_model=CheckoutResponse, status_code=200)
async def checkout(
    request: Request,
    body: CheckoutRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> CheckoutResponse:
    """
    Create a Stripe Checkout Session and return the hosted checkout URL.

    The mobile app opens this URL in a browser / in-app WebView.
    On success, Stripe calls POST /subscription/webhook with checkout.session.completed.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    try:
        url = await create_checkout_session(
            student_id=student_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except RuntimeError as exc:
        # Stripe not configured or price ID missing
        log.error("checkout_failed student_id=%s error=%s correlation_id=%s", student_id, exc, cid)
        raise HTTPException(
            status_code=503,
            detail={"error": "payment_unavailable", "detail": str(exc), "correlation_id": cid},
        )
    except Exception as exc:
        log.error("checkout_stripe_error student_id=%s error=%s correlation_id=%s", student_id, exc, cid)
        raise HTTPException(
            status_code=502,
            detail={"error": "stripe_error", "detail": "Could not create checkout session.", "correlation_id": cid},
        )

    return CheckoutResponse(checkout_url=url)


# ── POST /subscription/webhook ────────────────────────────────────────────────

@router.post("/subscription/webhook", status_code=200)
async def stripe_webhook(request: Request) -> dict:
    """
    Stripe webhook endpoint.

    Security:
      1. Validates Stripe-Signature header — rejects with 400 on failure.
      2. Deduplicates by stripe_event_id — returns 200 if already processed.
      3. Logs every event to stripe_events table.

    Always returns 200 to Stripe after signature verification so Stripe
    does not retry unnecessarily. Processing errors are logged but don't
    change the HTTP response code.

    Note: this endpoint does NOT use get_current_student — it is authenticated
    via the Stripe webhook signature only.
    """
    from config import settings

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not webhook_secret:
        log.error("stripe_webhook_secret_not_configured")
        raise HTTPException(status_code=503, detail={"error": "webhook_not_configured"})

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # ── Signature verification (CLAUDE.md non-negotiable rule #8) ─────────────
    try:
        stripe_mod = _get_stripe_module()
        event = stripe_mod.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as exc:
        log.warning("stripe_signature_invalid error=%s", exc)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_signature", "detail": "Stripe webhook signature verification failed."},
        )

    stripe_event_id = event["id"]
    event_type = event["type"]

    redis = get_redis(request)

    async with get_db(request) as conn:
        # ── Deduplication (CLAUDE.md non-negotiable rule #9) ──────────────────
        if await already_processed(conn, stripe_event_id):
            log.info("stripe_event_already_processed event_id=%s", stripe_event_id)
            return {"status": "already_processed"}

        # ── Dispatch to handler ───────────────────────────────────────────────
        error_detail = None
        try:
            await _dispatch_event(conn, redis, event_type, event["data"]["object"], event)
            outcome = "ok"
        except Exception as exc:
            log.error(
                "stripe_event_handler_failed event_id=%s event_type=%s error=%s",
                stripe_event_id, event_type, exc,
            )
            outcome = "error"
            error_detail = str(exc)

        await log_stripe_event(conn, stripe_event_id, event_type, outcome, error_detail)

    return {"status": "ok"}


async def _dispatch_event(conn, redis, event_type: str, obj: dict, event: dict) -> None:
    """Route a Stripe event to the correct handler."""
    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        student_id = metadata.get("student_id")
        plan = metadata.get("plan")
        if not student_id or not plan:
            log.warning("checkout.session.completed missing metadata student_id=%s plan=%s", student_id, plan)
            return

        stripe_customer_id = obj.get("customer", "")
        stripe_subscription_id = obj.get("subscription", "")

        # Retrieve current_period_end from the subscription object
        current_period_end = None
        try:
            stripe_mod = _get_stripe_module()
            from config import settings
            stripe_mod.api_key = settings.STRIPE_SECRET_KEY
            sub = stripe_mod.Subscription.retrieve(stripe_subscription_id)
            import datetime as _dt
            current_period_end = _dt.datetime.fromtimestamp(
                sub["current_period_end"], tz=_dt.timezone.utc
            )
        except Exception as exc:
            log.warning("could_not_fetch_subscription_period error=%s", exc)

        await activate_subscription(
            conn, redis,
            student_id=student_id,
            plan=plan,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            current_period_end=current_period_end,
        )

    elif event_type == "customer.subscription.updated":
        stripe_subscription_id = obj.get("id", "")
        raw_status = obj.get("status", "active")
        # Map Stripe statuses to our schema
        status = _map_stripe_status(raw_status)

        import datetime as _dt
        period_end_ts = obj.get("current_period_end")
        current_period_end = (
            _dt.datetime.fromtimestamp(period_end_ts, tz=_dt.timezone.utc)
            if period_end_ts else None
        )

        await update_subscription_status(conn, redis, stripe_subscription_id, status, current_period_end)

    elif event_type == "customer.subscription.deleted":
        stripe_subscription_id = obj.get("id", "")
        await cancel_subscription_db(conn, redis, stripe_subscription_id)

    elif event_type == "invoice.payment_failed":
        stripe_subscription_id = obj.get("subscription", "")
        if stripe_subscription_id:
            await handle_payment_failed(conn, redis, stripe_subscription_id)

    else:
        log.debug("stripe_event_unhandled event_type=%s", event_type)


def _map_stripe_status(stripe_status: str) -> str:
    """Map a Stripe subscription status to our internal status."""
    mapping = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "cancelled",
        "cancelled": "cancelled",
        "unpaid": "past_due",
        "trialing": "active",
    }
    return mapping.get(stripe_status, "active")


def _get_stripe_module():
    try:
        import stripe  # type: ignore
        return stripe
    except ImportError:
        raise RuntimeError("stripe package not installed")


# ── DELETE /subscription ──────────────────────────────────────────────────────

@router.delete("/subscription", response_model=CancelResponse, status_code=200)
async def cancel_subscription(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> CancelResponse:
    """
    Cancel the student's subscription at the end of the current billing period.

    The student retains access until current_period_end.
    Entitlement cache is expired immediately.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id, current_period_end
            FROM subscriptions
            WHERE student_id = $1 AND status = 'active'
            LIMIT 1
            """,
            student_id,
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "no_active_subscription", "detail": "No active subscription found.", "correlation_id": cid},
        )

    stripe_sub_id = row["stripe_subscription_id"]
    current_period_end = row["current_period_end"]

    try:
        await cancel_stripe_subscription(stripe_sub_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "payment_unavailable", "detail": str(exc), "correlation_id": cid},
        )
    except Exception as exc:
        log.error("cancel_subscription_stripe_error student_id=%s error=%s", student_id, exc)
        raise HTTPException(
            status_code=502,
            detail={"error": "stripe_error", "detail": "Could not cancel subscription.", "correlation_id": cid},
        )

    # Expire the entitlement cache so next request reflects the cancellation
    await expire_entitlement_cache(redis, student_id)

    return CancelResponse(
        status="cancelled_at_period_end",
        current_period_end=current_period_end.isoformat() if current_period_end else None,
    )
