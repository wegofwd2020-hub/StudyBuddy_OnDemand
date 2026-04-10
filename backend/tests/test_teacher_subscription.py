"""
tests/test_teacher_subscription.py

Tests for independent teacher subscription endpoints (#57):
  POST   /teachers/{teacher_id}/subscription/checkout
  GET    /teachers/{teacher_id}/subscription
  DELETE /teachers/{teacher_id}/subscription

Plus service-layer unit tests:
  - get_teacher_subscription_status()
  - check_student_seat_limit()
  - handle_teacher_subscription_activated()
  - handle_teacher_subscription_updated()
  - handle_teacher_subscription_deleted()
  - handle_teacher_payment_failed()

And webhook routing for teacher subscription events.

All Stripe SDK calls are mocked — no live API keys required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────

_INDEPENDENT_TEACHER_ID = "a1000000-0000-4000-8000-000000000001"
_SCHOOL_TEACHER_ID       = "a2000000-0000-4000-8000-000000000002"
_SCHOOL_ID               = "b1000000-0000-4000-8000-000000000001"


def _indep_token(teacher_id: str = _INDEPENDENT_TEACHER_ID) -> str:
    """JWT for an independent teacher (no school_id)."""
    return make_teacher_token(teacher_id=teacher_id, school_id=None)


def _school_token(teacher_id: str = _SCHOOL_TEACHER_ID) -> str:
    """JWT for a school-affiliated teacher."""
    return make_teacher_token(teacher_id=teacher_id, school_id=_SCHOOL_ID)


async def _create_independent_teacher(client: AsyncClient, teacher_id: str) -> None:
    """Insert a teacher row with school_id=NULL directly via pool.

    Sets app.current_school_id='bypass' to satisfy the FORCE ROW LEVEL SECURITY
    policy on teachers (migration 0028).  Independent teachers have no school_id
    so 'bypass' is the correct sentinel for fixture inserts.
    """
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers (teacher_id, school_id, external_auth_id,
                                  auth_provider, name, email, role, account_status)
            VALUES ($1::uuid, NULL, $2, 'auth0', 'Indie Teacher', $3, 'teacher', 'active')
            ON CONFLICT (teacher_id) DO NOTHING
            """,
            uuid.UUID(teacher_id),
            f"auth0|indep_{teacher_id[:8]}",
            f"indie_{teacher_id[:8]}@example.com",
        )


async def _insert_teacher_subscription(
    client: AsyncClient,
    teacher_id: str,
    plan: str = "solo",
    status: str = "active",
    stripe_sub_id: str | None = None,
    max_students: int | None = None,
) -> str:
    """Insert a teacher_subscriptions row directly via pool."""
    sub_id = stripe_sub_id or f"sub_teacher_{uuid.uuid4().hex[:12]}"
    from src.pricing import get_teacher_plan
    ms = max_students if max_students is not None else get_teacher_plan(plan).max_students
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teacher_subscriptions
                (teacher_id, plan, status, max_students,
                 stripe_customer_id, stripe_subscription_id, current_period_end)
            VALUES ($1::uuid, $2, $3, $4, 'cus_test_teacher', $5,
                    NOW() + INTERVAL '30 days')
            ON CONFLICT (teacher_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                status = EXCLUDED.status,
                max_students = EXCLUDED.max_students,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                updated_at = NOW()
            """,
            uuid.UUID(teacher_id),
            plan, status, ms, sub_id,
        )
        # Stamp teacher_plan column
        await conn.execute(
            "UPDATE teachers SET teacher_plan = $1 WHERE teacher_id = $2::uuid",
            plan if status == "active" else None,
            uuid.UUID(teacher_id),
        )
    return sub_id


# ── GET /teachers/{teacher_id}/subscription — no subscription ────────────────


@pytest.mark.asyncio
async def test_teacher_subscription_status_no_subscription(client: AsyncClient):
    """Returns plan='none', status=None when no subscription exists."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(tid)

    r = await client.get(
        f"/api/v1/teachers/{tid}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "none"
    assert data["status"] is None
    assert data["max_students"] == 0
    assert data["seats_used_students"] == 0


@pytest.mark.asyncio
async def test_teacher_subscription_status_active(client: AsyncClient):
    """Returns correct plan, status, and seat cap when subscription is active."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    await _insert_teacher_subscription(client, tid, plan="growth")
    token = _indep_token(tid)

    r = await client.get(
        f"/api/v1/teachers/{tid}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "growth"
    assert data["status"] == "active"
    assert data["max_students"] == 75


@pytest.mark.asyncio
async def test_teacher_subscription_status_forbidden_other_teacher(client: AsyncClient):
    """Cannot read another teacher's subscription."""
    tid = str(uuid.uuid4())
    other_tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(other_tid)   # JWT for a different teacher

    r = await client.get(
        f"/api/v1/teachers/{tid}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ── POST /teachers/{teacher_id}/subscription/checkout ────────────────────────


@pytest.mark.asyncio
async def test_teacher_checkout_school_affiliated_blocked(client: AsyncClient):
    """School-affiliated teachers cannot initiate an independent subscription."""
    # Register a real school so we have a valid school_id FK target.
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Affiliated School",
        "contact_email": f"admin-{uuid.uuid4().hex[:8]}@example.com",
        "country": "US",
    })
    assert r.status_code == 201, r.text
    real_school_id = r.json()["school_id"]
    real_teacher_id = r.json()["teacher_id"]

    token = make_teacher_token(teacher_id=real_teacher_id, school_id=real_school_id)

    r = await client.post(
        f"/api/v1/teachers/{real_teacher_id}/subscription/checkout",
        json={
            "plan": "solo",
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "school_affiliated"


@pytest.mark.asyncio
async def test_teacher_checkout_invalid_plan_rejected(client: AsyncClient):
    """Invalid plan name returns 422."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(tid)

    r = await client.post(
        f"/api/v1/teachers/{tid}/subscription/checkout",
        json={
            "plan": "enterprise",   # not a valid teacher plan
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_teacher_checkout_price_not_configured_returns_503(client: AsyncClient):
    """Returns 503 when Stripe price ID is not set in config."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(tid)

    with patch("src.teacher.subscription_service._stripe_key", return_value="sk_test"):
        with patch("src.teacher.subscription_service._teacher_price_id",
                   side_effect=RuntimeError("STRIPE_TEACHER_PRICE_SOLO_ID is not configured")):
            r = await client.post(
                f"/api/v1/teachers/{tid}/subscription/checkout",
                json={
                    "plan": "solo",
                    "success_url": "https://app.example.com/success",
                    "cancel_url": "https://app.example.com/cancel",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 503
    assert r.json()["error"] == "payment_unavailable"


@pytest.mark.asyncio
async def test_teacher_checkout_returns_stripe_url(client: AsyncClient):
    """Returns checkout_url from Stripe on success."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(tid)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"

    with patch("src.teacher.subscription_service._stripe_key", return_value="sk_test"):
        with patch("src.teacher.subscription_service._teacher_price_id", return_value="price_test_solo"):
            with patch("src.teacher.subscription_service._run_stripe",
                       return_value=mock_session):
                with patch("src.teacher.subscription_service._get_stripe"):
                    r = await client.post(
                        f"/api/v1/teachers/{tid}/subscription/checkout",
                        json={
                            "plan": "solo",
                            "success_url": "https://app.example.com/success",
                            "cancel_url": "https://app.example.com/cancel",
                        },
                        headers={"Authorization": f"Bearer {token}"},
                    )
    assert r.status_code == 200, r.text
    assert r.json()["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_abc123"


# ── DELETE /teachers/{teacher_id}/subscription ───────────────────────────────


@pytest.mark.asyncio
async def test_teacher_cancel_no_subscription_returns_404(client: AsyncClient):
    """Returns 404 when there is no active subscription to cancel."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    token = _indep_token(tid)

    r = await client.delete(
        f"/api/v1/teachers/{tid}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_teacher_cancel_sets_cancelled_at_period_end(client: AsyncClient):
    """Cancellation sets status=cancelled and returns current_period_end."""
    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    sub_id = await _insert_teacher_subscription(client, tid, plan="solo")
    token = _indep_token(tid)

    with patch("src.teacher.subscription_service._stripe_key", return_value="sk_test"):
        with patch("src.teacher.subscription_service._run_stripe", return_value=MagicMock()):
            with patch("src.teacher.subscription_service._get_stripe"):
                r = await client.delete(
                    f"/api/v1/teachers/{tid}/subscription",
                    headers={"Authorization": f"Bearer {token}"},
                )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "cancelled_at_period_end"
    assert data["current_period_end"] is not None


# ── Service-layer unit tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_teacher_subscription_activated(client: AsyncClient):
    """Activation creates teacher_subscriptions row and stamps teacher_plan."""
    from src.teacher.subscription_service import (
        get_teacher_subscription_status,
        handle_teacher_subscription_activated,
    )

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await handle_teacher_subscription_activated(
            conn,
            teacher_id=tid,
            plan="growth",
            stripe_customer_id="cus_test_abc",
            stripe_subscription_id="sub_test_abc",
            current_period_end=datetime.now(UTC) + timedelta(days=30),
        )
        status = await get_teacher_subscription_status(conn, tid)
        # Read teacher_plan on the same connection (bypass is set) so RLS doesn't
        # filter out the independent-teacher row (school_id IS NULL).
        plan_col = await conn.fetchval(
            "SELECT teacher_plan FROM teachers WHERE teacher_id = $1::uuid",
            uuid.UUID(tid),
        )

    assert status["plan"] == "growth"
    assert status["status"] == "active"
    assert status["max_students"] == 75
    assert plan_col == "growth"


@pytest.mark.asyncio
async def test_handle_teacher_subscription_activated_is_idempotent(client: AsyncClient):
    """Calling activated twice (replay) does not create duplicate rows."""
    from src.teacher.subscription_service import handle_teacher_subscription_activated

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for _ in range(2):
            await handle_teacher_subscription_activated(
                conn,
                teacher_id=tid,
                plan="solo",
                stripe_customer_id="cus_idempotent",
                stripe_subscription_id="sub_idempotent",
                current_period_end=datetime.now(UTC) + timedelta(days=30),
            )
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM teacher_subscriptions WHERE teacher_id = $1::uuid",
            uuid.UUID(tid),
        )
    assert count == 1


@pytest.mark.asyncio
async def test_handle_teacher_subscription_updated_changes_status(client: AsyncClient):
    """Updated event changes status and period_end."""
    from src.teacher.subscription_service import (
        get_teacher_subscription_status,
        handle_teacher_subscription_updated,
    )

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    sub_id = await _insert_teacher_subscription(client, tid, plan="pro", stripe_sub_id="sub_upd_test")

    new_period_end = datetime.now(UTC) + timedelta(days=60)
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await handle_teacher_subscription_updated(conn, sub_id, "past_due", new_period_end)
        status = await get_teacher_subscription_status(conn, tid)

    assert status["status"] == "past_due"


@pytest.mark.asyncio
async def test_handle_teacher_subscription_deleted_clears_plan(client: AsyncClient):
    """Deleted event sets status=cancelled and clears teacher_plan column."""
    from src.teacher.subscription_service import (
        get_teacher_subscription_status,
        handle_teacher_subscription_deleted,
    )

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    sub_id = await _insert_teacher_subscription(client, tid, plan="solo", stripe_sub_id="sub_del_test")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await handle_teacher_subscription_deleted(conn, sub_id)
        status = await get_teacher_subscription_status(conn, tid)
        plan_col = await conn.fetchval(
            "SELECT teacher_plan FROM teachers WHERE teacher_id = $1::uuid",
            uuid.UUID(tid),
        )

    assert status["status"] == "cancelled"
    assert plan_col is None


@pytest.mark.asyncio
async def test_handle_teacher_payment_failed_sets_past_due(client: AsyncClient):
    """payment_failed sets status=past_due and stamps grace_period_end."""
    from src.teacher.subscription_service import handle_teacher_payment_failed

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    sub_id = await _insert_teacher_subscription(
        client, tid, plan="growth", stripe_sub_id="sub_fail_test"
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await handle_teacher_payment_failed(conn, sub_id)
        row = await conn.fetchrow(
            "SELECT status, grace_period_end FROM teacher_subscriptions WHERE teacher_id = $1::uuid",
            uuid.UUID(tid),
        )

    assert row["status"] == "past_due"
    assert row["grace_period_end"] is not None


# ── Webhook routing ───────────────────────────────────────────────────────────


def _make_webhook_teacher_session(metadata: dict, sub_id: str = "sub_wh_test") -> dict:
    return {
        "id": f"cs_test_{uuid.uuid4().hex[:16]}",
        "object": "checkout.session",
        "customer": "cus_webhook_teacher",
        "subscription": sub_id,
        "metadata": metadata,
    }


@pytest.mark.asyncio
async def test_webhook_teacher_checkout_activates_subscription(client: AsyncClient):
    """Webhook with product_type=teacher_subscription creates subscription row."""
    from src.teacher.subscription_service import get_teacher_subscription_status

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)

    stripe_event_id = f"evt_teacher_{uuid.uuid4().hex[:12]}"
    session = _make_webhook_teacher_session({
        "teacher_id": tid,
        "plan": "solo",
        "product_type": "teacher_subscription",
    })

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {
        "id": stripe_event_id,
        "type": "checkout.session.completed",
        "data": {"object": session},
    }
    # Mock Subscription.retrieve to return a period_end timestamp
    future_ts = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    mock_stripe.Subscription.retrieve.return_value = {"current_period_end": future_ts}

    with patch("src.subscription.router._get_stripe_module", return_value=mock_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            mock_settings.STRIPE_SECRET_KEY = "sk_test"
            with patch("src.subscription.service.already_processed", return_value=False):
                with patch("src.subscription.service.log_stripe_event", return_value=None):
                    r = await client.post(
                        "/api/v1/subscription/webhook",
                        content=b"payload",
                        headers={"stripe-signature": "t=1,v1=sig"},
                    )

    assert r.status_code == 200, r.text
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        status = await get_teacher_subscription_status(conn, tid)
    assert status["plan"] == "solo"
    assert status["status"] == "active"


@pytest.mark.asyncio
async def test_webhook_teacher_subscription_deleted(client: AsyncClient):
    """Webhook customer.subscription.deleted cancels teacher subscription."""
    from src.teacher.subscription_service import get_teacher_subscription_status

    tid = str(uuid.uuid4())
    await _create_independent_teacher(client, tid)
    sub_id = await _insert_teacher_subscription(
        client, tid, plan="growth", stripe_sub_id="sub_del_wh"
    )

    stripe_event_id = f"evt_del_{uuid.uuid4().hex[:12]}"
    obj = {"id": sub_id, "status": "canceled", "current_period_end": None}

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {
        "id": stripe_event_id,
        "type": "customer.subscription.deleted",
        "data": {"object": obj},
    }

    with patch("src.subscription.router._get_stripe_module", return_value=mock_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            with patch("src.subscription.service.already_processed", return_value=False):
                with patch("src.subscription.service.log_stripe_event", return_value=None):
                    r = await client.post(
                        "/api/v1/subscription/webhook",
                        content=b"payload",
                        headers={"stripe-signature": "t=1,v1=sig"},
                    )

    assert r.status_code == 200, r.text
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        status = await get_teacher_subscription_status(conn, tid)
    assert status["status"] == "cancelled"


# ── Pricing constants ─────────────────────────────────────────────────────────


def test_teacher_plan_prices():
    """Verify pricing constants match the agreed rates."""
    from src.pricing import TEACHER_PLANS
    assert TEACHER_PLANS["solo"].price_monthly == "29.00"
    assert TEACHER_PLANS["solo"].max_students == 25
    assert TEACHER_PLANS["growth"].price_monthly == "59.00"
    assert TEACHER_PLANS["growth"].max_students == 75
    assert TEACHER_PLANS["pro"].price_monthly == "99.00"
    assert TEACHER_PLANS["pro"].max_students == 200


def test_get_teacher_plan_invalid_raises():
    """get_teacher_plan raises KeyError for unknown plan IDs."""
    from src.pricing import get_teacher_plan
    with pytest.raises(KeyError):
        get_teacher_plan("enterprise")
