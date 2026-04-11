"""
backend/src/teacher/subscription_service.py

Business logic for independent teacher Stripe subscriptions (#57, #105).

An independent teacher is one with school_id IS NULL in the teachers table.
They pay a flat monthly recurring fee (Solo $29 · Growth $59 · Pro $99) and
access the platform without a school affiliation.

Public API
──────────
  create_teacher_checkout_session(teacher_id, plan, success_url, cancel_url) → str
  get_teacher_subscription_status(conn, teacher_id) → dict
  cancel_teacher_stripe_subscription(stripe_sub_id) → None
  cancel_teacher_subscription_db(conn, teacher_id) → None

  upgrade_teacher_plan(conn, teacher_id, new_plan, stripe_subscription_id) → None
    Swaps the Stripe subscription price mid-cycle and updates the DB row.
    Clears over_quota so the Beat task can re-evaluate within 24 h.

  flag_teacher_over_quota(conn, teacher_id) → None
    Set over_quota=TRUE and stamp over_quota_since (idempotent on first flag).
  clear_teacher_over_quota(conn, teacher_id) → None
    Clear over_quota and over_quota_since.

  check_student_seat_limit(conn, teacher_id) → dict
    Returns {allowed, seats_used, max_students, plan}.

  handle_teacher_subscription_activated(conn, teacher_id, plan,
      stripe_customer_id, stripe_subscription_id, current_period_end) → None
  handle_teacher_subscription_updated(conn, stripe_subscription_id,
      status, current_period_end) → None
  handle_teacher_subscription_deleted(conn, stripe_subscription_id) → None
  handle_teacher_payment_failed(conn, stripe_subscription_id) → None

  find_teacher_by_stripe_subscription(conn, stripe_subscription_id) → str | None
    Returns teacher_id or None.
"""

from __future__ import annotations

import asyncio
from functools import partial

import asyncpg

from src.pricing import TEACHER_PLANS, get_teacher_plan
from src.utils.logger import get_logger

log = get_logger("teacher.subscription")


# ── Stripe helpers (mirrors school/subscription_service.py pattern) ────────────


def _get_stripe():
    try:
        import stripe  # type: ignore
        return stripe
    except ImportError:
        raise RuntimeError("stripe package not installed — run: pip install stripe")


def _stripe_key() -> str:
    from config import settings
    key = getattr(settings, "STRIPE_SECRET_KEY", None)
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return key


async def _run_stripe(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


def _teacher_price_id(plan_id: str) -> str:
    """Return Stripe price ID for the given teacher plan. Raises RuntimeError if unset."""
    from config import settings
    mapping = {
        "solo":   getattr(settings, "STRIPE_TEACHER_PRICE_SOLO_ID", None),
        "growth": getattr(settings, "STRIPE_TEACHER_PRICE_GROWTH_ID", None),
        "pro":    getattr(settings, "STRIPE_TEACHER_PRICE_PRO_ID", None),
    }
    price_id = mapping.get(plan_id)
    if not price_id:
        raise RuntimeError(
            f"STRIPE_TEACHER_PRICE_{plan_id.upper()}_ID is not configured"
        )
    return price_id


# ── Stripe Checkout session ────────────────────────────────────────────────────


async def create_teacher_checkout_session(
    teacher_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session (mode=subscription) for an independent teacher.

    On checkout.session.completed the webhook calls handle_teacher_subscription_activated().
    Returns the Stripe-hosted checkout URL.
    """
    get_teacher_plan(plan)   # validates plan_id; raises KeyError on unknown

    stripe = _get_stripe()
    stripe.api_key = _stripe_key()
    price_id = _teacher_price_id(plan)

    session = await _run_stripe(
        stripe.checkout.Session.create,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "teacher_id": teacher_id,
            "plan": plan,
            "product_type": "teacher_subscription",
        },
    )
    log.info("teacher_checkout_session_created teacher_id=%s plan=%s", teacher_id, plan)
    return session.url


# ── Subscription status ────────────────────────────────────────────────────────


async def get_teacher_subscription_status(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> dict:
    """
    Return subscription status for an independent teacher.

    Returns plan='none', status=None when no subscription row exists.
    Includes seat usage so the frontend can show the student cap.
    """
    row = await conn.fetchrow(
        """
        SELECT plan, status, max_students,
               stripe_subscription_id, current_period_end, grace_period_end,
               over_quota, over_quota_since
        FROM teacher_subscriptions
        WHERE teacher_id = $1::uuid
        """,
        teacher_id,
    )
    seats = await check_student_seat_limit(conn, teacher_id)

    if row is None:
        return {
            "plan": "none",
            "status": None,
            "max_students": 0,
            "seats_used_students": seats["seats_used"],
            "current_period_end": None,
            "over_quota": False,
            "over_quota_since": None,
        }

    if row["status"] == "past_due" and row["grace_period_end"]:
        valid_until = row["grace_period_end"].isoformat()
    elif row["current_period_end"]:
        valid_until = row["current_period_end"].isoformat()
    else:
        valid_until = None

    oqs = row["over_quota_since"]
    return {
        "plan": row["plan"],
        "status": row["status"],
        "max_students": row["max_students"],
        "seats_used_students": seats["seats_used"],
        "current_period_end": valid_until,
        "over_quota": bool(row["over_quota"]),
        "over_quota_since": oqs.isoformat() if oqs else None,
    }


# ── Seat limit check ──────────────────────────────────────────────────────────


async def check_student_seat_limit(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> dict:
    """
    Return {allowed, seats_used, max_students, plan} for an independent teacher.

    'allowed' is True only when seats_used < max_students and the subscription
    is active or trialing.  Returns allowed=False when no subscription exists.
    """
    sub_row = await conn.fetchrow(
        """
        SELECT plan, status, max_students
        FROM teacher_subscriptions
        WHERE teacher_id = $1::uuid
        """,
        teacher_id,
    )

    # Count students currently enrolled by this independent teacher.
    # Independent-teacher students have no school_id and are linked via
    # student_teacher_assignments.
    seats_used = await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM student_teacher_assignments sta
        JOIN students s ON s.student_id = sta.student_id
        WHERE sta.teacher_id = $1::uuid
          AND s.school_id IS NULL
          AND s.account_status = 'active'
        """,
        teacher_id,
    ) or 0

    if sub_row is None:
        return {
            "allowed": False,
            "seats_used": int(seats_used),
            "max_students": 0,
            "plan": "none",
        }

    active = sub_row["status"] in ("active", "trialing")
    max_s = sub_row["max_students"]

    return {
        "allowed": active and int(seats_used) < max_s,
        "seats_used": int(seats_used),
        "max_students": max_s,
        "plan": sub_row["plan"],
    }


# ── Cancellation ──────────────────────────────────────────────────────────────


async def cancel_teacher_stripe_subscription(stripe_subscription_id: str) -> None:
    """Set cancel_at_period_end=True on the Stripe subscription."""
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()
    await _run_stripe(
        stripe.Subscription.modify,
        stripe_subscription_id,
        cancel_at_period_end=True,
    )
    log.info("teacher_stripe_sub_cancel_at_period_end sub_id=%s", stripe_subscription_id)


async def cancel_teacher_subscription_db(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> None:
    """Mark the DB subscription row as cancelled and clear teacher_plan."""
    await conn.execute(
        """
        UPDATE teacher_subscriptions
        SET status = 'cancelled', updated_at = NOW()
        WHERE teacher_id = $1::uuid
        """,
        teacher_id,
    )
    await conn.execute(
        "UPDATE teachers SET teacher_plan = NULL WHERE teacher_id = $1::uuid",
        teacher_id,
    )
    log.info("teacher_subscription_cancelled_db teacher_id=%s", teacher_id)


# ── Webhook event handlers ────────────────────────────────────────────────────


async def handle_teacher_subscription_activated(
    conn: asyncpg.Connection,
    teacher_id: str,
    plan: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end,
) -> None:
    """
    Called on checkout.session.completed for product_type='teacher_subscription'.

    Upserts teacher_subscriptions and stamps teacher.teacher_plan.
    Idempotent — safe to call on replay.
    """
    teacher_plan = get_teacher_plan(plan)
    max_students = teacher_plan.max_students

    await conn.execute(
        """
        INSERT INTO teacher_subscriptions
            (teacher_id, plan, status, max_students,
             stripe_customer_id, stripe_subscription_id,
             current_period_end)
        VALUES ($1::uuid, $2, 'active', $3, $4, $5, $6)
        ON CONFLICT (teacher_id) DO UPDATE SET
            plan                  = EXCLUDED.plan,
            status                = 'active',
            max_students          = EXCLUDED.max_students,
            stripe_customer_id    = EXCLUDED.stripe_customer_id,
            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
            current_period_end    = EXCLUDED.current_period_end,
            updated_at            = NOW()
        """,
        teacher_id,
        plan,
        max_students,
        stripe_customer_id,
        stripe_subscription_id,
        current_period_end,
    )
    await conn.execute(
        "UPDATE teachers SET teacher_plan = $1 WHERE teacher_id = $2::uuid",
        plan, teacher_id,
    )
    log.info(
        "teacher_subscription_activated teacher_id=%s plan=%s sub_id=%s",
        teacher_id, plan, stripe_subscription_id,
    )


async def handle_teacher_subscription_updated(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
    status: str,
    current_period_end,
) -> None:
    """
    Called on customer.subscription.updated.

    Updates status and current_period_end.  If status transitions to 'active'
    from 'past_due' the grace_period_end is cleared.
    """
    clear_grace = "grace_period_end = NULL," if status == "active" else ""
    await conn.execute(
        f"""
        UPDATE teacher_subscriptions
        SET status = $1,
            {clear_grace}
            current_period_end = $2,
            updated_at = NOW()
        WHERE stripe_subscription_id = $3
        """,
        status, current_period_end, stripe_subscription_id,
    )
    log.info(
        "teacher_subscription_updated sub_id=%s status=%s",
        stripe_subscription_id, status,
    )


async def handle_teacher_subscription_deleted(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> None:
    """
    Called on customer.subscription.deleted.

    Sets status='cancelled' and clears teacher.teacher_plan.
    """
    teacher_id = await conn.fetchval(
        "SELECT teacher_id::text FROM teacher_subscriptions WHERE stripe_subscription_id = $1",
        stripe_subscription_id,
    )
    if teacher_id:
        await conn.execute(
            """
            UPDATE teacher_subscriptions
            SET status = 'cancelled', updated_at = NOW()
            WHERE stripe_subscription_id = $1
            """,
            stripe_subscription_id,
        )
        await conn.execute(
            "UPDATE teachers SET teacher_plan = NULL WHERE teacher_id = $1::uuid",
            teacher_id,
        )
        log.info(
            "teacher_subscription_deleted sub_id=%s teacher_id=%s",
            stripe_subscription_id, teacher_id,
        )


async def handle_teacher_payment_failed(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> None:
    """
    Called on invoice.payment_failed for a teacher subscription.

    Sets status='past_due' and stamps grace_period_end = NOW() + 7 days.
    After grace_period_end expires the teacher loses access.
    """
    await conn.execute(
        """
        UPDATE teacher_subscriptions
        SET status = 'past_due',
            grace_period_end = NOW() + INTERVAL '7 days',
            updated_at = NOW()
        WHERE stripe_subscription_id = $1
        """,
        stripe_subscription_id,
    )
    log.info("teacher_payment_failed sub_id=%s", stripe_subscription_id)


async def find_teacher_by_stripe_subscription(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> str | None:
    """Return teacher_id (str) for a Stripe subscription ID, or None if not found."""
    row = await conn.fetchval(
        "SELECT teacher_id::text FROM teacher_subscriptions WHERE stripe_subscription_id = $1",
        stripe_subscription_id,
    )
    return row


# ── Plan upgrade / downgrade (#105) ──────────────────────────────────────────


async def upgrade_teacher_plan(
    conn: asyncpg.Connection,
    teacher_id: str,
    new_plan: str,
    stripe_subscription_id: str,
) -> None:
    """
    Upgrade or downgrade an independent teacher's flat-fee plan mid-cycle.

    1. Fetches the current Stripe subscription to locate the line-item ID.
    2. Calls Stripe Subscription.modify() to swap the price, creating pro-rated
       charges/credits automatically (proration_behavior='create_prorations').
    3. Updates the DB row: new plan, max_students; clears over_quota so the
       daily Beat task can re-evaluate within 24 h on the new limit.
    4. Stamps teacher.teacher_plan with the new plan ID.

    Raises RuntimeError if Stripe or config is unavailable.
    Idempotent — replaying with the same new_plan is safe (Stripe deduplicates).
    """
    teacher_plan_obj = get_teacher_plan(new_plan)
    new_max = teacher_plan_obj.max_students
    new_price_id = _teacher_price_id(new_plan)

    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    # Retrieve the current subscription to get the line-item id to replace.
    sub = await _run_stripe(stripe.Subscription.retrieve, stripe_subscription_id)
    item_id = sub["items"]["data"][0]["id"]

    await _run_stripe(
        stripe.Subscription.modify,
        stripe_subscription_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
    )

    # Always clear over_quota on a plan change — the Beat task will re-flag
    # within 24 h if the new limit still doesn't cover the enrolled students.
    await conn.execute(
        """
        UPDATE teacher_subscriptions
        SET plan             = $1,
            max_students     = $2,
            over_quota       = FALSE,
            over_quota_since = NULL,
            updated_at       = NOW()
        WHERE teacher_id = $3::uuid
        """,
        new_plan,
        new_max,
        teacher_id,
    )
    await conn.execute(
        "UPDATE teachers SET teacher_plan = $1 WHERE teacher_id = $2::uuid",
        new_plan, teacher_id,
    )
    log.info(
        "teacher_plan_upgraded teacher_id=%s new_plan=%s max_students=%d",
        teacher_id, new_plan, new_max,
    )


# ── Over-quota flag helpers ───────────────────────────────────────────────────


async def flag_teacher_over_quota(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> None:
    """
    Mark an independent teacher as over-quota.

    Sets over_quota=TRUE and stamps over_quota_since with the current time on
    the first call.  Subsequent calls for an already-flagged teacher are no-ops
    (COALESCE preserves the original timestamp so the grace-period clock is not
    reset on repeat runs of the Beat task).
    """
    await conn.execute(
        """
        UPDATE teacher_subscriptions
        SET over_quota       = TRUE,
            over_quota_since = COALESCE(over_quota_since, NOW()),
            updated_at       = NOW()
        WHERE teacher_id = $1::uuid
          AND over_quota  = FALSE
        """,
        teacher_id,
    )
    log.info("teacher_over_quota_flagged teacher_id=%s", teacher_id)


async def clear_teacher_over_quota(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> None:
    """
    Clear the over-quota flag when seats_used has dropped back within the limit.

    No-op if the teacher is not currently flagged.
    """
    await conn.execute(
        """
        UPDATE teacher_subscriptions
        SET over_quota       = FALSE,
            over_quota_since = NULL,
            updated_at       = NOW()
        WHERE teacher_id = $1::uuid
          AND over_quota  = TRUE
        """,
        teacher_id,
    )
    log.info("teacher_over_quota_cleared teacher_id=%s", teacher_id)
