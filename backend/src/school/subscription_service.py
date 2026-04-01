"""
backend/src/school/subscription_service.py

School subscription business logic.

School billing model: one subscription per school covers all enrolled
students and teachers. Individual student subscriptions are unchanged.

Plan seat limits are resolved in priority order:
  1. school_plan_overrides (per-school manual override by super_admin)
  2. settings.SCHOOL_SEATS_*  (env-configurable plan defaults)

Stripe metadata convention for school sessions:
  {"school_id": "...", "plan": "starter|professional|enterprise"}

Entitlement derivation for school-enrolled students:
  - School subscription active  → student plan = school plan
  - School subscription absent / cancelled → fall back to student_entitlements
  The school path is cached at ent:school:{school_id} TTL=300s.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

from src.utils.logger import get_logger

log = get_logger("school.subscription")

_GRACE_PERIOD_DAYS = 3
_ENT_SCHOOL_KEY = "ent:school:{school_id}"
_ENT_SCHOOL_TTL = 300  # 5 minutes


# ── Plan defaults ─────────────────────────────────────────────────────────────


def _plan_seats(plan: str) -> dict[str, int]:
    """Return {max_students, max_teachers} for a plan using settings env vars."""
    from config import settings

    mapping = {
        "starter": {
            "max_students": settings.SCHOOL_SEATS_STARTER_STUDENTS,
            "max_teachers": settings.SCHOOL_SEATS_STARTER_TEACHERS,
        },
        "professional": {
            "max_students": settings.SCHOOL_SEATS_PROFESSIONAL_STUDENTS,
            "max_teachers": settings.SCHOOL_SEATS_PROFESSIONAL_TEACHERS,
        },
        "enterprise": {
            "max_students": settings.SCHOOL_SEATS_ENTERPRISE_STUDENTS,
            "max_teachers": settings.SCHOOL_SEATS_ENTERPRISE_TEACHERS,
        },
    }
    return mapping.get(plan, mapping["starter"])


# ── Seat usage ────────────────────────────────────────────────────────────────


async def get_seat_usage(conn: asyncpg.Connection, school_id: str) -> dict[str, int]:
    """Return active student and teacher counts for a school."""
    student_count = await conn.fetchval(
        "SELECT COUNT(*) FROM school_enrolments WHERE school_id = $1 AND status = 'active'",
        uuid.UUID(school_id),
    )
    teacher_count = await conn.fetchval(
        "SELECT COUNT(*) FROM teachers WHERE school_id = $1 AND account_status = 'active'",
        uuid.UUID(school_id),
    )
    return {
        "seats_used_students": int(student_count or 0),
        "seats_used_teachers": int(teacher_count or 0),
    }


# ── Subscription status ───────────────────────────────────────────────────────


async def get_school_subscription_status(
    conn: asyncpg.Connection,
    school_id: str,
) -> dict:
    """
    Return subscription status + seat usage for a school.

    Returns plan='none', status=None when no subscription exists.
    """
    row = await conn.fetchrow(
        """
        SELECT plan, status, max_students, max_teachers,
               current_period_end, grace_period_end,
               stripe_subscription_id
        FROM school_subscriptions
        WHERE school_id = $1
        """,
        uuid.UUID(school_id),
    )

    usage = await get_seat_usage(conn, school_id)

    if row is None:
        return {
            "plan": "none",
            "status": None,
            "max_students": 0,
            "max_teachers": 0,
            "current_period_end": None,
            **usage,
        }

    if row["status"] == "past_due" and row["grace_period_end"]:
        valid_until = row["grace_period_end"].isoformat()
    elif row["current_period_end"]:
        valid_until = row["current_period_end"].isoformat()
    else:
        valid_until = None

    return {
        "plan": row["plan"],
        "status": row["status"],
        "max_students": row["max_students"],
        "max_teachers": row["max_teachers"],
        "current_period_end": valid_until,
        **usage,
    }


# ── Stripe ────────────────────────────────────────────────────────────────────


def _get_stripe():
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


async def create_school_checkout_session(
    school_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session for a school subscription.

    Embeds school_id and plan in session metadata so the webhook can
    activate the subscription without a DB lookup.
    Returns the Stripe-hosted checkout URL.
    """
    from config import settings

    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    price_map = {
        "starter": getattr(settings, "STRIPE_SCHOOL_PRICE_STARTER_ID", None),
        "professional": getattr(settings, "STRIPE_SCHOOL_PRICE_PROFESSIONAL_ID", None),
        "enterprise": getattr(settings, "STRIPE_SCHOOL_PRICE_ENTERPRISE_ID", None),
    }
    price_id = price_map.get(plan)
    if not price_id:
        raise RuntimeError(f"STRIPE_SCHOOL_PRICE_{plan.upper()}_ID is not configured")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"school_id": school_id, "plan": plan},
        subscription_data={"metadata": {"school_id": school_id, "plan": plan}},
    )
    return session.url


async def cancel_school_stripe_subscription(stripe_subscription_id: str) -> None:
    """Cancel a school's Stripe subscription at period end."""
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()
    stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
    log.info("school_stripe_subscription_cancel_at_period_end sub_id=%s", stripe_subscription_id)


# ── Entitlement cache ─────────────────────────────────────────────────────────


async def expire_school_entitlement_cache(redis, school_id: str) -> None:
    """
    Delete ent:school:{school_id} from Redis and dispatch a Celery task
    to bulk-delete all enrolled students' ent:{student_id} keys.
    """
    await redis.delete(_ENT_SCHOOL_KEY.format(school_id=school_id))
    log.debug("school_entitlement_cache_expired school_id=%s", school_id)

    try:
        from src.auth.tasks import invalidate_school_entitlement_cache_task

        invalidate_school_entitlement_cache_task.delay(school_id)
    except Exception as exc:
        log.warning("could_not_dispatch_cache_invalidation school_id=%s error=%s", school_id, exc)


async def get_school_entitlement_for_student(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
) -> dict | None:
    """
    Return {plan, lessons_accessed, valid_until} derived from the school
    subscription for an enrolled student, or None if no active school subscription.

    Uses ent:school:{school_id} L2 cache (TTL=300s).
    """
    # Find the student's school_id
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT school_id::text FROM students WHERE student_id = $1 AND school_id IS NOT NULL",
            student_id,
        )
    if not row:
        return None

    school_id = row["school_id"]
    cache_key = _ENT_SCHOOL_KEY.format(school_id=school_id)

    cached = await redis.get(cache_key)
    if cached:
        try:
            school_ent = json.loads(cached)
            if not school_ent.get("active"):
                return None
            return {
                "plan": school_ent["plan"],
                "lessons_accessed": 0,
                "valid_until": school_ent.get("valid_until"),
            }
        except Exception:
            pass

    # Cache miss — query school_subscriptions
    async with pool.acquire() as conn:
        sub_row = await conn.fetchrow(
            """
            SELECT plan, status, current_period_end, grace_period_end
            FROM school_subscriptions
            WHERE school_id = $1
            """,
            uuid.UUID(school_id),
        )

    active = (
        sub_row is not None
        and sub_row["status"] in ("active", "trialing", "past_due")
    )

    if active and sub_row["status"] == "past_due" and sub_row["grace_period_end"]:
        valid_until = sub_row["grace_period_end"].isoformat()
    elif active and sub_row["current_period_end"]:
        valid_until = sub_row["current_period_end"].isoformat()
    else:
        valid_until = None

    school_ent = {
        "active": active,
        "plan": sub_row["plan"] if active else None,
        "valid_until": valid_until,
    }
    await redis.set(cache_key, json.dumps(school_ent), ex=_ENT_SCHOOL_TTL)

    if not active:
        return None
    return {
        "plan": school_ent["plan"],
        "lessons_accessed": 0,
        "valid_until": valid_until,
    }


# ── Webhook event handlers ────────────────────────────────────────────────────


async def activate_school_subscription(
    conn: asyncpg.Connection,
    redis,
    school_id: str,
    plan: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end: datetime | None,
) -> None:
    """
    Called on checkout.session.completed for a school session.

    Upserts school_subscriptions row (active).
    Bulk-updates student_entitlements for all enrolled students.
    Invalidates school entitlement cache.
    """
    seats = _plan_seats(plan)

    await conn.execute(
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
             max_students, max_teachers, current_period_end, updated_at)
        VALUES ($1, $2, 'active', $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (school_id)
            DO UPDATE SET
                plan                   = EXCLUDED.plan,
                status                 = 'active',
                stripe_customer_id     = EXCLUDED.stripe_customer_id,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                max_students           = EXCLUDED.max_students,
                max_teachers           = EXCLUDED.max_teachers,
                current_period_end     = EXCLUDED.current_period_end,
                grace_period_end       = NULL,
                updated_at             = NOW()
        """,
        uuid.UUID(school_id),
        plan,
        stripe_customer_id,
        stripe_subscription_id,
        seats["max_students"],
        seats["max_teachers"],
        current_period_end,
    )

    # Bulk-upsert student_entitlements for all enrolled students
    await _bulk_update_enrolled_student_entitlements(conn, school_id, plan, current_period_end)

    await expire_school_entitlement_cache(redis, school_id)
    log.info("school_subscription_activated school_id=%s plan=%s", school_id, plan)


async def update_school_subscription_status(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
    status: str,
    current_period_end: datetime | None,
) -> None:
    """Called on customer.subscription.updated for a school subscription."""
    row = await conn.fetchrow(
        """
        UPDATE school_subscriptions
        SET status = $2, current_period_end = $3, updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING school_id::text, plan
        """,
        stripe_subscription_id,
        status,
        current_period_end,
    )
    if not row:
        return

    school_id = row["school_id"]
    await _bulk_update_enrolled_student_entitlements(conn, school_id, row["plan"], current_period_end)
    await expire_school_entitlement_cache(redis, school_id)
    log.info(
        "school_subscription_updated stripe_sub=%s status=%s", stripe_subscription_id, status
    )


async def cancel_school_subscription_db(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    """Called on customer.subscription.deleted for a school subscription."""
    row = await conn.fetchrow(
        """
        UPDATE school_subscriptions
        SET status = 'cancelled', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING school_id::text
        """,
        stripe_subscription_id,
    )
    if not row:
        return

    school_id = row["school_id"]
    # Revert enrolled students to free tier
    await _bulk_update_enrolled_student_entitlements(conn, school_id, "free", None)
    await expire_school_entitlement_cache(redis, school_id)
    log.info(
        "school_subscription_cancelled stripe_sub=%s school_id=%s", stripe_subscription_id, school_id
    )


async def handle_school_payment_failed(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    """Called on invoice.payment_failed for a school subscription."""
    grace_end = datetime.now(UTC) + timedelta(days=_GRACE_PERIOD_DAYS)

    row = await conn.fetchrow(
        """
        UPDATE school_subscriptions
        SET status = 'past_due', grace_period_end = $2, updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING school_id::text, plan
        """,
        stripe_subscription_id,
        grace_end,
    )
    if not row:
        return

    school_id = row["school_id"]
    # Extend student entitlements to grace_period_end
    await _bulk_update_enrolled_student_entitlements(conn, school_id, row["plan"], grace_end)
    await expire_school_entitlement_cache(redis, school_id)
    log.info(
        "school_payment_failed_grace_set stripe_sub=%s school_id=%s grace_end=%s",
        stripe_subscription_id,
        school_id,
        grace_end.isoformat(),
    )


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _bulk_update_enrolled_student_entitlements(
    conn: asyncpg.Connection,
    school_id: str,
    plan: str,
    valid_until: datetime | None,
) -> None:
    """
    Upsert student_entitlements for all active enrolments in a school.

    Called on every school subscription state change so that the existing
    individual-student entitlement path returns the correct plan without
    needing an additional school_subscriptions lookup.
    """
    # Fetch all enrolled student_ids that have registered accounts
    rows = await conn.fetch(
        """
        SELECT se.student_id::text
        FROM school_enrolments se
        WHERE se.school_id = $1
          AND se.status = 'active'
          AND se.student_id IS NOT NULL
        """,
        uuid.UUID(school_id),
    )
    if not rows:
        return

    for row in rows:
        student_id = row["student_id"]
        await conn.execute(
            """
            INSERT INTO student_entitlements (student_id, plan, valid_until, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (student_id)
                DO UPDATE SET plan = EXCLUDED.plan, valid_until = EXCLUDED.valid_until, updated_at = NOW()
            """,
            student_id,
            plan,
            valid_until,
        )
    log.debug(
        "bulk_entitlement_update school_id=%s plan=%s count=%d", school_id, plan, len(rows)
    )
