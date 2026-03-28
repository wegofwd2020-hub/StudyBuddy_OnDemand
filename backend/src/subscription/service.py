"""
backend/src/subscription/service.py

Subscription business logic.

Stripe integration:
  create_checkout_session() — creates Stripe Checkout Session; returns checkout_url.
  cancel_stripe_subscription() — cancels at period end via Stripe API.

Database lifecycle:
  get_subscription_status()     — reads subscriptions + student_entitlements.
  activate_subscription()       — called from checkout.session.completed webhook.
  update_subscription_status()  — called from customer.subscription.updated webhook.
  cancel_subscription_db()      — called from customer.subscription.deleted webhook.
  handle_payment_failed()       — called from invoice.payment_failed; sets 3-day grace.
  log_stripe_event()            — upserts stripe_events row (dedup key).
  already_processed()           — check if stripe_event_id already handled.

Entitlement cache:
  expire_entitlement_cache()    — deletes ent:{student_id} from Redis; called on any
                                   subscription state change so next request re-fetches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg

from src.utils.logger import get_logger

log = get_logger("subscription")

_GRACE_PERIOD_DAYS = 3


# ── Stripe helpers ─────────────────────────────────────────────────────────────

def _get_stripe():
    """Import stripe lazily; raise RuntimeError if not installed."""
    try:
        import stripe  # type: ignore
        return stripe
    except ImportError:
        raise RuntimeError("stripe package not installed — run: pip install stripe")


def _stripe_key():
    from config import settings
    key = getattr(settings, "STRIPE_SECRET_KEY", None)
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return key


# ── Checkout ──────────────────────────────────────────────────────────────────

async def create_checkout_session(
    student_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session and return the checkout URL.

    Embeds student_id and plan in metadata so the webhook can activate
    the subscription without an additional DB lookup.
    """
    from config import settings
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    price_id = (
        getattr(settings, "STRIPE_PRICE_MONTHLY_ID", None)
        if plan == "monthly"
        else getattr(settings, "STRIPE_PRICE_ANNUAL_ID", None)
    )
    if not price_id:
        raise RuntimeError(f"STRIPE_PRICE_{plan.upper()}_ID is not configured")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"student_id": student_id, "plan": plan},
        subscription_data={"metadata": {"student_id": student_id, "plan": plan}},
    )
    return session.url


# ── Stripe cancellation ───────────────────────────────────────────────────────

async def cancel_stripe_subscription(stripe_subscription_id: str) -> None:
    """Cancel a Stripe subscription at period end."""
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()
    stripe.Subscription.modify(
        stripe_subscription_id,
        cancel_at_period_end=True,
    )
    log.info("stripe_subscription_cancel_at_period_end sub_id=%s", stripe_subscription_id)


# ── Entitlement cache ─────────────────────────────────────────────────────────

async def expire_entitlement_cache(redis, student_id: str) -> None:
    """Delete the Redis entitlement cache entry for a student."""
    await redis.delete(f"ent:{student_id}")
    log.debug("entitlement_cache_expired student_id=%s", student_id)


# ── Stripe event dedup ────────────────────────────────────────────────────────

async def already_processed(conn: asyncpg.Connection, stripe_event_id: str) -> bool:
    """Return True if this stripe_event_id has already been handled."""
    row = await conn.fetchrow(
        "SELECT 1 FROM stripe_events WHERE stripe_event_id = $1 AND outcome = 'ok'",
        stripe_event_id,
    )
    return row is not None


async def log_stripe_event(
    conn: asyncpg.Connection,
    stripe_event_id: str,
    event_type: str,
    outcome: str,
    error_detail: str | None = None,
) -> None:
    """Insert a stripe_events row. Uses INSERT ... ON CONFLICT DO NOTHING for idempotency."""
    await conn.execute(
        """
        INSERT INTO stripe_events (stripe_event_id, event_type, outcome, error_detail)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (stripe_event_id) DO NOTHING
        """,
        stripe_event_id,
        event_type,
        outcome,
        error_detail,
    )


# ── Subscription status ───────────────────────────────────────────────────────

async def get_subscription_status(conn: asyncpg.Connection, student_id: str) -> dict:
    """
    Return subscription status for a student.

    Merges data from subscriptions table + student_entitlements.
    """
    sub_row = await conn.fetchrow(
        """
        SELECT plan, status, stripe_subscription_id,
               current_period_end, grace_period_end
        FROM subscriptions
        WHERE student_id = $1
          AND status IN ('active', 'past_due')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        student_id,
    )

    ent_row = await conn.fetchrow(
        "SELECT lessons_accessed FROM student_entitlements WHERE student_id = $1",
        student_id,
    )
    lessons_accessed = ent_row["lessons_accessed"] if ent_row else 0

    if sub_row is None:
        return {
            "plan": "free",
            "status": None,
            "valid_until": None,
            "lessons_accessed": lessons_accessed,
            "stripe_subscription_id": None,
        }

    # For past_due, valid_until is grace_period_end
    if sub_row["status"] == "past_due" and sub_row["grace_period_end"]:
        valid_until = sub_row["grace_period_end"].isoformat()
    elif sub_row["current_period_end"]:
        valid_until = sub_row["current_period_end"].isoformat()
    else:
        valid_until = None

    return {
        "plan": sub_row["plan"],
        "status": sub_row["status"],
        "valid_until": valid_until,
        "lessons_accessed": lessons_accessed,
        "stripe_subscription_id": sub_row["stripe_subscription_id"],
    }


# ── Webhook event handlers ────────────────────────────────────────────────────

async def activate_subscription(
    conn: asyncpg.Connection,
    redis,
    student_id: str,
    plan: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end: datetime | None,
) -> None:
    """
    Called on checkout.session.completed.

    1. Upsert subscriptions row (active).
    2. Update student_entitlements.plan + valid_until.
    3. Expire entitlement cache.
    """
    await conn.execute(
        """
        INSERT INTO subscriptions
            (student_id, plan, status, stripe_customer_id, stripe_subscription_id,
             current_period_end, updated_at)
        VALUES ($1, $2, 'active', $3, $4, $5, NOW())
        ON CONFLICT (stripe_subscription_id)
            DO UPDATE SET
                status             = 'active',
                plan               = EXCLUDED.plan,
                current_period_end = EXCLUDED.current_period_end,
                grace_period_end   = NULL,
                updated_at         = NOW()
        """,
        student_id,
        plan,
        stripe_customer_id,
        stripe_subscription_id,
        current_period_end,
    )

    await conn.execute(
        """
        INSERT INTO student_entitlements (student_id, plan, valid_until, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (student_id)
            DO UPDATE SET plan = EXCLUDED.plan, valid_until = EXCLUDED.valid_until, updated_at = NOW()
        """,
        student_id,
        plan,
        current_period_end,
    )

    await expire_entitlement_cache(redis, student_id)
    log.info("subscription_activated student_id=%s plan=%s", student_id, plan)


async def update_subscription_status(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
    status: str,
    current_period_end: datetime | None,
) -> None:
    """
    Called on customer.subscription.updated.

    Updates the subscriptions row and refreshes student_entitlements.valid_until.
    """
    row = await conn.fetchrow(
        """
        UPDATE subscriptions
        SET status = $2, current_period_end = $3, updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING student_id::text, plan
        """,
        stripe_subscription_id,
        status,
        current_period_end,
    )
    if not row:
        return

    student_id = row["student_id"]
    await conn.execute(
        """
        UPDATE student_entitlements
        SET valid_until = $2, updated_at = NOW()
        WHERE student_id = $1
        """,
        student_id,
        current_period_end,
    )
    await expire_entitlement_cache(redis, student_id)
    log.info("subscription_updated stripe_sub=%s status=%s", stripe_subscription_id, status)


async def cancel_subscription_db(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    """
    Called on customer.subscription.deleted.

    Marks subscription cancelled and reverts student to free tier.
    """
    row = await conn.fetchrow(
        """
        UPDATE subscriptions
        SET status = 'cancelled', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING student_id::text
        """,
        stripe_subscription_id,
    )
    if not row:
        return

    student_id = row["student_id"]
    # Revert entitlement to free plan
    await conn.execute(
        """
        UPDATE student_entitlements
        SET plan = 'free', valid_until = NULL, updated_at = NOW()
        WHERE student_id = $1
        """,
        student_id,
    )
    await expire_entitlement_cache(redis, student_id)
    log.info("subscription_cancelled stripe_sub=%s student_id=%s", stripe_subscription_id, student_id)


async def handle_payment_failed(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    """
    Called on invoice.payment_failed.

    Sets status=past_due and grace_period_end = NOW() + 3 days.
    Student retains access until grace_period_end.
    """
    grace_end = datetime.now(UTC) + timedelta(days=_GRACE_PERIOD_DAYS)

    row = await conn.fetchrow(
        """
        UPDATE subscriptions
        SET status = 'past_due', grace_period_end = $2, updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING student_id::text
        """,
        stripe_subscription_id,
        grace_end,
    )
    if not row:
        return

    student_id = row["student_id"]
    # Extend valid_until to grace_period_end in entitlements
    await conn.execute(
        """
        UPDATE student_entitlements
        SET valid_until = $2, updated_at = NOW()
        WHERE student_id = $1
        """,
        student_id,
        grace_end,
    )
    await expire_entitlement_cache(redis, student_id)
    log.info(
        "payment_failed_grace_period_set stripe_sub=%s student_id=%s grace_end=%s",
        stripe_subscription_id, student_id, grace_end.isoformat()
    )


async def cancel_active_subscription_for_student(
    conn: asyncpg.Connection,
    student_id: str,
) -> str | None:
    """
    Return the active stripe_subscription_id for a student (or None).
    Used by DELETE /auth/account to cancel Stripe sub before GDPR deletion.
    """
    row = await conn.fetchrow(
        """
        SELECT stripe_subscription_id FROM subscriptions
        WHERE student_id = $1 AND status = 'active'
        LIMIT 1
        """,
        student_id,
    )
    return row["stripe_subscription_id"] if row else None
