"""
backend/src/teacher/connect_service.py

Business logic for Stripe Connect (Express) revenue-share billing — Option B (#104).

Under Option B an independent teacher:
  1. Onboards with Stripe Connect (Express account).
  2. Students pay a recurring monthly fee to the platform.
  3. Stripe automatically transfers TEACHER_REVENUE_SHARE_PCT % to the teacher's
     Connect account and keeps CONNECT_APPLICATION_FEE_PCT % as a platform fee.
  4. No flat monthly fee is charged to the teacher.

Public API
──────────
  create_connect_account(teacher_id, email)
      → str  (stripe_account_id)

  create_onboarding_link(teacher_id, stripe_account_id, return_url, refresh_url)
      → str  (Stripe-hosted onboarding URL)

  get_connect_account(conn, teacher_id)
      → dict | None

  sync_connect_account(conn, teacher_id, stripe_account_id,
                       charges_enabled, payouts_enabled)
      → None  (upserts teacher_connect_accounts; sets billing_model on activation)

  create_student_checkout_session(
      teacher_id, student_id, stripe_account_id,
      success_url, cancel_url,
  ) → str  (Stripe-hosted checkout URL)

  get_earnings(stripe_account_id, limit)
      → list[dict]  (recent Stripe Transfer objects)

  handle_student_subscription_activated(conn, student_id, teacher_id,
      stripe_customer_id, stripe_subscription_id, current_period_end)
      → None

  handle_student_subscription_updated(conn, stripe_subscription_id,
      status, current_period_end)
      → None

  handle_student_subscription_deleted(conn, stripe_subscription_id)
      → None

  handle_student_payment_failed(conn, stripe_subscription_id)
      → None

  find_teacher_by_student_subscription(conn, stripe_subscription_id)
      → str | None  (teacher_id or None)
"""

from __future__ import annotations

import asyncio
from functools import partial

import asyncpg

from src.pricing import CONNECT_APPLICATION_FEE_PCT
from src.utils.logger import get_logger

log = get_logger("teacher.connect")


# ── Stripe helpers ─────────────────────────────────────────────────────────────


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


def _student_connect_price_id() -> str:
    from config import settings
    price_id = getattr(settings, "STRIPE_STUDENT_CONNECT_PRICE_ID", None)
    if not price_id:
        raise RuntimeError("STRIPE_STUDENT_CONNECT_PRICE_ID is not configured")
    return price_id


async def _run_stripe(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


# ── Onboarding ─────────────────────────────────────────────────────────────────


async def create_connect_account(teacher_id: str, email: str) -> str:
    """
    Create a Stripe Express Connect account for the teacher.

    Returns the stripe_account_id (e.g. 'acct_...').
    The account is stored in teacher_connect_accounts by the caller after this
    returns.  The teacher must complete onboarding via the link returned by
    create_onboarding_link() before charges are enabled.
    """
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    account = await _run_stripe(
        stripe.Account.create,
        type="express",
        email=email,
        metadata={"teacher_id": teacher_id},
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    )
    log.info(
        "connect_account_created teacher_id=%s stripe_account_id=%s",
        teacher_id, account["id"],
    )
    return account["id"]


async def create_onboarding_link(
    teacher_id: str,
    stripe_account_id: str,
    return_url: str,
    refresh_url: str,
) -> str:
    """
    Create a Stripe AccountLink (type=account_onboarding) for the teacher.

    Returns the URL the teacher should be redirected to.  Links expire after
    ~5 minutes; POST /connect/refresh to get a fresh one.
    """
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    link = await _run_stripe(
        stripe.AccountLink.create,
        account=stripe_account_id,
        return_url=return_url,
        refresh_url=refresh_url,
        type="account_onboarding",
    )
    log.info(
        "connect_onboarding_link_created teacher_id=%s account=%s",
        teacher_id, stripe_account_id,
    )
    return link["url"]


# ── DB helpers ─────────────────────────────────────────────────────────────────


async def get_connect_account(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> dict | None:
    """Return the teacher_connect_accounts row for teacher_id, or None."""
    row = await conn.fetchrow(
        """
        SELECT teacher_id::text, stripe_account_id,
               onboarding_complete, charges_enabled, payouts_enabled,
               last_synced_at, created_at
        FROM teacher_connect_accounts
        WHERE teacher_id = $1::uuid
        """,
        teacher_id,
    )
    if row is None:
        return None
    return dict(row)


async def sync_connect_account(
    conn: asyncpg.Connection,
    teacher_id: str,
    stripe_account_id: str,
    charges_enabled: bool,
    payouts_enabled: bool,
) -> None:
    """
    Upsert teacher_connect_accounts with the latest capability state from Stripe.

    Called on account.updated webhook events and after onboarding completes.
    Sets onboarding_complete=True once both charges_enabled and payouts_enabled
    are True, and stamps teachers.billing_model='revenue_share' at that point.
    """
    onboarding_complete = charges_enabled and payouts_enabled

    await conn.execute(
        """
        INSERT INTO teacher_connect_accounts
            (teacher_id, stripe_account_id, onboarding_complete,
             charges_enabled, payouts_enabled, last_synced_at)
        VALUES ($1::uuid, $2, $3, $4, $5, NOW())
        ON CONFLICT (teacher_id) DO UPDATE SET
            stripe_account_id   = EXCLUDED.stripe_account_id,
            onboarding_complete = EXCLUDED.onboarding_complete,
            charges_enabled     = EXCLUDED.charges_enabled,
            payouts_enabled     = EXCLUDED.payouts_enabled,
            last_synced_at      = NOW(),
            updated_at          = NOW()
        """,
        teacher_id,
        stripe_account_id,
        onboarding_complete,
        charges_enabled,
        payouts_enabled,
    )

    if onboarding_complete:
        await conn.execute(
            """
            UPDATE teachers
            SET billing_model = 'revenue_share'
            WHERE teacher_id = $1::uuid AND billing_model IS DISTINCT FROM 'revenue_share'
            """,
            teacher_id,
        )
        log.info(
            "connect_account_onboarding_complete teacher_id=%s account=%s",
            teacher_id, stripe_account_id,
        )


# ── Student checkout ───────────────────────────────────────────────────────────


async def create_student_checkout_session(
    teacher_id: str,
    student_id: str,
    stripe_account_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session (mode=subscription) for a student enrolling
    under an Option-B teacher.

    The session sets application_fee_percent=CONNECT_APPLICATION_FEE_PCT and
    transfer_data.destination=stripe_account_id so Stripe automatically forwards
    the teacher's share on every invoice payment.

    Returns the Stripe-hosted checkout URL.
    """
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()
    price_id = _student_connect_price_id()

    session = await _run_stripe(
        stripe.checkout.Session.create,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        subscription_data={
            "application_fee_percent": CONNECT_APPLICATION_FEE_PCT,
            "transfer_data": {"destination": stripe_account_id},
            "metadata": {
                "product_type": "student_connect_subscription",
                "teacher_id": teacher_id,
                "student_id": student_id,
            },
        },
        metadata={
            "product_type": "student_connect_subscription",
            "teacher_id": teacher_id,
            "student_id": student_id,
        },
    )
    log.info(
        "student_connect_checkout_created teacher_id=%s student_id=%s",
        teacher_id, student_id,
    )
    return session.url


# ── Earnings ───────────────────────────────────────────────────────────────────


async def get_earnings(stripe_account_id: str, limit: int = 25) -> list[dict]:
    """
    Return recent Stripe Transfer objects destined for the teacher's Connect
    account.  Each dict contains: id, amount (cents), currency, created (unix ts),
    description.

    Uses the platform account's API key (the platform owns the Transfer objects)
    and filters by destination=stripe_account_id.
    """
    stripe = _get_stripe()
    stripe.api_key = _stripe_key()

    transfers = await _run_stripe(
        stripe.Transfer.list,
        destination=stripe_account_id,
        limit=min(limit, 100),
    )
    results = []
    for t in transfers.get("data", []):
        results.append({
            "transfer_id": t["id"],
            "amount_cents": t["amount"],
            "currency": t.get("currency", "usd"),
            "created": t["created"],
            "description": t.get("description") or "",
        })
    return results


# ── Webhook handlers ───────────────────────────────────────────────────────────


async def handle_student_subscription_activated(
    conn: asyncpg.Connection,
    student_id: str,
    teacher_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end,
) -> None:
    """
    Called on checkout.session.completed for product_type='student_connect_subscription'.

    Upserts student_connect_subscriptions.  Idempotent — safe on replay.
    """
    await conn.execute(
        """
        INSERT INTO student_connect_subscriptions
            (student_id, teacher_id, stripe_customer_id,
             stripe_subscription_id, status, current_period_end)
        VALUES ($1::uuid, $2::uuid, $3, $4, 'active', $5)
        ON CONFLICT (student_id, teacher_id) DO UPDATE SET
            stripe_customer_id     = EXCLUDED.stripe_customer_id,
            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
            status                 = 'active',
            current_period_end     = EXCLUDED.current_period_end,
            updated_at             = NOW()
        """,
        student_id,
        teacher_id,
        stripe_customer_id,
        stripe_subscription_id,
        current_period_end,
    )
    log.info(
        "student_connect_subscription_activated student_id=%s teacher_id=%s",
        student_id, teacher_id,
    )


async def handle_student_subscription_updated(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
    status: str,
    current_period_end,
) -> None:
    """Called on customer.subscription.updated for a student Connect subscription."""
    clear_grace = "grace_period_end = NULL," if status == "active" else ""
    await conn.execute(
        f"""
        UPDATE student_connect_subscriptions
        SET status = $1,
            {clear_grace}
            current_period_end = $2,
            updated_at = NOW()
        WHERE stripe_subscription_id = $3
        """,
        status, current_period_end, stripe_subscription_id,
    )
    log.info(
        "student_connect_subscription_updated sub_id=%s status=%s",
        stripe_subscription_id, status,
    )


async def handle_student_subscription_deleted(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> None:
    """Called on customer.subscription.deleted for a student Connect subscription."""
    await conn.execute(
        """
        UPDATE student_connect_subscriptions
        SET status = 'cancelled', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        """,
        stripe_subscription_id,
    )
    log.info(
        "student_connect_subscription_deleted sub_id=%s", stripe_subscription_id,
    )


async def handle_student_payment_failed(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> None:
    """
    Called on invoice.payment_failed for a student Connect subscription.

    Sets status='past_due' and stamps a 7-day grace window.
    """
    await conn.execute(
        """
        UPDATE student_connect_subscriptions
        SET status = 'past_due',
            grace_period_end = NOW() + INTERVAL '7 days',
            updated_at = NOW()
        WHERE stripe_subscription_id = $1
        """,
        stripe_subscription_id,
    )
    log.info("student_connect_payment_failed sub_id=%s", stripe_subscription_id)


async def find_teacher_by_student_subscription(
    conn: asyncpg.Connection,
    stripe_subscription_id: str,
) -> str | None:
    """Return teacher_id for a student Connect stripe_subscription_id, or None."""
    return await conn.fetchval(
        """
        SELECT teacher_id::text
        FROM student_connect_subscriptions
        WHERE stripe_subscription_id = $1
        """,
        stripe_subscription_id,
    )
