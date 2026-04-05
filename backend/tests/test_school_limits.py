"""
tests/test_school_limits.py

Tests for school limits and override endpoints:
  GET  /schools/{school_id}/limits
  GET  /admin/schools/{school_id}/limits
  PUT  /admin/schools/{school_id}/limits
  DELETE /admin/schools/{school_id}/limits
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token, make_teacher_token

# ── Deterministic test IDs (Rule 9 — no uuid4 in fixtures) ───────────────────
_ADMIN_ID_01  = "e1000000-0000-0000-0000-000000000001"
_ADMIN_ID_02  = "e1000000-0000-0000-0000-000000000002"
_ADMIN_ID_03  = "e1000000-0000-0000-0000-000000000003"
_ADMIN_ID_04  = "e1000000-0000-0000-0000-000000000004"
_ADMIN_ID_05  = "e1000000-0000-0000-0000-000000000005"
_ADMIN_ID_06  = "e1000000-0000-0000-0000-000000000006"
_ADMIN_ID_07  = "e1000000-0000-0000-0000-000000000007"
_ADMIN_ID_08  = "e1000000-0000-0000-0000-000000000008"
_ADMIN_ID_09  = "e1000000-0000-0000-0000-000000000009"
_WRONG_SCHOOL = "ffff0000-0000-0000-0000-000000000002"  # never registered
_NOT_FOUND_SCHOOL = "ffff0000-0000-0000-0000-000000000003"  # for 404 checks
_FIXED_SUB_ID = "sub_fixedtestsubscription01"  # deterministic Stripe sub ID


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    """Register a school and return {school_id, teacher_id, access_token}."""
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Limits Test School",
        "contact_email": "limits-fixed@example.com",
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_admin(client: AsyncClient, admin_id: str, role: str = "super_admin") -> None:
    """Insert an admin_users row so FK constraints on set_by_admin_id pass."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, password_hash, role, account_status)
        VALUES ($1, $2, 'x', $3, 'active')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(admin_id),
        f"admin-{admin_id[:8]}@example.com",
        role,
    )


async def _insert_subscription(client: AsyncClient, school_id: str, plan: str = "professional") -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
             max_students, max_teachers, current_period_end)
        VALUES ($1, $2, 'active', 'cus_test', $3, 150, 10, NOW() + INTERVAL '30 days')
        ON CONFLICT (school_id) DO UPDATE SET plan = EXCLUDED.plan
        """,
        uuid.UUID(school_id),
        plan,
        _FIXED_SUB_ID,
    )


# ── GET /schools/{school_id}/limits ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_school_limits_no_subscription_returns_starter_defaults(client: AsyncClient):
    """Without a subscription, effective limits fall back to starter plan defaults."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "starter"
    assert data["max_students"] == 30    # SCHOOL_SEATS_STARTER_STUDENTS default
    assert data["max_teachers"] == 3     # SCHOOL_SEATS_STARTER_TEACHERS default
    assert data["pipeline_quota_monthly"] == 3  # SCHOOL_PIPELINE_QUOTA_STARTER default
    assert data["has_override"] is False
    assert "pipeline_resets_at" in data
    assert data["seats_used_teachers"] >= 1  # the school_admin teacher


@pytest.mark.asyncio
async def test_school_limits_with_professional_subscription(client: AsyncClient):
    """Limits reflect the professional plan when an active subscription exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")
    await _insert_subscription(client, school_id, plan="professional")

    r = await client.get(
        f"/api/v1/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "professional"
    assert data["max_students"] == 150
    assert data["max_teachers"] == 10
    assert data["pipeline_quota_monthly"] == 10


@pytest.mark.asyncio
async def test_school_limits_wrong_school_returns_403(client: AsyncClient):
    """Teacher cannot view limits for a different school."""
    reg = await _register_school(client)
    other_school_id = _WRONG_SCHOOL
    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin")

    r = await client.get(
        f"/api/v1/schools/{other_school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_limits_requires_auth(client: AsyncClient):
    r = await client.get(f"/api/v1/schools/{_WRONG_SCHOOL}/limits")
    assert r.status_code == 401


# ── resolve_school_limits — override priority ─────────────────────────────────


@pytest.mark.asyncio
async def test_override_takes_priority_over_plan_default(client: AsyncClient):
    """Override values shadow plan defaults; NULL override fields fall back to plan defaults."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    await _insert_subscription(client, school_id, plan="professional")

    # Set only pipeline_quota override; max_students and max_teachers stay as plan defaults
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_plan_overrides (school_id, pipeline_quota, override_reason, set_by_admin_id)
        VALUES ($1, 99, 'test override', $2)
        ON CONFLICT (school_id) DO UPDATE SET pipeline_quota = 99
        """,
        uuid.UUID(school_id),
        uuid.UUID(admin_id),
    )

    token = make_teacher_token(teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin")
    r = await client.get(
        f"/api/v1/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["pipeline_quota_monthly"] == 99  # override applied
    assert data["max_students"] == 150           # plan default (override NULL)
    assert data["max_teachers"] == 10            # plan default (override NULL)
    assert data["has_override"] is True


# ── GET /admin/schools/{school_id}/limits ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_get_school_limits_includes_override_detail(client: AsyncClient):
    """Admin GET returns override object when an override exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)

    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_plan_overrides (school_id, max_students, override_reason, set_by_admin_id)
        VALUES ($1, 200, 'VIP school', $2)
        ON CONFLICT (school_id) DO UPDATE SET max_students = 200
        """,
        uuid.UUID(school_id),
        uuid.UUID(admin_id),
    )

    token = make_admin_token(admin_id=admin_id, role="super_admin")
    r = await client.get(
        f"/api/v1/admin/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_override"] is True
    assert data["override"]["max_students"] == 200
    assert data["override"]["override_reason"] == "VIP school"


@pytest.mark.asyncio
async def test_admin_get_school_limits_no_override(client: AsyncClient):
    """Admin GET returns override=None when no override exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)

    token = make_admin_token(admin_id=admin_id, role="super_admin")
    r = await client.get(
        f"/api/v1/admin/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["has_override"] is False
    assert data["override"] is None


@pytest.mark.asyncio
async def test_admin_get_school_not_found_returns_404(client: AsyncClient):
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    r = await client.get(
        f"/api/v1/admin/schools/{_NOT_FOUND_SCHOOL}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_limits_insufficient_permission_returns_403(client: AsyncClient):
    """developer role does not have school:manage — 403."""
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id, role="developer")
    token = make_admin_token(admin_id=admin_id, role="developer")

    r = await client.get(
        f"/api/v1/admin/schools/{_NOT_FOUND_SCHOOL}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ── PUT /admin/schools/{school_id}/limits ─────────────────────────────────────


@pytest.mark.asyncio
async def test_set_override_creates_row_and_writes_audit_log(client: AsyncClient):
    """PUT creates override row; audit log entry dispatched."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    with patch("src.school.limits_router.write_audit_log") as mock_audit:
        r = await client.put(
            f"/api/v1/admin/schools/{school_id}/limits",
            json={"max_students": 500, "pipeline_quota": 20, "override_reason": "Big school"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "override_set"
    assert data["school_id"] == school_id
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["event_type"] == "SET_SCHOOL_LIMITS_OVERRIDE"

    # Verify the row was persisted
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT max_students, pipeline_quota FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    assert row is not None
    assert row["max_students"] == 500
    assert row["pipeline_quota"] == 20


@pytest.mark.asyncio
async def test_set_override_missing_reason_returns_422(client: AsyncClient):
    """override_reason is required — 422 without it."""
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    r = await client.put(
        f"/api/v1/admin/schools/{_NOT_FOUND_SCHOOL}/limits",
        json={"max_students": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_set_override_school_not_found_returns_404(client: AsyncClient):
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    r = await client.put(
        f"/api/v1/admin/schools/{_NOT_FOUND_SCHOOL}/limits",
        json={"max_students": 100, "override_reason": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ── DELETE /admin/schools/{school_id}/limits ──────────────────────────────────


@pytest.mark.asyncio
async def test_clear_override_removes_row_and_writes_audit_log(client: AsyncClient):
    """DELETE removes override row and dispatches audit log entry."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    # Seed an override first
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_plan_overrides (school_id, max_students, override_reason, set_by_admin_id)
        VALUES ($1, 999, 'to be cleared', $2)
        ON CONFLICT (school_id) DO UPDATE SET max_students = 999
        """,
        uuid.UUID(school_id),
        uuid.UUID(admin_id),
    )

    with patch("src.school.limits_router.write_audit_log") as mock_audit:
        r = await client.delete(
            f"/api/v1/admin/schools/{school_id}/limits",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "override_cleared"
    mock_audit.assert_called_once()
    assert mock_audit.call_args[1]["event_type"] == "CLEAR_SCHOOL_LIMITS_OVERRIDE"

    # Row should be gone
    row = await pool.fetchrow(
        "SELECT 1 FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    assert row is None


@pytest.mark.asyncio
async def test_clear_override_no_override_returns_404(client: AsyncClient):
    """DELETE when no override exists returns 404."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    r = await client.delete(
        f"/api/v1/admin/schools/{school_id}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "no_override"


@pytest.mark.asyncio
async def test_clear_override_school_not_found_returns_404(client: AsyncClient):
    admin_id = _ADMIN_ID_01
    await _seed_admin(client, admin_id)
    token = make_admin_token(admin_id=admin_id, role="super_admin")

    r = await client.delete(
        f"/api/v1/admin/schools/{_NOT_FOUND_SCHOOL}/limits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
