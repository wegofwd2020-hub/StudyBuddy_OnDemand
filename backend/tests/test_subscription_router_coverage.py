"""
tests/test_subscription_router_coverage.py

Targeted coverage of src/subscription/router.py — PR #10 of #261.

Focuses on the pure dispatch helpers that don't need a real webhook
signature round-trip:

  - _map_stripe_status               — L228-238 (all 6 mapping branches + default)
  - _dispatch_event                  — routing to student_connect /
                                        teacher / school handlers
  - _dispatch_teacher_checkout       — missing-metadata warning + happy path
  - _dispatch_teacher_lifecycle      — updated / deleted / payment_failed
  - _dispatch_school_event (partial) — curriculum_renewal + storage_addon
                                        missing / invalid metadata branches
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ── _map_stripe_status ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("stripe_status", "expected"),
    [
        ("active", "active"),
        ("past_due", "past_due"),
        ("canceled", "cancelled"),
        ("cancelled", "cancelled"),
        ("unpaid", "past_due"),
        ("trialing", "active"),
        ("unknown_status", "active"),  # default branch
    ],
)
def test_map_stripe_status(stripe_status, expected):
    from src.subscription.router import _map_stripe_status

    assert _map_stripe_status(stripe_status) == expected


# ── _dispatch_event routing ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_event_routes_student_connect_checkout():
    """product_type=student_connect_subscription → student-connect checkout handler."""
    from src.subscription.router import _dispatch_event

    obj = {"metadata": {"product_type": "student_connect_subscription"}}
    conn = AsyncMock()
    redis = AsyncMock()

    with patch(
        "src.subscription.router._dispatch_student_connect_checkout",
        new_callable=AsyncMock,
    ) as mock_student_checkout:
        await _dispatch_event(conn, redis, "checkout.session.completed", obj)

    mock_student_checkout.assert_awaited_once_with(conn, obj, obj["metadata"])


@pytest.mark.asyncio
async def test_dispatch_event_routes_teacher_checkout():
    from src.subscription.router import _dispatch_event

    obj = {"metadata": {"product_type": "teacher_subscription"}}
    conn = AsyncMock()
    redis = AsyncMock()

    with patch(
        "src.subscription.router._dispatch_teacher_checkout", new_callable=AsyncMock
    ) as mock_teacher_checkout:
        await _dispatch_event(conn, redis, "checkout.session.completed", obj)

    mock_teacher_checkout.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_event_lifecycle_routes_to_student_connect():
    """customer.subscription.updated with a matching Connect sub → Option B lifecycle."""
    from src.subscription.router import _dispatch_event

    obj = {"id": "sub_connect_1", "metadata": {}}
    conn = AsyncMock()
    redis = AsyncMock()

    with (
        patch(
            "src.teacher.connect_service.find_teacher_by_student_subscription",
            new_callable=AsyncMock,
            return_value="teacher-xyz",
        ),
        patch(
            "src.subscription.router._dispatch_student_connect_lifecycle",
            new_callable=AsyncMock,
        ) as mock_lifecycle,
    ):
        await _dispatch_event(conn, redis, "customer.subscription.updated", obj)

    mock_lifecycle.assert_awaited_once_with(conn, "customer.subscription.updated", obj, "sub_connect_1")


@pytest.mark.asyncio
async def test_dispatch_event_lifecycle_routes_to_teacher_subscription():
    """customer.subscription.updated with a Connect miss but teacher-sub hit → Option A."""
    from src.subscription.router import _dispatch_event

    obj = {"id": "sub_flat_1", "metadata": {}}
    conn = AsyncMock()
    redis = AsyncMock()

    with (
        patch(
            "src.teacher.connect_service.find_teacher_by_student_subscription",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "src.teacher.subscription_service.find_teacher_by_stripe_subscription",
            new_callable=AsyncMock,
            return_value="teacher-flat",
        ),
        patch(
            "src.subscription.router._dispatch_teacher_lifecycle", new_callable=AsyncMock
        ) as mock_teacher_lifecycle,
    ):
        await _dispatch_event(conn, redis, "customer.subscription.updated", obj)

    mock_teacher_lifecycle.assert_awaited_once_with(
        conn, "customer.subscription.updated", obj, "sub_flat_1"
    )


@pytest.mark.asyncio
async def test_dispatch_event_falls_through_to_school_event():
    """No product_type match, no teacher match → school event handler."""
    from src.subscription.router import _dispatch_event

    obj = {"id": "sub_other", "metadata": {}}
    conn = AsyncMock()
    redis = AsyncMock()

    with (
        patch(
            "src.teacher.connect_service.find_teacher_by_student_subscription",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "src.teacher.subscription_service.find_teacher_by_stripe_subscription",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "src.subscription.router._dispatch_school_event", new_callable=AsyncMock
        ) as mock_school,
    ):
        await _dispatch_event(conn, redis, "customer.subscription.updated", obj)

    mock_school.assert_awaited_once()


# ── _dispatch_teacher_checkout ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_teacher_checkout_missing_metadata_warns_and_returns():
    """Missing teacher_id or plan → warning log, no downstream call."""
    from src.subscription.router import _dispatch_teacher_checkout

    conn = AsyncMock()

    with patch(
        "src.teacher.subscription_service.handle_teacher_subscription_activated",
        new_callable=AsyncMock,
    ) as mock_activate:
        await _dispatch_teacher_checkout(conn, obj={"customer": "cus_1"}, metadata={})

    mock_activate.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_teacher_checkout_fetches_period_end_and_activates():
    """Happy path — fetches stripe subscription period_end + calls activator."""
    from src.subscription.router import _dispatch_teacher_checkout

    conn = AsyncMock()
    obj = {"customer": "cus_1", "subscription": "sub_1"}
    metadata = {"teacher_id": "tea-1", "plan": "pro"}

    stripe_sub = {"current_period_end": 1776816000}  # unix ts
    stripe_mod = AsyncMock()
    stripe_mod.Subscription.retrieve = AsyncMock(return_value=stripe_sub)

    with (
        patch("src.subscription.router._get_stripe_module", return_value=stripe_mod),
        patch("src.subscription.router.run_stripe", new_callable=AsyncMock, return_value=stripe_sub),
        patch(
            "src.teacher.subscription_service.handle_teacher_subscription_activated",
            new_callable=AsyncMock,
        ) as mock_activate,
    ):
        await _dispatch_teacher_checkout(conn, obj=obj, metadata=metadata)

    mock_activate.assert_awaited_once()
    kwargs = mock_activate.call_args.kwargs
    assert kwargs["teacher_id"] == "tea-1"
    assert kwargs["plan"] == "pro"


@pytest.mark.asyncio
async def test_dispatch_teacher_checkout_stripe_fetch_exception_still_activates():
    """Stripe retrieve fails → warning log, activate called with period_end=None."""
    from src.subscription.router import _dispatch_teacher_checkout

    conn = AsyncMock()
    obj = {"customer": "cus_1", "subscription": "sub_1"}
    metadata = {"teacher_id": "tea-1", "plan": "pro"}

    stripe_mod = AsyncMock()

    with (
        patch("src.subscription.router._get_stripe_module", return_value=stripe_mod),
        patch(
            "src.subscription.router.run_stripe",
            new_callable=AsyncMock,
            side_effect=RuntimeError("stripe down"),
        ),
        patch(
            "src.teacher.subscription_service.handle_teacher_subscription_activated",
            new_callable=AsyncMock,
        ) as mock_activate,
    ):
        await _dispatch_teacher_checkout(conn, obj=obj, metadata=metadata)

    mock_activate.assert_awaited_once()
    assert mock_activate.call_args.kwargs["current_period_end"] is None


# ── _dispatch_teacher_lifecycle ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_teacher_lifecycle_updated():
    from src.subscription.router import _dispatch_teacher_lifecycle

    conn = AsyncMock()
    obj = {"status": "active", "current_period_end": 1776816000}

    with patch(
        "src.teacher.subscription_service.handle_teacher_subscription_updated",
        new_callable=AsyncMock,
    ) as mock_updated:
        await _dispatch_teacher_lifecycle(conn, "customer.subscription.updated", obj, "sub_1")

    mock_updated.assert_awaited_once()
    # 4th positional arg is current_period_end datetime.
    assert mock_updated.call_args.args[3] is not None


@pytest.mark.asyncio
async def test_dispatch_teacher_lifecycle_deleted():
    from src.subscription.router import _dispatch_teacher_lifecycle

    conn = AsyncMock()
    with patch(
        "src.teacher.subscription_service.handle_teacher_subscription_deleted",
        new_callable=AsyncMock,
    ) as mock_deleted:
        await _dispatch_teacher_lifecycle(conn, "customer.subscription.deleted", {}, "sub_1")

    mock_deleted.assert_awaited_once_with(conn, "sub_1")


@pytest.mark.asyncio
async def test_dispatch_teacher_lifecycle_payment_failed():
    from src.subscription.router import _dispatch_teacher_lifecycle

    conn = AsyncMock()
    with patch(
        "src.teacher.subscription_service.handle_teacher_payment_failed",
        new_callable=AsyncMock,
    ) as mock_failed:
        await _dispatch_teacher_lifecycle(conn, "invoice.payment_failed", {}, "sub_1")

    mock_failed.assert_awaited_once_with(conn, "sub_1")


# ── _dispatch_school_event (curriculum_renewal / storage_addon branches) ────


@pytest.mark.asyncio
async def test_dispatch_school_event_curriculum_renewal_missing_metadata():
    """renewal checkout with missing school_id or curriculum_id → warn + return."""
    from src.subscription.router import _dispatch_school_event

    conn = AsyncMock()
    redis = AsyncMock()
    obj = {"metadata": {"product_type": "curriculum_renewal"}}  # no school_id/curriculum_id

    with patch(
        "src.school.subscription_service.handle_curriculum_renewal_payment",
        new_callable=AsyncMock,
    ) as mock_handle:
        await _dispatch_school_event(conn, redis, "checkout.session.completed", obj)

    mock_handle.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_school_event_curriculum_renewal_happy():
    from src.subscription.router import _dispatch_school_event

    conn = AsyncMock()
    redis = AsyncMock()
    obj = {
        "metadata": {
            "product_type": "curriculum_renewal",
            "school_id": "d3000000-0000-0000-0000-000000000099",
            "curriculum_id": "cur-42",
        }
    }

    with patch(
        "src.school.subscription_service.handle_curriculum_renewal_payment",
        new_callable=AsyncMock,
    ) as mock_handle:
        await _dispatch_school_event(conn, redis, "checkout.session.completed", obj)

    mock_handle.assert_awaited_once_with(
        conn, "d3000000-0000-0000-0000-000000000099", "cur-42"
    )


@pytest.mark.asyncio
async def test_dispatch_school_event_storage_addon_invalid_gb():
    """additional_gb that isn't an int → warn + return."""
    from src.subscription.router import _dispatch_school_event

    conn = AsyncMock()
    redis = AsyncMock()
    obj = {
        "metadata": {
            "product_type": "storage_addon",
            "school_id": "d3000000-0000-0000-0000-000000000099",
            "additional_gb": "not-a-number",
        }
    }

    with patch(
        "src.school.subscription_service.handle_storage_addon_payment",
        new_callable=AsyncMock,
    ) as mock_handle:
        await _dispatch_school_event(conn, redis, "checkout.session.completed", obj)

    mock_handle.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_school_event_storage_addon_zero_gb():
    from src.subscription.router import _dispatch_school_event

    conn = AsyncMock()
    redis = AsyncMock()
    obj = {
        "metadata": {
            "product_type": "storage_addon",
            "school_id": "d3000000-0000-0000-0000-000000000099",
            "additional_gb": "0",
        }
    }

    with patch(
        "src.school.subscription_service.handle_storage_addon_payment",
        new_callable=AsyncMock,
    ) as mock_handle:
        await _dispatch_school_event(conn, redis, "checkout.session.completed", obj)

    mock_handle.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_school_event_storage_addon_happy():
    from src.subscription.router import _dispatch_school_event

    conn = AsyncMock()
    redis = AsyncMock()
    obj = {
        "metadata": {
            "product_type": "storage_addon",
            "school_id": "d3000000-0000-0000-0000-000000000099",
            "additional_gb": "50",
        }
    }

    with patch(
        "src.school.subscription_service.handle_storage_addon_payment",
        new_callable=AsyncMock,
    ) as mock_handle:
        await _dispatch_school_event(conn, redis, "checkout.session.completed", obj)

    mock_handle.assert_awaited_once_with(
        conn, "d3000000-0000-0000-0000-000000000099", 50
    )
