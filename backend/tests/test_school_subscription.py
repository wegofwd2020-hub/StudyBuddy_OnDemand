"""
tests/test_school_subscription.py

Tests for school subscription endpoints:
  POST   /schools/{school_id}/subscription/checkout
  GET    /schools/{school_id}/subscription
  DELETE /schools/{school_id}/subscription

Plus webhook routing for school events and seat limit enforcement.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    """Register a school and return {school_id, teacher_id, access_token}."""
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Subscription Test School",
        "contact_email": f"admin-{uuid.uuid4().hex[:8]}@example.com",
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _insert_school_subscription(
    client: AsyncClient,
    school_id: str,
    plan: str = "professional",
    status: str = "active",
    max_students: int = 150,
    max_teachers: int = 10,
    stripe_sub_id: str | None = None,
) -> str:
    """Insert a school_subscriptions row directly via the pool."""
    sub_id = stripe_sub_id or f"sub_school_{uuid.uuid4().hex[:12]}"
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
             max_students, max_teachers, current_period_end)
        VALUES ($1, $2, $3, 'cus_test', $4, $5, $6, NOW() + INTERVAL '30 days')
        ON CONFLICT (school_id) DO UPDATE
            SET plan = EXCLUDED.plan, status = EXCLUDED.status,
                max_students = EXCLUDED.max_students, max_teachers = EXCLUDED.max_teachers,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                updated_at = NOW()
        """,
        uuid.UUID(school_id),
        plan,
        status,
        sub_id,
        max_students,
        max_teachers,
    )
    return sub_id


# ── GET /schools/{school_id}/subscription ────────────────────────────────────


@pytest.mark.asyncio
async def test_school_subscription_status_no_subscription(client: AsyncClient):
    """Returns plan='none' and status=None when no subscription exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/schools/{school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "none"
    assert data["status"] is None
    assert data["seats_used_students"] == 0
    assert data["seats_used_teachers"] >= 1  # the school_admin teacher counts


@pytest.mark.asyncio
async def test_school_subscription_status_active(client: AsyncClient):
    """Returns correct plan, status, and max seats when subscription exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    await _insert_school_subscription(client, school_id, plan="professional", max_students=150)

    r = await client.get(
        f"/api/v1/schools/{school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "professional"
    assert data["status"] == "active"
    assert data["max_students"] == 150


@pytest.mark.asyncio
async def test_school_subscription_status_wrong_school_returns_403(client: AsyncClient):
    """Teacher cannot view subscription for a different school."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    other_school_id = str(uuid.uuid4())
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/schools/{other_school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_subscription_status_requires_auth(client: AsyncClient):
    r = await client.get(f"/api/v1/schools/{uuid.uuid4()}/subscription")
    assert r.status_code == 401


# ── POST /schools/{school_id}/subscription/checkout ──────────────────────────


@pytest.mark.asyncio
async def test_school_checkout_returns_url(client: AsyncClient):
    """Checkout returns a URL when Stripe is mocked."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    # Patch at the router's import location so the router picks up the mock
    with patch(
        "src.school.subscription_router.create_school_checkout_session",
        return_value="https://checkout.stripe.com/c/pay/test_school_123",
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/subscription/checkout",
            json={
                "plan": "professional",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert "checkout_url" in data
    assert "stripe.com" in data["checkout_url"]


@pytest.mark.asyncio
async def test_school_checkout_invalid_plan_returns_422(client: AsyncClient):
    """Unsupported plan name returns 422."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.post(
        f"/api/v1/schools/{school_id}/subscription/checkout",
        json={"plan": "monthly", "success_url": "https://x.com/ok", "cancel_url": "https://x.com/c"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_school_checkout_not_school_admin_returns_403(client: AsyncClient):
    """Regular teacher (not school_admin) cannot initiate checkout."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="teacher")

    r = await client.post(
        f"/api/v1/schools/{school_id}/subscription/checkout",
        json={"plan": "starter", "success_url": "https://x.com/ok", "cancel_url": "https://x.com/c"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_checkout_stripe_not_configured_returns_503(client: AsyncClient):
    """503 when Stripe price ID is not configured."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.post(
        f"/api/v1/schools/{school_id}/subscription/checkout",
        json={"plan": "starter", "success_url": "https://x.com/ok", "cancel_url": "https://x.com/c"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Without STRIPE_SCHOOL_PRICE_STARTER_ID configured, expect 503
    assert r.status_code == 503
    assert r.json()["error"] == "payment_unavailable"


# ── DELETE /schools/{school_id}/subscription ─────────────────────────────────


@pytest.mark.asyncio
async def test_school_subscription_cancel_no_subscription_returns_404(client: AsyncClient):
    """404 when school has no active subscription."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.delete(
        f"/api/v1/schools/{school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "no_active_subscription"


@pytest.mark.asyncio
async def test_school_subscription_cancel_mocked_stripe(client: AsyncClient):
    """Cancel sets status cancelled_at_period_end (Stripe mocked)."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")
    await _insert_school_subscription(client, school_id)

    # Patch at the router's import location
    with patch(
        "src.school.subscription_router.cancel_school_stripe_subscription"
    ) as mock_cancel:
        mock_cancel.return_value = None
        with patch(
            "src.school.subscription_router.expire_school_entitlement_cache"
        ) as mock_expire:
            mock_expire.return_value = None
            r = await client.delete(
                f"/api/v1/schools/{school_id}/subscription",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "cancelled_at_period_end"
    assert "current_period_end" in data


# ── Webhook routing ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_activates_school_subscription(client: AsyncClient):
    """checkout.session.completed with school_id in metadata activates school subscription."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    fake_event = {
        "id": f"evt_school_{uuid.uuid4().hex[:12]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"school_id": school_id, "plan": "starter"},
                "customer": "cus_school_test",
                "subscription": "sub_school_test_123",
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = fake_event
    mock_stripe.Subscription.retrieve.return_value = {
        "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    }
    mock_stripe.api_key = None

    with patch("src.subscription.router._get_stripe_module", return_value=mock_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            mock_settings.STRIPE_SECRET_KEY = "sk_test_xxx"
            with patch("src.school.subscription_service.expire_school_entitlement_cache") as mock_expire:
                mock_expire.return_value = None
                r = await client.post(
                    "/api/v1/subscription/webhook",
                    content=b'{"type":"checkout.session.completed"}',
                    headers={
                        "stripe-signature": "t=1,v1=dummy",
                        "content-type": "application/json",
                    },
                )

    assert r.status_code == 200, r.text

    # Verify school_subscriptions row was created
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT plan, status FROM school_subscriptions WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    assert row is not None
    assert row["plan"] == "starter"
    assert row["status"] == "active"


@pytest.mark.asyncio
async def test_webhook_deduplication_for_school_event(client: AsyncClient):
    """Second webhook with same event_id returns already_processed."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    event_id = f"evt_school_dup_{uuid.uuid4().hex[:12]}"

    # Pre-insert the event as already processed
    pool = client._transport.app.state.pool
    await pool.execute(
        "INSERT INTO stripe_events (stripe_event_id, event_type, outcome) VALUES ($1, $2, 'ok')",
        event_id,
        "checkout.session.completed",
    )

    fake_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"school_id": school_id, "plan": "starter"}}},
    }
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = fake_event

    with patch("src.subscription.router._get_stripe_module", return_value=mock_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=dummy"},
            )

    assert r.status_code == 200
    assert r.json()["status"] == "already_processed"


# ── Seat limit enforcement ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrolment_blocked_at_seat_limit(client: AsyncClient):
    """Enrolment upload returns 402 when student seat limit would be exceeded."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    # Subscription with max_students=1
    await _insert_school_subscription(client, school_id, max_students=1, max_teachers=10)

    # Uploading 2 students exceeds the limit of 1
    r = await client.post(
        f"/api/v1/schools/{school_id}/enrolment",
        json={"students": [{"email": "s1@test.com"}, {"email": "s2@test.com"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 402, r.text
    data = r.json()
    assert data["error"] == "seat_limit_reached"
    assert data["limit"] == 1


@pytest.mark.asyncio
async def test_enrolment_allowed_within_seat_limit(client: AsyncClient):
    """Enrolment upload succeeds when within the seat limit."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    # Subscription with max_students=50
    await _insert_school_subscription(client, school_id, max_students=50, max_teachers=10)

    r = await client.post(
        f"/api/v1/schools/{school_id}/enrolment",
        json={"students": [{"email": "stu1@test.com"}, {"email": "stu2@test.com"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_teacher_invite_blocked_at_seat_limit(client: AsyncClient):
    """Teacher invite returns 402 when teacher seat limit is reached."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    # max_teachers=1; school_admin already counts as 1 active teacher
    await _insert_school_subscription(client, school_id, max_students=50, max_teachers=1)

    r = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json={"name": "New Teacher", "email": f"newteacher-{uuid.uuid4().hex[:6]}@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 402, r.text
    assert r.json()["error"] == "seat_limit_reached"
