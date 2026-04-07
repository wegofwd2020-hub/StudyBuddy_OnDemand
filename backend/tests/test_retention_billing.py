"""
tests/test_retention_billing.py

Integration tests for Phase G retention billing endpoints.

Endpoints under test:
  POST /api/v1/schools/{school_id}/curriculum/versions/{curriculum_id}/renewal-checkout
  POST /api/v1/schools/{school_id}/storage/checkout

Plus Stripe webhook routing for:
  checkout.session.completed with product_type='curriculum_renewal'
  checkout.session.completed with product_type='storage_addon'

All Stripe SDK calls are mocked — no live Stripe account needed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


# ── Test helpers ──────────────────────────────────────────────────────────────

_FAKE_CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_billing123"


async def _register_school(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Billing Test School",
        "contact_email": f"billing-{uuid.uuid4().hex[:8]}@example.com",
        "country": "US",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    token = make_teacher_token(
        teacher_id=body["teacher_id"],
        school_id=body["school_id"],
        role="school_admin",
    )
    return {**body, "token": token}


async def _seed_curriculum(
    client: AsyncClient,
    school_id: str,
    grade: int = 8,
    year: int = 2026,
    retention_status: str = "active",
    expires_at: datetime | None = None,
) -> str:
    """Insert a curriculum row directly via the app pool (RLS bypassed)."""
    curriculum_id = f"{school_id[:8]}-{year}-g{grade}-{uuid.uuid4().hex[:6]}"
    exp = expires_at or (datetime.now(UTC) + timedelta(days=365))

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type,
                 school_id, status, owner_type, owner_id, retention_status, expires_at)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid, 'active',
                    'school', $5::uuid, $6, $7)
            ON CONFLICT (curriculum_id) DO UPDATE
                SET retention_status = EXCLUDED.retention_status,
                    expires_at       = EXCLUDED.expires_at
            """,
            curriculum_id, grade, year, f"Grade {grade} Curriculum ({year})",
            school_id, retention_status, exp,
        )
    return curriculum_id


async def _pool_fetchval(client: AsyncClient, query: str, *args):
    """Run a scalar query against the pool with RLS bypassed."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        return await conn.fetchval(query, *args)


async def _pool_fetchrow(client: AsyncClient, query: str, *args):
    """Run a row query against the pool with RLS bypassed."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        return await conn.fetchrow(query, *args)


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


# ── POST .../renewal-checkout ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_renewal_checkout_returns_url(client: AsyncClient):
    """Happy path: returns a Stripe checkout URL for an active curriculum."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(client, school_id, grade=8)

    with patch(
        "src.school.subscription_router.create_renewal_checkout_session",
        return_value=_FAKE_CHECKOUT_URL,
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renewal-checkout",
            json={
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()["checkout_url"] == _FAKE_CHECKOUT_URL


@pytest.mark.asyncio
async def test_renewal_checkout_unavailable_curriculum(client: AsyncClient):
    """Unavailable curriculum (in grace period) can still be renewed via checkout."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(
        client, school_id, grade=9,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=5),
    )

    with patch(
        "src.school.subscription_router.create_renewal_checkout_session",
        return_value=_FAKE_CHECKOUT_URL,
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renewal-checkout",
            json={
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_renewal_checkout_purged_returns_409(client: AsyncClient):
    """Purged curriculum cannot be renewed — returns 409."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(client, school_id, grade=10, retention_status="purged")

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renewal-checkout",
        json={
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 409
    assert r.json()["error"] == "already_purged"


@pytest.mark.asyncio
async def test_renewal_checkout_missing_curriculum_returns_404(client: AsyncClient):
    """Non-existent curriculum returns 404."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/nonexistent/renewal-checkout",
        json={
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_renewal_checkout_stripe_not_configured_returns_503(client: AsyncClient):
    """Returns 503 when STRIPE_SCHOOL_PRICE_RENEWAL_ID is not set."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(client, school_id, grade=8)

    with patch(
        "src.school.subscription_router.create_renewal_checkout_session",
        side_effect=RuntimeError("STRIPE_SCHOOL_PRICE_RENEWAL_ID is not configured"),
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renewal-checkout",
            json={
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 503
    assert r.json()["error"] == "payment_unavailable"


@pytest.mark.asyncio
async def test_renewal_checkout_plain_teacher_returns_403(client: AsyncClient):
    """Plain teacher (not school_admin) cannot initiate renewal checkout."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    cid = await _seed_curriculum(client, school_id, grade=8)
    teacher_token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="teacher"
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renewal-checkout",
        json={
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_renewal_checkout_requires_auth(client: AsyncClient):
    r = await client.post(
        "/api/v1/schools/some-id/curriculum/versions/some-cid/renewal-checkout",
        json={"success_url": "https://x.com", "cancel_url": "https://x.com"},
    )
    assert r.status_code == 401


# ── POST .../storage/checkout ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_checkout_returns_url(client: AsyncClient):
    """Happy path: returns a Stripe checkout URL for 10 GB add-on."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    with patch(
        "src.school.subscription_router.create_storage_checkout_session",
        return_value=_FAKE_CHECKOUT_URL,
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/storage/checkout",
            json={
                "gb_package": 10,
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()["checkout_url"] == _FAKE_CHECKOUT_URL


@pytest.mark.asyncio
async def test_storage_checkout_invalid_package_returns_422(client: AsyncClient):
    """gb_package must be 5, 10, or 25 — other values return 422."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/storage/checkout",
        json={
            "gb_package": 7,
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_storage_checkout_stripe_not_configured_returns_503(client: AsyncClient):
    """Returns 503 when STRIPE_SCHOOL_PRICE_STORAGE_*_ID is not set."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    with patch(
        "src.school.subscription_router.create_storage_checkout_session",
        side_effect=RuntimeError("STRIPE_SCHOOL_PRICE_STORAGE_5GB_ID is not configured"),
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/storage/checkout",
            json={
                "gb_package": 5,
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 503
    assert r.json()["error"] == "payment_unavailable"


@pytest.mark.asyncio
async def test_storage_checkout_plain_teacher_returns_403(client: AsyncClient):
    """Plain teacher cannot purchase storage add-ons."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    teacher_token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="teacher"
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/storage/checkout",
        json={
            "gb_package": 10,
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_storage_checkout_requires_auth(client: AsyncClient):
    r = await client.post(
        "/api/v1/schools/some-id/storage/checkout",
        json={"gb_package": 10, "success_url": "https://x.com", "cancel_url": "https://x.com"},
    )
    assert r.status_code == 401


# ── Webhook: curriculum_renewal ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_renewal_activates_curriculum(client: AsyncClient):
    """
    checkout.session.completed with product_type='curriculum_renewal' renews
    the curriculum: sets retention_status='active', extends expires_at by 1 year.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    old_expires = datetime.now(UTC) - timedelta(days=5)
    cid = await _seed_curriculum(
        client, school_id, grade=8,
        retention_status="unavailable",
        expires_at=old_expires,
    )

    fake_event = _make_webhook_event(
        "checkout.session.completed",
        {
            "metadata": {
                "school_id": school_id,
                "curriculum_id": cid,
                "grade": "8",
                "product_type": "curriculum_renewal",
            },
        },
    )

    with patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(fake_event)):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b'{"type":"checkout.session.completed"}',
                headers={
                    "stripe-signature": "t=1,v1=dummy",
                    "content-type": "application/json",
                },
            )

    assert r.status_code == 200

    row = await _pool_fetchrow(
        client,
        "SELECT retention_status, expires_at, grace_until FROM curricula WHERE curriculum_id = $1",
        cid,
    )
    assert row["retention_status"] == "active"
    assert row["grace_until"] is None
    # new expires_at ≈ old_expires + 1 year (365–367 days)
    delta = (row["expires_at"] - old_expires).days
    assert 363 <= delta <= 367


@pytest.mark.asyncio
async def test_webhook_renewal_purged_curriculum_is_logged_not_raised(client: AsyncClient):
    """
    If the curriculum was purged before the webhook arrived, the handler logs
    a warning but returns 200 (does not raise) — payment requires manual refund.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    cid = await _seed_curriculum(client, school_id, grade=10, retention_status="purged")

    fake_event = _make_webhook_event(
        "checkout.session.completed",
        {
            "metadata": {
                "school_id": school_id,
                "curriculum_id": cid,
                "product_type": "curriculum_renewal",
            },
        },
    )

    with patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(fake_event)):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b'{"type":"checkout.session.completed"}',
                headers={
                    "stripe-signature": "t=1,v1=dummy",
                    "content-type": "application/json",
                },
            )

    assert r.status_code == 200

    row = await _pool_fetchrow(
        client,
        "SELECT retention_status FROM curricula WHERE curriculum_id = $1",
        cid,
    )
    # Status must remain 'purged' — the handler did not update it
    assert row["retention_status"] == "purged"


# ── Webhook: storage_addon ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_storage_addon_increments_purchased_gb(client: AsyncClient):
    """
    checkout.session.completed with product_type='storage_addon' increments
    school_storage_quotas.purchased_gb by the purchased amount.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    # Get baseline purchased_gb (should be 0 for a freshly registered school)
    before = await _pool_fetchval(
        client,
        "SELECT purchased_gb FROM school_storage_quotas WHERE school_id = $1::uuid",
        school_id,
    )
    assert before is not None

    fake_event = _make_webhook_event(
        "checkout.session.completed",
        {
            "metadata": {
                "school_id": school_id,
                "additional_gb": "10",
                "product_type": "storage_addon",
            },
        },
    )

    with patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(fake_event)):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b'{"type":"checkout.session.completed"}',
                headers={
                    "stripe-signature": "t=1,v1=dummy",
                    "content-type": "application/json",
                },
            )

    assert r.status_code == 200

    after = await _pool_fetchval(
        client,
        "SELECT purchased_gb FROM school_storage_quotas WHERE school_id = $1::uuid",
        school_id,
    )
    assert after == before + 10


@pytest.mark.asyncio
async def test_webhook_storage_addon_idempotent_via_dedup(client: AsyncClient):
    """
    A duplicated storage_addon webhook (same stripe_event_id) is silently
    skipped by already_processed() — purchased_gb is only incremented once.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    event_id = f"evt_storage_{uuid.uuid4().hex[:12]}"

    # Pre-insert the event as already processed (stripe_events has no RLS).
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            "INSERT INTO stripe_events (stripe_event_id, event_type, outcome) VALUES ($1, $2, 'ok')",
            event_id, "checkout.session.completed",
        )

    before = await _pool_fetchval(
        client,
        "SELECT purchased_gb FROM school_storage_quotas WHERE school_id = $1::uuid",
        school_id,
    )

    fake_event = _make_webhook_event(
        "checkout.session.completed",
        {
            "metadata": {
                "school_id": school_id,
                "additional_gb": "25",
                "product_type": "storage_addon",
            },
        },
        event_id=event_id,
    )

    with patch("src.subscription.router._get_stripe_module", return_value=_stripe_mock(fake_event)):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            r = await client.post(
                "/api/v1/subscription/webhook",
                content=b'{"type":"checkout.session.completed"}',
                headers={
                    "stripe-signature": "t=1,v1=dummy",
                    "content-type": "application/json",
                },
            )

    assert r.status_code == 200

    after = await _pool_fetchval(
        client,
        "SELECT purchased_gb FROM school_storage_quotas WHERE school_id = $1::uuid",
        school_id,
    )
    # No change — dedup prevented the second execution
    assert after == before


@pytest.mark.asyncio
async def test_webhook_existing_subscription_checkout_unaffected(client: AsyncClient):
    """
    Existing checkout.session.completed without product_type still routes to
    the school subscription activation handler.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    fake_event = _make_webhook_event(
        "checkout.session.completed",
        {
            "metadata": {"school_id": school_id, "plan": "starter"},
            "customer": "cus_test_routing",
            "subscription": "sub_test_routing",
        },
    )

    mock_stripe = _stripe_mock(fake_event)
    mock_stripe.Subscription.retrieve.return_value = {
        "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    }

    with patch("src.subscription.router._get_stripe_module", return_value=mock_stripe):
        with patch("config.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            mock_settings.STRIPE_SECRET_KEY = "sk_test_routing"
            with patch(
                "src.school.subscription_service.expire_school_entitlement_cache"
            ) as mock_expire:
                mock_expire.return_value = None
                r = await client.post(
                    "/api/v1/subscription/webhook",
                    content=b'{"type":"checkout.session.completed"}',
                    headers={
                        "stripe-signature": "t=1,v1=dummy",
                        "content-type": "application/json",
                    },
                )

    assert r.status_code == 200

    row = await _pool_fetchrow(
        client,
        "SELECT plan, status FROM school_subscriptions WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    assert row is not None
    assert row["plan"] == "starter"
    assert row["status"] == "active"
