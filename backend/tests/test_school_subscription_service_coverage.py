"""
tests/test_school_subscription_service_coverage.py

Targeted coverage of src/school/subscription_service.py — PR #11 of #261.

The bucket is biggest-gap (67.2% vs required 90%). This file focuses on
pure helpers + small webhook handlers with AsyncMock conn / redis, no
live Stripe and no FastAPI stack:

  - _stripe_key                          (happy / missing)
  - _storage_price_id                    (5 / 10 / 25 / invalid raises)
  - _credits_price_id                    (3 / 10 / 25 / invalid raises)
  - expire_school_entitlement_cache      (happy + dispatch exception swallowed)
  - _bulk_update_enrolled_student_entitlements (empty noop / upserts per row)
  - create_school_checkout_session       (happy + unknown plan raises)
  - create_renewal_checkout_session      (happy + missing price_id raises)
  - create_storage_checkout_session      (happy)
  - create_extra_build_checkout_session  (happy + missing price_id raises)
  - create_credits_bundle_checkout_session (happy + invalid bundle raises)
  - cancel_school_stripe_subscription    (cancel_at_period_end=True)
  - handle_curriculum_renewal_payment    (not found / already purged / happy)
  - handle_storage_addon_payment         (UPDATE 0 warn / applied)
  - handle_extra_build_payment           (UPDATE 0 warn / applied)
  - handle_credits_bundle_payment        (UPDATE 0 warn / applied)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── _stripe_key ───────────────────────────────────────────────────────────────


def test_stripe_key_returns_configured_value():
    """_stripe_key does `from config import settings` inside the function —
    patch config.settings directly (the module attr, not an import in the
    service module)."""
    from src.school.subscription_service import _stripe_key

    with patch("config.settings.STRIPE_SECRET_KEY", "sk_test_abc"):
        assert _stripe_key() == "sk_test_abc"


def test_stripe_key_raises_when_not_configured():
    from src.school.subscription_service import _stripe_key

    with patch("config.settings.STRIPE_SECRET_KEY", None):
        with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured"):
            _stripe_key()


# ── _storage_price_id / _credits_price_id ────────────────────────────────────


@pytest.mark.parametrize(
    ("gb", "env_attr"),
    [
        (5, "STRIPE_SCHOOL_PRICE_STORAGE_5GB_ID"),
        (10, "STRIPE_SCHOOL_PRICE_STORAGE_10GB_ID"),
        (25, "STRIPE_SCHOOL_PRICE_STORAGE_25GB_ID"),
    ],
)
def test_storage_price_id_returns_configured_id(gb, env_attr):
    from src.school.subscription_service import _storage_price_id

    with patch(f"config.settings.{env_attr}", f"price_storage_{gb}gb"):
        assert _storage_price_id(gb) == f"price_storage_{gb}gb"


def test_storage_price_id_unknown_gb_raises():
    from src.school.subscription_service import _storage_price_id

    with pytest.raises(RuntimeError, match="STRIPE_SCHOOL_PRICE_STORAGE_100GB_ID"):
        _storage_price_id(100)


@pytest.mark.parametrize(
    ("bundle_size", "env_attr"),
    [
        (3, "STRIPE_SCHOOL_PRICE_CREDITS_3_ID"),
        (10, "STRIPE_SCHOOL_PRICE_CREDITS_10_ID"),
        (25, "STRIPE_SCHOOL_PRICE_CREDITS_25_ID"),
    ],
)
def test_credits_price_id_returns_configured_id(bundle_size, env_attr):
    from src.school.subscription_service import _credits_price_id

    with patch(f"config.settings.{env_attr}", f"price_credits_{bundle_size}"):
        assert _credits_price_id(bundle_size) == f"price_credits_{bundle_size}"


def test_credits_price_id_unknown_bundle_raises():
    from src.school.subscription_service import _credits_price_id

    with pytest.raises(RuntimeError, match="STRIPE_SCHOOL_PRICE_CREDITS_99_ID"):
        _credits_price_id(99)


# ── expire_school_entitlement_cache ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_expire_school_entitlement_cache_deletes_and_dispatches_task():
    from src.school.subscription_service import expire_school_entitlement_cache

    school_id = str(uuid.uuid4())
    redis = AsyncMock()

    with patch(
        "src.auth.tasks.invalidate_school_entitlement_cache_task.delay"
    ) as mock_delay:
        await expire_school_entitlement_cache(redis, school_id)

    redis.delete.assert_awaited_once()
    mock_delay.assert_called_once_with(school_id)


@pytest.mark.asyncio
async def test_expire_school_entitlement_cache_swallows_task_dispatch_error():
    """Celery broker unreachable → logged warning, no raise."""
    from src.school.subscription_service import expire_school_entitlement_cache

    redis = AsyncMock()

    with patch(
        "src.auth.tasks.invalidate_school_entitlement_cache_task.delay",
        side_effect=RuntimeError("broker down"),
    ):
        # Must not raise.
        await expire_school_entitlement_cache(redis, str(uuid.uuid4()))


# ── _bulk_update_enrolled_student_entitlements ───────────────────────────────


@pytest.mark.asyncio
async def test_bulk_update_entitlements_noop_when_no_enrolments():
    from src.school.subscription_service import _bulk_update_enrolled_student_entitlements

    conn = AsyncMock()
    conn.fetch.return_value = []

    await _bulk_update_enrolled_student_entitlements(
        conn, str(uuid.uuid4()), "basic", None
    )

    # Only the SELECT — no INSERTs.
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_update_entitlements_upserts_each_student():
    from src.school.subscription_service import _bulk_update_enrolled_student_entitlements

    conn = AsyncMock()
    conn.fetch.return_value = [
        {"student_id": "student-1"},
        {"student_id": "student-2"},
        {"student_id": "student-3"},
    ]

    await _bulk_update_enrolled_student_entitlements(
        conn, str(uuid.uuid4()), "premium", None
    )

    # One INSERT ... ON CONFLICT per enrolled student.
    assert conn.execute.await_count == 3


# ── create_school_checkout_session ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_school_checkout_session_returns_stripe_url():
    from src.school.subscription_service import create_school_checkout_session

    stripe_mod = MagicMock()

    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch(
            "config.settings.STRIPE_SCHOOL_PRICE_STARTER_ID",
            "price_starter",
        ),
        patch(
            "src.school.subscription_service.run_stripe",
            new_callable=AsyncMock,
            return_value=MagicMock(url="https://checkout.stripe.com/starter"),
        ),
    ):
        url = await create_school_checkout_session(
            str(uuid.uuid4()), "starter", "https://app/s", "https://app/c"
        )

    assert url == "https://checkout.stripe.com/starter"


@pytest.mark.asyncio
async def test_create_school_checkout_session_unknown_plan_raises():
    from src.school.subscription_service import create_school_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
    ):
        with pytest.raises(RuntimeError, match="STRIPE_SCHOOL_PRICE_ULTRA_ID"):
            await create_school_checkout_session(
                str(uuid.uuid4()), "ultra", "https://s", "https://c"
            )


# ── create_renewal_checkout_session ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_renewal_checkout_session_happy():
    from src.school.subscription_service import create_renewal_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_RENEWAL_ID", "price_renewal"),
        patch(
            "src.school.subscription_service.run_stripe",
            new_callable=AsyncMock,
            return_value=MagicMock(url="https://checkout.stripe.com/renewal"),
        ),
    ):
        url = await create_renewal_checkout_session(
            str(uuid.uuid4()), "cur-1", 8, "https://s", "https://c"
        )

    assert url == "https://checkout.stripe.com/renewal"


@pytest.mark.asyncio
async def test_create_renewal_checkout_session_missing_price_raises():
    from src.school.subscription_service import create_renewal_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_RENEWAL_ID", None),
    ):
        with pytest.raises(RuntimeError, match="STRIPE_SCHOOL_PRICE_RENEWAL_ID"):
            await create_renewal_checkout_session(
                str(uuid.uuid4()), "cur-1", 8, "https://s", "https://c"
            )


# ── create_storage_checkout_session ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_storage_checkout_session_happy():
    from src.school.subscription_service import create_storage_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_STORAGE_10GB_ID", "price_10gb"),
        patch(
            "src.school.subscription_service.run_stripe",
            new_callable=AsyncMock,
            return_value=MagicMock(url="https://checkout.stripe.com/storage"),
        ),
    ):
        url = await create_storage_checkout_session(
            str(uuid.uuid4()), 10, "https://s", "https://c"
        )

    assert url == "https://checkout.stripe.com/storage"


# ── create_extra_build_checkout_session ───────────────────────────────────────


@pytest.mark.asyncio
async def test_create_extra_build_checkout_session_happy():
    from src.school.subscription_service import create_extra_build_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_EXTRA_BUILD_ID", "price_extra"),
        patch(
            "src.school.subscription_service.run_stripe",
            new_callable=AsyncMock,
            return_value=MagicMock(url="https://checkout.stripe.com/extra"),
        ),
    ):
        url = await create_extra_build_checkout_session(
            str(uuid.uuid4()), "https://s", "https://c"
        )

    assert url == "https://checkout.stripe.com/extra"


@pytest.mark.asyncio
async def test_create_extra_build_checkout_session_missing_price_raises():
    from src.school.subscription_service import create_extra_build_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_EXTRA_BUILD_ID", None),
    ):
        with pytest.raises(RuntimeError, match="STRIPE_SCHOOL_PRICE_EXTRA_BUILD_ID"):
            await create_extra_build_checkout_session(
                str(uuid.uuid4()), "https://s", "https://c"
            )


# ── create_credits_bundle_checkout_session ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_credits_bundle_checkout_session_invalid_size_raises():
    """Bundle size outside VALID_CREDIT_BUNDLE_SIZES raises ValueError."""
    from src.school.subscription_service import create_credits_bundle_checkout_session

    with pytest.raises(ValueError, match="Invalid credit bundle size"):
        await create_credits_bundle_checkout_session(
            str(uuid.uuid4()), 99, "https://s", "https://c"
        )


@pytest.mark.asyncio
async def test_create_credits_bundle_checkout_session_happy():
    from src.school.subscription_service import create_credits_bundle_checkout_session

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch("config.settings.STRIPE_SCHOOL_PRICE_CREDITS_10_ID", "price_c10"),
        patch(
            "src.school.subscription_service.run_stripe",
            new_callable=AsyncMock,
            return_value=MagicMock(url="https://checkout.stripe.com/credits"),
        ),
    ):
        url = await create_credits_bundle_checkout_session(
            str(uuid.uuid4()), 10, "https://s", "https://c"
        )

    assert url == "https://checkout.stripe.com/credits"


# ── cancel_school_stripe_subscription ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_school_stripe_subscription_sets_cancel_at_period_end():
    from src.school.subscription_service import cancel_school_stripe_subscription

    stripe_mod = MagicMock()
    with (
        patch("src.school.subscription_service._get_stripe", return_value=stripe_mod),
        patch("src.school.subscription_service._stripe_key", return_value="sk_test"),
        patch(
            "src.school.subscription_service.run_stripe", new_callable=AsyncMock
        ) as mock_run,
    ):
        await cancel_school_stripe_subscription("sub_abc")

    mock_run.assert_awaited_once()
    # Args after `run_stripe(callable, ...)`.
    call_args = mock_run.call_args
    assert call_args.args[1] == "sub_abc"
    assert call_args.kwargs == {"cancel_at_period_end": True}


# ── handle_curriculum_renewal_payment ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_curriculum_renewal_payment_curriculum_not_found():
    from src.school.subscription_service import handle_curriculum_renewal_payment

    conn = AsyncMock()
    conn.fetchrow.return_value = None

    await handle_curriculum_renewal_payment(conn, str(uuid.uuid4()), "cur-1")
    # Only the SELECT; no UPDATE.
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_handle_curriculum_renewal_payment_already_purged_skipped():
    from src.school.subscription_service import handle_curriculum_renewal_payment

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "curriculum_id": "cur-1",
        "grade": 8,
        "retention_status": "purged",
    }

    await handle_curriculum_renewal_payment(conn, str(uuid.uuid4()), "cur-1")
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_handle_curriculum_renewal_payment_renews():
    from src.school.subscription_service import handle_curriculum_renewal_payment

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "curriculum_id": "cur-1",
        "grade": 8,
        "retention_status": "active",
    }

    await handle_curriculum_renewal_payment(conn, str(uuid.uuid4()), "cur-1")

    conn.execute.assert_awaited_once()
    assert "UPDATE curricula" in conn.execute.call_args.args[0]


# ── handle_storage_addon_payment ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_storage_addon_payment_no_quota_row_warns():
    from src.school.subscription_service import handle_storage_addon_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 0"

    # Must not raise — warning only.
    await handle_storage_addon_payment(conn, str(uuid.uuid4()), 10)


@pytest.mark.asyncio
async def test_handle_storage_addon_payment_applies_increment():
    from src.school.subscription_service import handle_storage_addon_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 1"

    await handle_storage_addon_payment(conn, str(uuid.uuid4()), 25)

    assert "purchased_gb = purchased_gb + $1" in conn.execute.call_args.args[0]
    assert conn.execute.call_args.args[1] == 25


# ── handle_extra_build_payment ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_extra_build_payment_no_quota_row_warns():
    from src.school.subscription_service import handle_extra_build_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 0"

    await handle_extra_build_payment(conn, str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_handle_extra_build_payment_applies_one_credit():
    from src.school.subscription_service import handle_extra_build_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 1"

    await handle_extra_build_payment(conn, str(uuid.uuid4()))

    assert "builds_credits_balance = builds_credits_balance + 1" in conn.execute.call_args.args[0]


# ── handle_credits_bundle_payment ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_credits_bundle_payment_no_quota_row_warns():
    from src.school.subscription_service import handle_credits_bundle_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 0"

    await handle_credits_bundle_payment(conn, str(uuid.uuid4()), 10)


@pytest.mark.asyncio
async def test_handle_credits_bundle_payment_applies_credits():
    from src.school.subscription_service import handle_credits_bundle_payment

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 1"

    await handle_credits_bundle_payment(conn, str(uuid.uuid4()), 25)

    assert "builds_credits_balance = builds_credits_balance + $1" in conn.execute.call_args.args[0]
    assert conn.execute.call_args.args[1] == 25
