"""
backend/src/subscription/router.py

Stripe webhook endpoint — school and teacher subscriptions.

Routes (all prefixed /api/v1 in main.py):
  POST /subscription/webhook  → 200  (Stripe webhook — no JWT required)

Individual student subscription endpoints (status / checkout / cancel) were
removed in migration 0027 per ADR-001 Decision 2.

School billing:   src/school/subscription_router.py
Teacher billing:  src/teacher/subscription_router.py  (#57)

Security:
  POST /subscription/webhook validates the Stripe-Signature header.
  All other routes in the subscription domain are on the domain-specific routers.

Idempotency:
  Webhook handler checks stripe_events table before processing.
  Returns 200 immediately if already processed.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.core.db import get_db
from src.core.events import write_audit_log
from src.core.redis_client import get_redis
from src.core.stripe_async import run_stripe
from src.subscription.service import already_processed, log_stripe_event
from src.utils.logger import get_logger

log = get_logger("subscription")
router = APIRouter(tags=["subscription"])


# ── POST /subscription/webhook ────────────────────────────────────────────────


@router.post("/subscription/webhook", status_code=200)
async def stripe_webhook(request: Request) -> dict:
    """
    Stripe webhook endpoint — school subscriptions only.

    Security:
      1. Validates Stripe-Signature header — rejects with 400 on failure.
      2. Deduplicates by stripe_event_id — returns 200 if already processed.
      3. Logs every event to stripe_events table.

    Always returns 200 to Stripe after signature verification so Stripe
    does not retry unnecessarily.  Processing errors are logged but don't
    change the HTTP response code.
    """
    from config import settings

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not webhook_secret:
        log.error("stripe_webhook_secret_not_configured")
        raise HTTPException(status_code=503, detail={"error": "webhook_not_configured"})

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # ── Signature verification ────────────────────────────────────────────────
    # construct_event is CPU-bound (HMAC) — run in executor to keep the loop free.
    try:
        stripe_mod = _get_stripe_module()
        event = await run_stripe(stripe_mod.Webhook.construct_event, payload, sig_header, webhook_secret)
    except Exception as exc:
        log.warning("stripe_signature_invalid error=%s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_signature",
                "detail": "Stripe webhook signature verification failed.",
            },
        )

    stripe_event_id = event["id"]
    event_type = event["type"]
    redis = get_redis(request)

    async with get_db(request) as conn:
        # ── Deduplication ─────────────────────────────────────────────────────
        if await already_processed(conn, stripe_event_id):
            log.info("stripe_event_already_processed event_id=%s", stripe_event_id)
            return {"status": "already_processed"}

        # ── Dispatch ──────────────────────────────────────────────────────────
        error_detail = None
        try:
            await _dispatch_event(conn, redis, event_type, event["data"]["object"])
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


# ── Event dispatcher ───────────────────────────────────────────────────────��──


async def _dispatch_event(conn, redis, event_type: str, obj: dict) -> None:
    """Route a Stripe event to the appropriate subscription handler.

    Teacher subscription events are identified by product_type='teacher_subscription'
    in checkout.session.metadata or by matching stripe_subscription_id against
    teacher_subscriptions for lifecycle events.
    """
    # ── Teacher subscription events (#57) ─────────────────────────────────────
    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        if metadata.get("product_type") == "teacher_subscription":
            await _dispatch_teacher_checkout(conn, obj, metadata)
            return

    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_failed",
    ):
        stripe_sub_id = obj.get("id") or obj.get("subscription", "")
        if stripe_sub_id:
            from src.teacher.subscription_service import find_teacher_by_stripe_subscription
            teacher_id = await find_teacher_by_stripe_subscription(conn, stripe_sub_id)
            if teacher_id:
                await _dispatch_teacher_lifecycle(conn, event_type, obj, stripe_sub_id)
                return

    # ── School subscription events (existing) ─────────────────────────────────
    await _dispatch_school_event(conn, redis, event_type, obj)


async def _dispatch_teacher_checkout(conn, obj: dict, metadata: dict) -> None:
    """Handle checkout.session.completed for teacher_subscription product_type."""
    import datetime as _dt
    from src.teacher.subscription_service import handle_teacher_subscription_activated

    teacher_id = metadata.get("teacher_id", "")
    plan = metadata.get("plan", "")
    if not teacher_id or not plan:
        log.warning(
            "teacher_checkout.session.completed missing metadata "
            "teacher_id=%s plan=%s",
            teacher_id, plan,
        )
        return

    stripe_customer_id = obj.get("customer", "")
    stripe_subscription_id = obj.get("subscription", "")
    current_period_end = None

    try:
        stripe_mod = _get_stripe_module()
        from config import settings as _settings
        stripe_mod.api_key = _settings.STRIPE_SECRET_KEY
        sub = await run_stripe(stripe_mod.Subscription.retrieve, stripe_subscription_id)
        current_period_end = _dt.datetime.fromtimestamp(
            sub["current_period_end"], tz=_dt.UTC
        )
    except Exception as exc:
        log.warning("could_not_fetch_teacher_subscription_period error=%s", exc)

    await handle_teacher_subscription_activated(
        conn,
        teacher_id=teacher_id,
        plan=plan,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        current_period_end=current_period_end,
    )


async def _dispatch_teacher_lifecycle(
    conn, event_type: str, obj: dict, stripe_sub_id: str
) -> None:
    """Handle lifecycle events (updated / deleted / payment_failed) for teacher subscriptions."""
    import datetime as _dt
    from src.teacher.subscription_service import (
        handle_teacher_payment_failed,
        handle_teacher_subscription_deleted,
        handle_teacher_subscription_updated,
    )

    if event_type == "customer.subscription.updated":
        status = _map_stripe_status(obj.get("status", "active"))
        period_end_ts = obj.get("current_period_end")
        current_period_end = (
            _dt.datetime.fromtimestamp(period_end_ts, tz=_dt.UTC) if period_end_ts else None
        )
        await handle_teacher_subscription_updated(conn, stripe_sub_id, status, current_period_end)

    elif event_type == "customer.subscription.deleted":
        await handle_teacher_subscription_deleted(conn, stripe_sub_id)

    elif event_type == "invoice.payment_failed":
        await handle_teacher_payment_failed(conn, stripe_sub_id)


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


# ── School subscription event handlers ───────────────────────────────────────


async def _dispatch_school_event(conn, redis, event_type: str, obj: dict) -> None:
    """Route Stripe events to school subscription handlers."""
    from src.school.subscription_service import (
        activate_school_subscription,
        cancel_school_subscription_db,
        handle_school_payment_failed,
        update_school_subscription_status,
    )

    metadata = obj.get("metadata") or {}

    if event_type == "checkout.session.completed":
        school_id = metadata.get("school_id")
        product_type = metadata.get("product_type", "")

        # ── Phase G: curriculum renewal payment ───────────────────────────────
        if product_type == "curriculum_renewal":
            from src.school.subscription_service import handle_curriculum_renewal_payment

            curriculum_id = metadata.get("curriculum_id", "")
            if not school_id or not curriculum_id:
                log.warning(
                    "renewal_checkout.session.completed missing metadata "
                    "school_id=%s curriculum_id=%s",
                    school_id, curriculum_id,
                )
                return
            await handle_curriculum_renewal_payment(conn, school_id, curriculum_id)
            return

        # ── Phase G: storage add-on payment ───────────────────────────────────
        if product_type == "storage_addon":
            from src.school.subscription_service import handle_storage_addon_payment

            additional_gb_str = metadata.get("additional_gb", "0")
            try:
                additional_gb = int(additional_gb_str)
            except ValueError:
                log.warning(
                    "storage_addon_checkout.session.completed invalid additional_gb=%s",
                    additional_gb_str,
                )
                return
            if not school_id or additional_gb <= 0:
                log.warning(
                    "storage_addon_checkout.session.completed missing/invalid metadata "
                    "school_id=%s additional_gb=%d",
                    school_id, additional_gb,
                )
                return
            await handle_storage_addon_payment(conn, school_id, additional_gb)
            return

        # ── #106: extra build payment ($15 / one grade build) ─────────────────
        if product_type == "extra_build":
            from src.school.subscription_service import handle_extra_build_payment

            if not school_id:
                log.warning(
                    "extra_build_checkout.session.completed missing school_id in metadata"
                )
                return
            await handle_extra_build_payment(conn, school_id)
            return

        # ── #107: build credit bundle payment ─────────────────────────────────
        if product_type == "build_credits":
            from src.school.subscription_service import handle_credits_bundle_payment

            credits_str = metadata.get("credits", "0")
            try:
                credits = int(credits_str)
            except ValueError:
                log.warning(
                    "build_credits_checkout.session.completed invalid credits=%s",
                    credits_str,
                )
                return
            if not school_id or credits <= 0:
                log.warning(
                    "build_credits_checkout.session.completed missing/invalid metadata "
                    "school_id=%s credits=%d",
                    school_id, credits,
                )
                return
            await handle_credits_bundle_payment(conn, school_id, credits)
            return

        # ── School subscription (existing flow) ───────────────────────────────
        plan = metadata.get("plan")
        if not school_id or not plan:
            log.warning(
                "school_checkout.session.completed missing metadata school_id=%s plan=%s",
                school_id, plan,
            )
            return

        stripe_customer_id = obj.get("customer", "")
        stripe_subscription_id = obj.get("subscription", "")

        current_period_end = None
        try:
            stripe_mod = _get_stripe_module()
            from config import settings as _settings
            stripe_mod.api_key = _settings.STRIPE_SECRET_KEY
            sub = await run_stripe(stripe_mod.Subscription.retrieve, stripe_subscription_id)
            import datetime as _dt
            current_period_end = _dt.datetime.fromtimestamp(sub["current_period_end"], tz=_dt.UTC)
        except Exception as exc:
            log.warning("could_not_fetch_school_subscription_period error=%s", exc)

        await activate_school_subscription(
            conn, redis,
            school_id=school_id,
            plan=plan,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            current_period_end=current_period_end,
        )

    elif event_type == "customer.subscription.updated":
        stripe_subscription_id = obj.get("id", "")
        status = _map_stripe_status(obj.get("status", "active"))
        import datetime as _dt
        period_end_ts = obj.get("current_period_end")
        current_period_end = (
            _dt.datetime.fromtimestamp(period_end_ts, tz=_dt.UTC) if period_end_ts else None
        )
        await update_school_subscription_status(
            conn, redis, stripe_subscription_id, status, current_period_end
        )

    elif event_type == "customer.subscription.deleted":
        stripe_subscription_id = obj.get("id", "")
        await cancel_school_subscription_db(conn, redis, stripe_subscription_id)

    elif event_type == "invoice.payment_failed":
        stripe_subscription_id = obj.get("subscription", "")
        if stripe_subscription_id:
            await handle_school_payment_failed(conn, redis, stripe_subscription_id)

    elif event_type == "invoice.payment_action_required":
        await _handle_payment_action_required(conn, obj)

    else:
        log.debug("school_stripe_event_unhandled event_type=%s", event_type)


async def _handle_payment_action_required(conn, obj: dict) -> None:
    """
    Handle invoice.payment_action_required — fires when a European bank requires
    SCA / 3DS authentication before authorising a subscription payment.

    Resolves the school via stripe_subscription_id from school_subscriptions,
    then fetches the contact_email from schools.  Dispatches a Celery task
    to email the contact with the Stripe hosted_invoice_url so they can
    complete the 3DS challenge.  The audit log records the event for compliance.

    If the subscription is not found (e.g. a non-school invoice or setup-mode
    invoice before a subscription exists), the event is silently skipped —
    Stripe still receives a 200.
    """
    stripe_subscription_id: str = obj.get("subscription", "")
    action_url: str = obj.get("hosted_invoice_url", "")

    if not stripe_subscription_id:
        log.warning("payment_action_required_missing_subscription_id")
        return

    row = await conn.fetchrow(
        """
        SELECT ss.school_id, s.contact_email
        FROM school_subscriptions ss
        JOIN schools s ON s.school_id = ss.school_id
        WHERE ss.stripe_subscription_id = $1
        """,
        stripe_subscription_id,
    )

    if not row:
        log.info(
            "payment_action_required_school_not_found stripe_sub=%s",
            stripe_subscription_id,
        )
        return

    school_id = str(row["school_id"])
    contact_email: str = row["contact_email"]

    from src.auth.tasks import send_payment_action_required_email_task

    send_payment_action_required_email_task.delay(
        to_email=contact_email,
        action_url=action_url,
    )

    write_audit_log(
        event_type="payment_action_required",
        actor_type="stripe",
        actor_id=None,
        target_type="school",
        target_id=row["school_id"],
    )

    log.info(
        "payment_action_required_email_queued school_id=%s contact_email=%s",
        school_id,
        contact_email,
    )
