"""
tests/test_stripe_webhook_hardening.py  — K-3 (Epic 6 Platform Hardening)

Stripe webhook edge cases not covered by test_school_subscription.py:

  WHK-01  Invalid signature → 400 invalid_signature
  WHK-02  Missing stripe-signature header → 400
  WHK-03  Retry storm: same event sent 3× — first processes, next two return already_processed
  WHK-04  Out-of-order: customer.subscription.deleted for unknown stripe_sub_id → 200, no crash
  WHK-05  Out-of-order: customer.subscription.updated for unknown stripe_sub_id → 200, no crash
  WHK-06  invoice.payment_failed for a known school subscription sets status=past_due
  WHK-07  Unknown event type is silently ignored → 200 ok
  WHK-08  Handler exception → Stripe still gets 200 (never retried) and event logged as 'error'
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Webhook Hardening School",
            "contact_email": f"wh-{uuid.uuid4().hex[:8]}@example.com",
            "country": "US",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _insert_subscription(
    client: AsyncClient,
    school_id: str,
    stripe_sub_id: str,
    status: str = "active",
) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO school_subscriptions
                (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
                 max_students, max_teachers, current_period_end)
            VALUES ($1, 'professional', $2, 'cus_wh_test', $3, 150, 10,
                    NOW() + INTERVAL '30 days')
            ON CONFLICT (school_id) DO UPDATE
                SET stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """,
            uuid.UUID(school_id),
            status,
            stripe_sub_id,
        )


def _make_stripe_mock(event: dict) -> MagicMock:
    """Return a mock stripe module whose Webhook.construct_event returns `event`."""
    m = MagicMock()
    m.Webhook.construct_event.return_value = event
    m.api_key = None
    return m


async def _post_webhook(client: AsyncClient, event: dict) -> object:
    """Post a webhook request with a patched stripe module and settings."""
    stripe_mock = _make_stripe_mock(event)
    with patch("src.subscription.router._get_stripe_module", return_value=stripe_mock):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            mock_settings.STRIPE_SECRET_KEY = "sk_test_xxx"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=dummy"},
            )
    return r


# ── WHK-01 — Invalid signature ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_whk01_invalid_signature_returns_400(client: AsyncClient):
    """construct_event raises → 400 with error=invalid_signature."""
    bad_stripe = MagicMock()
    bad_stripe.Webhook.construct_event.side_effect = Exception("Signature mismatch")

    with patch("src.subscription.router._get_stripe_module", return_value=bad_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b"tampered_payload",
                headers={"stripe-signature": "t=1,v1=bad_sig"},
            )

    assert r.status_code == 400
    assert r.json()["error"] == "invalid_signature"


# ── WHK-02 — Missing stripe-signature header ──────────────────────────────────


@pytest.mark.asyncio
async def test_whk02_missing_signature_header_returns_400(client: AsyncClient):
    """No stripe-signature header → construct_event raises → 400."""
    bad_stripe = MagicMock()
    bad_stripe.Webhook.construct_event.side_effect = Exception("No signature")

    with patch("src.subscription.router._get_stripe_module", return_value=bad_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            # Deliberately omit the stripe-signature header
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b"{}",
            )

    assert r.status_code == 400
    assert r.json()["error"] == "invalid_signature"


# ── WHK-03 — Retry storm: same event sent 3× ─────────────────────────────────


@pytest.mark.asyncio
async def test_whk03_retry_storm_only_first_delivery_processed(client: AsyncClient):
    """
    Stripe sends the same event 3 times (retry storm).
    The first delivery writes a stripe_events row (outcome='ok').
    The 2nd and 3rd deliveries hit the deduplication guard → already_processed.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]
    event_id = f"evt_storm_{uuid.uuid4().hex[:12]}"

    def _event() -> dict:
        return {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"school_id": school_id, "plan": "starter"},
                    "customer": "cus_storm_test",
                    "subscription": f"sub_storm_{uuid.uuid4().hex[:8]}",
                }
            },
        }

    stripe_mock = MagicMock()
    stripe_mock.Webhook.construct_event.side_effect = lambda *_: _event()
    stripe_mock.Subscription.retrieve.return_value = {"current_period_end": 9_999_999_999}
    stripe_mock.api_key = None

    async def _send():
        with patch("src.subscription.router._get_stripe_module", return_value=stripe_mock):
            with patch("config.settings") as ms:
                ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
                ms.STRIPE_SECRET_KEY = "sk_test_xxx"
                with patch("src.school.subscription_service.expire_school_entitlement_cache"):
                    return await client.post(
                        "/api/v1/subscription/webhook",
                        content=b"{}",
                        headers={"stripe-signature": "t=1,v1=dummy"},
                    )

    r1 = await _send()
    r2 = await _send()
    r3 = await _send()

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200

    # First call processed successfully
    assert r1.json()["status"] == "ok"
    # Subsequent calls deduplicated
    assert r2.json()["status"] == "already_processed"
    assert r3.json()["status"] == "already_processed"

    # Stripe events table has exactly one row for this event_id
    pool = client._transport.app.state.pool
    row_count = await pool.fetchval(
        "SELECT COUNT(*) FROM stripe_events WHERE stripe_event_id = $1", event_id
    )
    assert row_count == 1


# ── WHK-04 — Out-of-order: subscription.deleted for unknown sub_id ────────────


@pytest.mark.asyncio
async def test_whk04_subscription_deleted_unknown_sub_id_no_crash(client: AsyncClient):
    """
    customer.subscription.deleted for a stripe_subscription_id that doesn't
    exist in school_subscriptions should not crash — it's a no-op.
    Returns 200 ok.
    """
    unknown_sub_id = f"sub_unknown_{uuid.uuid4().hex[:12]}"
    event = {
        "id": f"evt_del_{uuid.uuid4().hex[:12]}",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": unknown_sub_id,
                "status": "canceled",
                "metadata": {},
            }
        },
    }

    r = await _post_webhook(client, event)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


# ── WHK-05 — Out-of-order: subscription.updated for unknown sub_id ────────────


@pytest.mark.asyncio
async def test_whk05_subscription_updated_unknown_sub_id_no_crash(client: AsyncClient):
    """
    customer.subscription.updated for a stripe_subscription_id that doesn't
    exist in either school_subscriptions or teacher_subscriptions is a no-op.
    Returns 200 ok.
    """
    unknown_sub_id = f"sub_new_{uuid.uuid4().hex[:12]}"
    event = {
        "id": f"evt_upd_{uuid.uuid4().hex[:12]}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": unknown_sub_id,
                "status": "active",
                "current_period_end": 9_999_999_999,
                "metadata": {},
            }
        },
    }

    r = await _post_webhook(client, event)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


# ── WHK-06 — invoice.payment_failed for a known school sets past_due ──────────


@pytest.mark.asyncio
async def test_whk06_invoice_payment_failed_sets_past_due(client: AsyncClient):
    """
    invoice.payment_failed for a known school subscription sets status → past_due.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]
    stripe_sub_id = f"sub_pf_{uuid.uuid4().hex[:12]}"
    await _insert_subscription(client, school_id, stripe_sub_id)

    event = {
        "id": f"evt_pf_{uuid.uuid4().hex[:12]}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": stripe_sub_id,
                "metadata": {},
            }
        },
    }

    with patch("src.school.subscription_service.expire_school_entitlement_cache"):
        r = await _post_webhook(client, event)

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    # Verify status was updated to past_due
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        row = await conn.fetchrow(
            "SELECT status FROM school_subscriptions WHERE school_id = $1",
            uuid.UUID(school_id),
        )
    assert row is not None
    assert row["status"] == "past_due"


# ── WHK-07 — Unknown event type is silently ignored ───────────────────────────


@pytest.mark.asyncio
async def test_whk07_unknown_event_type_ignored_returns_200(client: AsyncClient):
    """
    An event type the handler doesn't recognise (e.g., balance.available) is
    dispatched but produces no database effect. Returns 200 ok.
    """
    event = {
        "id": f"evt_unk_{uuid.uuid4().hex[:12]}",
        "type": "balance.available",
        "data": {"object": {"object": "balance"}},
    }

    r = await _post_webhook(client, event)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


# ── WHK-08 — Handler exception → always acknowledge Stripe ───────────────────


@pytest.mark.asyncio
async def test_whk08_handler_exception_still_returns_200(client: AsyncClient):
    """
    If _dispatch_event raises an unexpected exception (e.g., DB constraint
    violation), the webhook must still return 200 so Stripe stops retrying.
    The stripe_events row records outcome='error'.
    """
    event_id = f"evt_exc_{uuid.uuid4().hex[:12]}"
    event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"school_id": str(uuid.uuid4()), "plan": "starter"},
                "customer": "cus_exc_test",
                "subscription": "sub_exc_test",
            }
        },
    }

    stripe_mock = _make_stripe_mock(event)

    # Force _dispatch_event to raise after signature verification succeeds
    with patch("src.subscription.router._get_stripe_module", return_value=stripe_mock):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            mock_settings.STRIPE_SECRET_KEY = "sk_test_xxx"
            with patch(
                "src.subscription.router._dispatch_event",
                new_callable=AsyncMock,
                side_effect=RuntimeError("simulated handler crash"),
            ):
                r = await client.post(
                    "/api/v1/subscription/webhook",
                    content=b"{}",
                    headers={"stripe-signature": "t=1,v1=dummy"},
                )

    # Stripe must receive 200 even on handler crash
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    # stripe_events row should record outcome='error'
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT outcome, error_detail FROM stripe_events WHERE stripe_event_id = $1",
        event_id,
    )
    assert row is not None, "stripe_events row was not written on handler crash"
    assert row["outcome"] == "error"
    assert "simulated handler crash" in (row["error_detail"] or "")
