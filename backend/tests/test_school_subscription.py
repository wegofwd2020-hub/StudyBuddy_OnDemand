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
    """Insert a school_subscriptions row directly via the pool.

    Sets app.current_school_id = 'bypass' to satisfy the FORCE ROW LEVEL
    SECURITY policy on school_subscriptions (migration 0028).
    """
    sub_id = stripe_sub_id or f"sub_school_{uuid.uuid4().hex[:12]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
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
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        row = await conn.fetchrow(
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


# ── Build allowance (Option A) ────────────────────────────────────────────────


async def _insert_quota_row(
    client: AsyncClient,
    school_id: str,
    builds_included: int = 3,
    builds_used: int = 0,
    builds_period_end_days: int = 365,
) -> None:
    """Insert a school_storage_quotas row with build allowance columns set.

    Sets app.current_school_id = 'bypass' to satisfy the FORCE ROW LEVEL
    SECURITY policy on school_storage_quotas (migration 0029).
    """
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_storage_quotas
                (school_id, builds_included, builds_used, builds_period_end)
            VALUES ($1, $2, $3, NOW() + ($4 || ' days')::INTERVAL)
            ON CONFLICT (school_id) DO UPDATE SET
                builds_included   = EXCLUDED.builds_included,
                builds_used       = EXCLUDED.builds_used,
                builds_period_end = EXCLUDED.builds_period_end,
                updated_at        = NOW()
            """,
            uuid.UUID(school_id),
            builds_included,
            builds_used,
            str(builds_period_end_days),
        )


@pytest.mark.asyncio
async def test_check_build_allowance_no_quota_row(client: AsyncClient):
    """Returns allowed=False with 0 allowance when no quota row exists."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    pool = client._transport.app.state.pool

    async with pool.acquire() as conn:
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is False
    assert result["builds_included"] == 0
    assert result["builds_used"] == 0
    assert result["builds_remaining"] == 0
    assert result["builds_period_end"] is None


@pytest.mark.asyncio
async def test_check_build_allowance_has_remaining(client: AsyncClient):
    """Returns allowed=True with correct remaining count when builds available."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row(client, school_id, builds_included=3, builds_used=1)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is True
    assert result["builds_included"] == 3
    assert result["builds_used"] == 1
    assert result["builds_remaining"] == 2
    assert result["builds_period_end"] is not None


@pytest.mark.asyncio
async def test_check_build_allowance_exhausted(client: AsyncClient):
    """Returns allowed=False when builds_used >= builds_included."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row(client, school_id, builds_included=1, builds_used=1)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is False
    assert result["builds_remaining"] == 0


@pytest.mark.asyncio
async def test_check_build_allowance_enterprise_unlimited(client: AsyncClient):
    """Enterprise plan (-1) reports allowed=True and builds_remaining=-1."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row(client, school_id, builds_included=-1, builds_used=99)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is True
    assert result["builds_included"] == -1
    assert result["builds_remaining"] == -1


@pytest.mark.asyncio
async def test_consume_build_increments_counter(client: AsyncClient):
    """consume_build increments builds_used by 1."""
    from src.school.subscription_service import check_build_allowance, consume_build

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row(client, school_id, builds_included=3, builds_used=0)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        await consume_build(conn, school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["builds_used"] == 1
    assert result["builds_remaining"] == 2


@pytest.mark.asyncio
async def test_stamp_build_allowance_resets_on_reactivation(client: AsyncClient):
    """_stamp_build_allowance resets builds_used=0 and sets builds_included from plan."""
    from src.school.subscription_service import _stamp_build_allowance, check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    # Start with used=2 (simulating mid-year)
    await _insert_quota_row(client, school_id, builds_included=3, builds_used=2)

    pool = client._transport.app.state.pool
    new_period_end = datetime.now(UTC) + timedelta(days=365)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        # Simulate reactivation on professional plan
        await _stamp_build_allowance(conn, school_id, "professional", new_period_end)
        result = await check_build_allowance(conn, school_id)

    assert result["builds_used"] == 0           # reset
    assert result["builds_included"] == 3       # professional = 3
    assert result["builds_remaining"] == 3
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_subscription_status_response_includes_builds_fields(client: AsyncClient):
    """GET /subscription response includes builds_included, builds_used, builds_remaining."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    await _insert_school_subscription(client, school_id, plan="professional")
    await _insert_quota_row(client, school_id, builds_included=3, builds_used=1)

    r = await client.get(
        f"/api/v1/schools/{school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert "builds_included" in data
    assert "builds_used" in data
    assert "builds_remaining" in data
    assert data["builds_included"] == 3
    assert data["builds_used"] == 1
    assert data["builds_remaining"] == 2


# ── Credit balance (#107) — check_build_allowance ────────────────────────────


async def _insert_quota_row_with_credits(
    client: AsyncClient,
    school_id: str,
    builds_included: int = 1,
    builds_used: int = 0,
    builds_credits_balance: int = 0,
) -> None:
    """Insert a quota row with a credit balance for testing.

    Sets app.current_school_id = 'bypass' so the FORCE ROW LEVEL SECURITY
    policy on school_storage_quotas permits the direct write.
    """
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_storage_quotas
                (school_id, builds_included, builds_used, builds_period_end,
                 builds_credits_balance)
            VALUES ($1, $2, $3, NOW() + INTERVAL '365 days', $4)
            ON CONFLICT (school_id) DO UPDATE SET
                builds_included        = EXCLUDED.builds_included,
                builds_used            = EXCLUDED.builds_used,
                builds_credits_balance = EXCLUDED.builds_credits_balance,
                builds_period_end      = EXCLUDED.builds_period_end,
                updated_at             = NOW()
            """,
            uuid.UUID(school_id),
            builds_included,
            builds_used,
            builds_credits_balance,
        )


@pytest.mark.asyncio
async def test_check_build_allowance_credits_enable_build_when_plan_exhausted(
    client: AsyncClient,
):
    """allowed=True when plan allowance=0 but credits>0."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    # Plan fully used, but 3 rollover credits available
    await _insert_quota_row_with_credits(
        client, school_id,
        builds_included=1, builds_used=1, builds_credits_balance=3,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is True
    assert result["builds_remaining"] == 0
    assert result["builds_credits_balance"] == 3


@pytest.mark.asyncio
async def test_check_build_allowance_no_plan_no_credits_blocked(client: AsyncClient):
    """allowed=False when plan allowance=0 and credits=0."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row_with_credits(
        client, school_id,
        builds_included=1, builds_used=1, builds_credits_balance=0,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["allowed"] is False
    assert result["builds_credits_balance"] == 0


# ── consume_build with credits (#107) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_build_deducts_credit_when_plan_exhausted(client: AsyncClient):
    """consume_build deducts from credits when plan allowance is 0."""
    from src.school.subscription_service import check_build_allowance, consume_build

    reg = await _register_school(client)
    school_id = reg["school_id"]
    # Plan exhausted, 5 credits available
    await _insert_quota_row_with_credits(
        client, school_id,
        builds_included=1, builds_used=1, builds_credits_balance=5,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        await consume_build(conn, school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["builds_used"] == 1           # plan counter unchanged
    assert result["builds_credits_balance"] == 4  # one credit deducted


@pytest.mark.asyncio
async def test_consume_build_uses_plan_first_before_credits(client: AsyncClient):
    """consume_build uses plan allowance, not credits, when plan has remaining."""
    from src.school.subscription_service import check_build_allowance, consume_build

    reg = await _register_school(client)
    school_id = reg["school_id"]
    # Plan has 1 remaining, 3 credits in reserve
    await _insert_quota_row_with_credits(
        client, school_id,
        builds_included=2, builds_used=1, builds_credits_balance=3,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        await consume_build(conn, school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["builds_used"] == 2           # plan counter incremented
    assert result["builds_credits_balance"] == 3  # credits untouched


# ── handle_extra_build_payment and handle_credits_bundle_payment ──────────────


@pytest.mark.asyncio
async def test_handle_extra_build_payment_increments_credits(client: AsyncClient):
    """handle_extra_build_payment adds 1 to builds_credits_balance."""
    from src.school.subscription_service import (
        check_build_allowance,
        handle_extra_build_payment,
    )

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row_with_credits(
        client, school_id, builds_included=1, builds_used=1, builds_credits_balance=0,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        await handle_extra_build_payment(conn, school_id)
        result = await check_build_allowance(conn, school_id)

    assert result["builds_credits_balance"] == 1
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_handle_credits_bundle_payment_adds_correct_count(client: AsyncClient):
    """handle_credits_bundle_payment increments balance by the bundle size."""
    from src.school.subscription_service import (
        check_build_allowance,
        handle_credits_bundle_payment,
    )

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row_with_credits(
        client, school_id, builds_included=1, builds_used=1, builds_credits_balance=2,
    )

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        await handle_credits_bundle_payment(conn, school_id, 10)  # buy 10-pack
        result = await check_build_allowance(conn, school_id)

    assert result["builds_credits_balance"] == 12  # 2 existing + 10 purchased


# ── Webhook routing — extra_build and build_credits product_types ─────────────


def _make_webhook_session(metadata: dict) -> dict:
    """Build a minimal checkout.session.completed Stripe object."""
    return {
        "id": f"cs_test_{uuid.uuid4().hex[:16]}",
        "object": "checkout.session",
        "customer": "cus_test_webhook",
        "subscription": None,
        "metadata": metadata,
    }


@pytest.mark.asyncio
async def test_webhook_extra_build_payment_applies_credit(client: AsyncClient):
    """Webhook with product_type=extra_build increments builds_credits_balance by 1."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row_with_credits(
        client, school_id, builds_included=1, builds_used=1, builds_credits_balance=0,
    )

    stripe_event_id = f"evt_extrabuild_{uuid.uuid4().hex[:12]}"
    session = _make_webhook_session({"school_id": school_id, "product_type": "extra_build", "credits": "1"})

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {
        "id": stripe_event_id,
        "type": "checkout.session.completed",
        "data": {"object": session},
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
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)
    assert result["builds_credits_balance"] == 1


@pytest.mark.asyncio
async def test_webhook_build_credits_payment_adds_bundle_count(client: AsyncClient):
    """Webhook with product_type=build_credits increments balance by the credits value."""
    from src.school.subscription_service import check_build_allowance

    reg = await _register_school(client)
    school_id = reg["school_id"]
    await _insert_quota_row_with_credits(
        client, school_id, builds_included=1, builds_used=1, builds_credits_balance=0,
    )

    stripe_event_id = f"evt_credits_{uuid.uuid4().hex[:12]}"
    session = _make_webhook_session({
        "school_id": school_id,
        "product_type": "build_credits",
        "credits": "10",
    })

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {
        "id": stripe_event_id,
        "type": "checkout.session.completed",
        "data": {"object": session},
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
        await conn.execute("SELECT set_config('app.current_school_id', $1, false)", school_id)
        result = await check_build_allowance(conn, school_id)
    assert result["builds_credits_balance"] == 10


# ── subscription status includes builds_credits_balance ─────────────────────


@pytest.mark.asyncio
async def test_subscription_status_includes_credits_balance(client: AsyncClient):
    """GET /subscription response includes builds_credits_balance in the payload.

    We test with an unsubscribed school that has a quota row with credits — the
    endpoint returns plan='none' but still surfaces the credit balance so the
    frontend can show it.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    # Insert quota row with 5 credits (no subscription row needed for this check)
    await _insert_quota_row_with_credits(
        client, school_id,
        builds_included=1, builds_used=0, builds_credits_balance=5,
    )

    r = await client.get(
        f"/api/v1/schools/{school_id}/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "builds_credits_balance" in data, "builds_credits_balance must be in subscription response"
    assert data["builds_credits_balance"] == 5
