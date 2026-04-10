"""
tests/test_payment_action_required.py

Integration tests for the invoice.payment_action_required webhook handler (#117).

Covers:
  - Happy path: known school → Celery email task dispatched, audit log written
  - Missing subscription field in invoice → silent skip, no task dispatched
  - Unknown stripe_subscription_id → silent skip, no task dispatched
  - Idempotency: duplicate event_id → already_processed short-circuits
  - Bad Stripe signature → 400 (regression guard)
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


_WEBHOOK_SECRET = "whsec_test"


def _make_webhook_event(event_type: str, obj: dict, event_id: str | None = None) -> dict:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
        "type": event_type,
        "data": {"object": obj},
    }


def _stripe_mock(event: dict) -> MagicMock:
    mock = MagicMock()
    mock.Webhook.construct_event.return_value = event
    mock.api_key = None
    return mock


def _invoice_obj(
    stripe_subscription_id: str = "sub_test123",
    hosted_invoice_url: str = "https://invoice.stripe.com/i/test/3ds",
) -> dict:
    return {
        "subscription": stripe_subscription_id,
        "hosted_invoice_url": hosted_invoice_url,
    }


async def _pool_exec(client: AsyncClient, query: str, *args) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(query, *args)


async def _register_school(client: AsyncClient, contact_email: str | None = None) -> dict:
    """Register a school; return response dict augmented with the input contact_email."""
    email = contact_email or f"sca-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": "SCA Test School", "contact_email": email, "country": "DE"},
    )
    assert r.status_code == 201, r.text
    return {**r.json(), "contact_email": email}


async def _seed_school_subscription(
    client: AsyncClient,
    school_id: str,
    stripe_subscription_id: str,
) -> None:
    """Insert a minimal school_subscriptions row for webhook resolution."""
    await _pool_exec(
        client,
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, stripe_customer_id, stripe_subscription_id)
        VALUES ($1::uuid, 'starter', 'active', $2, $3)
        ON CONFLICT (school_id) DO UPDATE
            SET stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                stripe_customer_id     = EXCLUDED.stripe_customer_id
        """,
        school_id,
        f"cus_{uuid.uuid4().hex[:12]}",
        stripe_subscription_id,
    )


async def _post_webhook(client: AsyncClient) -> "httpx.Response":
    return await client.post(
        "/api/v1/subscription/webhook",
        content=b"payload",
        headers={"stripe-signature": "sig_test", "content-type": "application/json"},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_payment_action_required_dispatches_email(client: AsyncClient):
    """
    Happy path: known school with matching stripe_subscription_id receives
    a Celery email task dispatch and an audit log entry.
    """
    stripe_sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    action_url = "https://invoice.stripe.com/i/test_3ds_action"

    reg = await _register_school(client)
    school_id = reg["school_id"]
    contact_email = reg["contact_email"]
    await _seed_school_subscription(client, school_id, stripe_sub_id)

    event = _make_webhook_event(
        "invoice.payment_action_required",
        _invoice_obj(stripe_subscription_id=stripe_sub_id, hosted_invoice_url=action_url),
    )

    with (
        patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(event)),
        patch("src.auth.tasks.send_payment_action_required_email_task") as mock_task,
        patch("src.subscription.router.write_audit_log") as mock_audit,
        patch("config.settings") as mock_cfg,
    ):
        mock_cfg.STRIPE_WEBHOOK_SECRET = _WEBHOOK_SECRET
        r = await _post_webhook(client)

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    mock_task.delay.assert_called_once_with(
        to_email=contact_email,
        action_url=action_url,
    )
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["event_type"] == "payment_action_required"
    assert kw["actor_type"] == "stripe"
    assert kw["target_type"] == "school"


@pytest.mark.asyncio
async def test_payment_action_required_missing_subscription_id(client: AsyncClient):
    """Invoice object with no 'subscription' field → silent skip, no email dispatched."""
    event = _make_webhook_event(
        "invoice.payment_action_required",
        {"hosted_invoice_url": "https://invoice.stripe.com/i/test"},
    )

    with (
        patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(event)),
        patch("src.auth.tasks.send_payment_action_required_email_task") as mock_task,
        patch("config.settings") as mock_cfg,
    ):
        mock_cfg.STRIPE_WEBHOOK_SECRET = _WEBHOOK_SECRET
        r = await _post_webhook(client)

    assert r.status_code == 200
    mock_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_payment_action_required_unknown_subscription(client: AsyncClient):
    """stripe_subscription_id not in school_subscriptions → silent skip."""
    event = _make_webhook_event(
        "invoice.payment_action_required",
        _invoice_obj(stripe_subscription_id="sub_nobody_knows_me"),
    )

    with (
        patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(event)),
        patch("src.auth.tasks.send_payment_action_required_email_task") as mock_task,
        patch("config.settings") as mock_cfg,
    ):
        mock_cfg.STRIPE_WEBHOOK_SECRET = _WEBHOOK_SECRET
        r = await _post_webhook(client)

    assert r.status_code == 200
    mock_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_payment_action_required_idempotent(client: AsyncClient):
    """Duplicate stripe_event_id → already_processed short-circuits, handler not called."""
    stripe_sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    event_id = f"evt_{uuid.uuid4().hex[:12]}"

    reg = await _register_school(client)
    await _seed_school_subscription(client, reg["school_id"], stripe_sub_id)

    # Seed the event as already processed.
    await _pool_exec(
        client,
        "INSERT INTO stripe_events (stripe_event_id, event_type, outcome) "
        "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        event_id,
        "invoice.payment_action_required",
        "ok",
    )

    event = _make_webhook_event(
        "invoice.payment_action_required",
        _invoice_obj(stripe_subscription_id=stripe_sub_id),
        event_id=event_id,
    )

    with (
        patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(event)),
        patch("src.auth.tasks.send_payment_action_required_email_task") as mock_task,
        patch("config.settings") as mock_cfg,
    ):
        mock_cfg.STRIPE_WEBHOOK_SECRET = _WEBHOOK_SECRET
        r = await _post_webhook(client)

    assert r.status_code == 200
    assert r.json()["status"] == "already_processed"
    mock_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_stripe_signature_returns_400(client: AsyncClient):
    """Bad Stripe-Signature header → 400 (regression guard for signature verification)."""
    with (
        patch("src.subscription.router._get_stripe_module") as mock_get_stripe,
        patch("config.settings") as mock_cfg,
    ):
        mock_cfg.STRIPE_WEBHOOK_SECRET = _WEBHOOK_SECRET
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.side_effect = Exception("bad signature")
        mock_get_stripe.return_value = mock_stripe

        r = await client.post(
            "/api/v1/subscription/webhook",
            content=b"payload",
            headers={"stripe-signature": "bad_sig", "content-type": "application/json"},
        )

    assert r.status_code == 400
    assert r.json()["error"] == "invalid_signature"
