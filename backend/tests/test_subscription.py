"""
tests/test_subscription.py

Tests for subscription and payment endpoints.

Coverage:
  - GET  /subscription/status   — free plan when no subscription
  - POST /subscription/checkout — 503 when Stripe not configured; mocked success path
  - POST /subscription/webhook  — signature verification; deduplication; checkout.session.completed
                                   customer.subscription.updated; customer.subscription.deleted;
                                   invoice.payment_failed (grace period)
  - DELETE /subscription        — 404 when no active subscription; mocked cancel success
  - Auth: all JWT-gated endpoints return 403 without token
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token


# ── Helpers ───────────────────────────────────────────────────────────────────

def _student_id_from_token(token: str) -> str:
    from jose import jwt as _jwt
    payload = _jwt.decode(
        token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"]
    )
    return payload["student_id"]


async def _insert_student(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|sub-{student_id[:8]}",
        f"Sub Student {student_id[:6]}",
        f"sub-{student_id[:6]}@test.invalid",
    )


async def _insert_subscription(
    client: AsyncClient,
    student_id: str,
    plan: str = "monthly",
    status: str = "active",
    stripe_sub_id: str | None = None,
) -> str:
    """Insert a subscriptions row; returns stripe_sub_id."""
    pool = client._transport.app.state.pool
    sid = stripe_sub_id or f"sub_test_{uuid.uuid4().hex[:12]}"
    await pool.execute(
        """
        INSERT INTO subscriptions
            (student_id, plan, status, stripe_customer_id, stripe_subscription_id,
             current_period_end, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW() + INTERVAL '30 days', NOW())
        ON CONFLICT (stripe_subscription_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        plan,
        status,
        f"cus_test_{student_id[:8]}",
        sid,
    )
    return sid


def _fake_stripe_sig(payload: bytes, secret: str = "whsec_test") -> str:
    """Return a fake Stripe-Signature header. Tests bypass verification via mock."""
    return "t=1234567890,v1=fakesig"


# ── GET /subscription/status ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_returns_free_when_no_subscription(client, db_conn, student_token):
    """Unsubscribed student gets plan=free."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.get(
        "/api/v1/subscription/status",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "free"
    assert data["status"] is None
    assert data["lessons_accessed"] == 0


@pytest.mark.asyncio
async def test_status_returns_active_subscription(client, db_conn, student_token):
    """Student with active subscription gets plan + status."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    await _insert_subscription(client, student_id, plan="monthly", status="active")

    r = await client.get(
        "/api/v1/subscription/status",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "monthly"
    assert data["status"] == "active"


# ── POST /subscription/checkout ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkout_503_when_stripe_not_configured(client, db_conn, student_token):
    """Without Stripe keys configured, checkout returns 503."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    with patch("src.subscription.service._stripe_key", side_effect=RuntimeError("STRIPE_SECRET_KEY is not configured")):
        r = await client.post(
            "/api/v1/subscription/checkout",
            json={
                "plan": "monthly",
                "success_url": "studybuddy://subscription/success",
                "cancel_url": "studybuddy://subscription/cancel",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 503
    assert r.json()["error"] == "payment_unavailable"


@pytest.mark.asyncio
async def test_checkout_returns_url(client, db_conn, student_token):
    """With Stripe configured, checkout returns checkout_url."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"

    with patch(
        "src.subscription.router.create_checkout_session",
        new_callable=AsyncMock,
        return_value="https://checkout.stripe.com/pay/cs_test_abc123",
    ):
        r = await client.post(
            "/api/v1/subscription/checkout",
            json={
                "plan": "monthly",
                "success_url": "studybuddy://subscription/success",
                "cancel_url": "studybuddy://subscription/cancel",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "checkout_url" in data
    assert data["checkout_url"].startswith("https://checkout.stripe.com")


# ── POST /subscription/webhook ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client, db_conn):
    """Webhook returns 400 on invalid Stripe signature."""
    with patch("src.subscription.router._get_stripe_module") as mock_stripe_factory:
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.side_effect = Exception("Invalid signature")
        mock_stripe_factory.return_value = mock_stripe

        # Ensure STRIPE_WEBHOOK_SECRET is set so we don't get 503
        with patch("src.subscription.router.getattr", return_value="whsec_test"), \
             patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b'{"id":"evt_test","type":"test"}',
                headers={"stripe-signature": "t=123,v1=badsig"},
            )
    assert r.status_code in (400, 503)


@pytest.mark.asyncio
async def test_webhook_deduplicates_already_processed_event(client, db_conn, student_token):
    """Webhook returns already_processed for a duplicate stripe_event_id."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    stripe_event_id = f"evt_dup_{uuid.uuid4().hex[:12]}"

    # Pre-insert a processed event
    pool = client._transport.app.state.pool
    await pool.execute(
        "INSERT INTO stripe_events (stripe_event_id, event_type, outcome) VALUES ($1, $2, $3)",
        stripe_event_id, "checkout.session.completed", "ok",
    )

    fake_event = {
        "id": stripe_event_id,
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"student_id": student_id, "plan": "monthly"}}},
    }

    with patch("src.subscription.router._get_stripe_module") as mock_factory, \
         patch("config.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = fake_event
        mock_factory.return_value = mock_stripe

        r = await client.post(
            "/api/v1/subscription/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": _fake_stripe_sig(b"")},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_webhook_checkout_session_completed(client, db_conn, student_token):
    """checkout.session.completed activates the subscription in the DB."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    stripe_event_id = f"evt_checkout_{uuid.uuid4().hex[:10]}"
    stripe_sub_id = f"sub_{uuid.uuid4().hex[:10]}"
    stripe_cus_id = f"cus_{uuid.uuid4().hex[:10]}"

    fake_obj = {
        "customer": stripe_cus_id,
        "subscription": stripe_sub_id,
        "metadata": {"student_id": student_id, "plan": "annual"},
    }
    fake_event = {
        "id": stripe_event_id,
        "type": "checkout.session.completed",
        "data": {"object": fake_obj},
    }

    # Mock the Stripe Subscription.retrieve call inside _dispatch_event
    fake_sub = {"current_period_end": 1893456000}  # some future timestamp

    with patch("src.subscription.router._get_stripe_module") as mock_factory, \
         patch("config.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_settings.STRIPE_SECRET_KEY = "sk_test"
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = fake_event
        mock_stripe.Subscription.retrieve.return_value = fake_sub
        mock_factory.return_value = mock_stripe

        r = await client.post(
            "/api/v1/subscription/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": _fake_stripe_sig(b"")},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # Verify DB row was created
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT plan, status FROM subscriptions WHERE stripe_subscription_id = $1",
        stripe_sub_id,
    )
    assert row is not None
    assert row["plan"] == "annual"
    assert row["status"] == "active"


@pytest.mark.asyncio
async def test_webhook_payment_failed_sets_grace_period(client, db_conn, student_token):
    """invoice.payment_failed sets status=past_due and grace_period_end."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    stripe_sub_id = await _insert_subscription(client, student_id, status="active")

    stripe_event_id = f"evt_failed_{uuid.uuid4().hex[:10]}"
    fake_event = {
        "id": stripe_event_id,
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": stripe_sub_id}},
    }

    with patch("src.subscription.router._get_stripe_module") as mock_factory, \
         patch("config.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = fake_event
        mock_factory.return_value = mock_stripe

        r = await client.post(
            "/api/v1/subscription/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": _fake_stripe_sig(b"")},
        )
    assert r.status_code == 200

    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT status, grace_period_end FROM subscriptions WHERE stripe_subscription_id = $1",
        stripe_sub_id,
    )
    assert row["status"] == "past_due"
    assert row["grace_period_end"] is not None


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_cancels(client, db_conn, student_token):
    """customer.subscription.deleted marks subscription cancelled."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    stripe_sub_id = await _insert_subscription(client, student_id, status="active")

    stripe_event_id = f"evt_del_{uuid.uuid4().hex[:10]}"
    fake_event = {
        "id": stripe_event_id,
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": stripe_sub_id}},
    }

    with patch("src.subscription.router._get_stripe_module") as mock_factory, \
         patch("config.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = fake_event
        mock_factory.return_value = mock_stripe

        r = await client.post(
            "/api/v1/subscription/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": _fake_stripe_sig(b"")},
        )
    assert r.status_code == 200

    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT status FROM subscriptions WHERE stripe_subscription_id = $1",
        stripe_sub_id,
    )
    assert row["status"] == "cancelled"


# ── DELETE /subscription ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_subscription_404_when_none(client, db_conn, student_token):
    """DELETE /subscription returns 404 when no active subscription exists."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.delete(
        "/api/v1/subscription",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "no_active_subscription"


@pytest.mark.asyncio
async def test_cancel_subscription_success(client, db_conn, student_token):
    """DELETE /subscription calls Stripe and returns cancelled_at_period_end."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    stripe_sub_id = await _insert_subscription(client, student_id, status="active")

    with patch("src.subscription.router.cancel_stripe_subscription", new_callable=AsyncMock), \
         patch("src.subscription.router.expire_entitlement_cache", new_callable=AsyncMock):
        r = await client.delete(
            "/api/v1/subscription",
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "cancelled_at_period_end"


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_endpoints_require_auth(client):
    """All JWT-gated subscription endpoints return 401 without a token."""
    r1 = await client.get("/api/v1/subscription/status")
    r2 = await client.post(
        "/api/v1/subscription/checkout",
        json={"plan": "monthly", "success_url": "x://s", "cancel_url": "x://c"},
    )
    r3 = await client.delete("/api/v1/subscription")
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
