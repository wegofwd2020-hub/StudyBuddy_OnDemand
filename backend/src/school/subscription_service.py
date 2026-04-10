"""
backend/src/school/subscription_service.py

School subscription business logic.

School billing model: one subscription per school covers all enrolled
students and teachers.

Plan seat limits and build allowances are resolved from src/pricing.py
(single source of truth for all platform pricing).
Per-school manual overrides by super_admin can be applied separately.

Stripe metadata convention for school sessions:
  {"school_id": "...", "plan": "starter|professional|enterprise"}

Entitlement derivation for school-enrolled students:
  Handled by src/content/service.py::get_entitlement() which calls
  _get_school_sub() using school_id from the JWT — no students-table lookup.
  The result is cached at school:{school_id}:ent (TTL=300s).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

from src.core.cache_keys import school_ent_key, school_scan_pattern
from src.utils.logger import get_logger

log = get_logger("school.subscription")

_GRACE_PERIOD_DAYS = 3


# ── Plan defaults ─────────────────────────────────────────────────────────────


def _plan_seats(plan: str) -> dict[str, int]:
    """Return {max_students, max_teachers} for a plan from src/pricing.py."""
    from src.pricing import plan_seats
    return plan_seats(plan)


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
    Delete school:{school_id}:ent from Redis and dispatch a Celery task
    to bulk-delete all remaining school:{school_id}:* keys (ent + cur per student).
    """
    await redis.delete(school_ent_key(school_id))
    log.debug("school_entitlement_cache_expired school_id=%s", school_id)

    try:
        from src.auth.tasks import invalidate_school_entitlement_cache_task

        invalidate_school_entitlement_cache_task.delay(school_id)
    except Exception as exc:
        log.warning("could_not_dispatch_cache_invalidation school_id=%s error=%s", school_id, exc)


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


# ── Retention billing — Stripe Checkout sessions ──────────────────────────────

_STORAGE_PACKAGES: dict[int, str] = {5: "5GB", 10: "10GB", 25: "25GB"}


def _storage_price_id(gb: int) -> str:
    """Return the Stripe price ID for a storage add-on package."""
    from config import settings

    price_map = {
        5: getattr(settings, "STRIPE_SCHOOL_PRICE_STORAGE_5GB_ID", None),
        10: getattr(settings, "STRIPE_SCHOOL_PRICE_STORAGE_10GB_ID", None),
        25: getattr(settings, "STRIPE_SCHOOL_PRICE_STORAGE_25GB_ID", None),
    }
    price_id = price_map.get(gb)
    if not price_id:
        raise RuntimeError(f"STRIPE_SCHOOL_PRICE_STORAGE_{gb}GB_ID is not configured")
    return price_id


async def create_renewal_checkout_session(
    school_id: str,
    curriculum_id: str,
    grade: int,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session (mode=payment) for curriculum renewal.

    Embeds school_id, curriculum_id, and product_type in metadata so the
    checkout.session.completed webhook can activate the renewal without
    needing a synchronous API call from the frontend.

    Returns the Stripe-hosted checkout URL.
    """
    from config import settings

    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    price_id = getattr(settings, "STRIPE_SCHOOL_PRICE_RENEWAL_ID", None)
    if not price_id:
        raise RuntimeError("STRIPE_SCHOOL_PRICE_RENEWAL_ID is not configured")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "school_id": school_id,
            "curriculum_id": curriculum_id,
            "grade": str(grade),
            "product_type": "curriculum_renewal",
        },
    )
    return session.url


async def create_storage_checkout_session(
    school_id: str,
    gb_package: int,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session (mode=payment) for a storage add-on.

    gb_package must be one of: 5, 10, 25.
    On payment, the checkout.session.completed webhook increments
    school_storage_quotas.purchased_gb by gb_package.

    Returns the Stripe-hosted checkout URL.
    """
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    price_id = _storage_price_id(gb_package)

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "school_id": school_id,
            "additional_gb": str(gb_package),
            "product_type": "storage_addon",
        },
    )
    return session.url


# ── Retention billing — webhook event handlers ────────────────────────────────


async def handle_curriculum_renewal_payment(
    conn: asyncpg.Connection,
    school_id: str,
    curriculum_id: str,
) -> None:
    """
    Called on checkout.session.completed with product_type='curriculum_renewal'.

    Renews the curriculum: extends expires_at by 1 year, resets retention_status
    to 'active', clears grace_until, sets renewed_at = NOW().

    Idempotent: if the curriculum is already active (was renewed via the API
    before the webhook arrived), the UPDATE is a safe no-op (status stays active).
    Purged curricula are logged as a warning — the payment succeeded but the
    content was already deleted; refund must be handled manually.
    """
    row = await conn.fetchrow(
        """
        SELECT curriculum_id, grade, retention_status
        FROM curricula
        WHERE curriculum_id = $1
          AND school_id = $2::uuid
          AND owner_type = 'school'
        """,
        curriculum_id, school_id,
    )

    if row is None:
        log.warning(
            "retention_renewal_curriculum_not_found curriculum_id=%s school_id=%s",
            curriculum_id, school_id,
        )
        return

    if row["retention_status"] == "purged":
        log.warning(
            "retention_renewal_curriculum_already_purged curriculum_id=%s school_id=%s "
            "— payment succeeded but content was already purged; manual refund may be needed",
            curriculum_id, school_id,
        )
        return

    await conn.execute(
        """
        UPDATE curricula
        SET expires_at       = expires_at + INTERVAL '1 year',
            grace_until      = NULL,
            retention_status = 'active',
            renewed_at       = NOW()
        WHERE curriculum_id = $1
        """,
        curriculum_id,
    )
    log.info(
        "retention_renewal_payment_applied curriculum_id=%s school_id=%s grade=%d",
        curriculum_id, school_id, row["grade"],
    )


async def handle_storage_addon_payment(
    conn: asyncpg.Connection,
    school_id: str,
    additional_gb: int,
) -> None:
    """
    Called on checkout.session.completed with product_type='storage_addon'.

    Increments school_storage_quotas.purchased_gb by additional_gb.

    Idempotent from the Stripe webhook perspective: the already_processed()
    check in the webhook handler prevents duplicate execution for the same
    stripe_event_id.
    """
    result = await conn.execute(
        """
        UPDATE school_storage_quotas
        SET purchased_gb = purchased_gb + $1,
            updated_at   = NOW()
        WHERE school_id = $2::uuid
        """,
        additional_gb, school_id,
    )
    if result == "UPDATE 0":
        log.warning(
            "storage_addon_no_quota_row school_id=%s additional_gb=%d",
            school_id, additional_gb,
        )
    else:
        log.info(
            "storage_addon_applied school_id=%s additional_gb=%d",
            school_id, additional_gb,
        )
