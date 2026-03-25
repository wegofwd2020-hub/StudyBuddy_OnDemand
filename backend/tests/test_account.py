"""
tests/test_account.py

Tests for account management endpoints.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token, make_student_token


async def _create_student(pool, email: str = None, status: str = "active") -> dict:
    """Helper: insert a student record directly into the test DB."""
    email = email or f"student_{uuid.uuid4().hex[:8]}@example.com"
    row = await pool.fetchrow(
        """
        INSERT INTO students
            (external_auth_id, auth_provider, name, email, grade, locale, account_status)
        VALUES ($1, 'auth0', $2, $3, 8, 'en', $4)
        RETURNING student_id, name, email, account_status
        """,
        f"auth0|{uuid.uuid4()}",
        "Test Student",
        email,
        status,
    )
    return dict(row)


async def _create_school(pool) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO schools (name, contact_email, country)
        VALUES ('Test School', 'school@example.com', 'CA')
        RETURNING school_id, name, status
        """
    )
    return dict(row)


async def _create_teacher(pool, school_id: uuid.UUID, email: str = None) -> dict:
    email = email or f"teacher_{uuid.uuid4().hex[:8]}@example.com"
    row = await pool.fetchrow(
        """
        INSERT INTO teachers (school_id, external_auth_id, name, email, role, account_status)
        VALUES ($1, $2, 'Test Teacher', $3, 'teacher', 'active')
        RETURNING teacher_id, school_id, name, email, account_status
        """,
        school_id,
        f"auth0|{uuid.uuid4()}",
        email,
    )
    return dict(row)


# ── Student status changes ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_suspend_student(client: AsyncClient):
    """product_admin can PATCH student status to suspended."""
    pool = client._transport.app.state.pool
    student = await _create_student(pool)
    token = make_admin_token(role="product_admin")

    response = await client.patch(
        f"/api/v1/account/students/{student['student_id']}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["account_status"] == "suspended"


@pytest.mark.asyncio
async def test_admin_can_reactivate_student(client: AsyncClient, fake_redis):
    """product_admin can reactivate a suspended student."""
    pool = client._transport.app.state.pool
    student = await _create_student(pool, status="suspended")

    # Add to Redis suspended set to simulate full suspension.
    await fake_redis.set(f"suspended:{student['student_id']}", "1")

    token = make_admin_token(role="product_admin")
    response = await client.patch(
        f"/api/v1/account/students/{student['student_id']}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["account_status"] == "active"

    # Redis key should be removed.
    exists = await fake_redis.exists(f"suspended:{student['student_id']}")
    assert not exists


@pytest.mark.asyncio
async def test_non_admin_cannot_change_student_status(client: AsyncClient):
    """A student JWT must not be able to change account status (403)."""
    pool = client._transport.app.state.pool
    target = await _create_student(pool)
    student_token = make_student_token()

    response = await client.patch(
        f"/api/v1/account/students/{target['student_id']}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    # Student token uses JWT_SECRET, not ADMIN_JWT_SECRET → 401 or 403
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_developer_role_cannot_suspend_student(client: AsyncClient):
    """developer role does not have student:manage permission → 403."""
    pool = client._transport.app.state.pool
    student = await _create_student(pool)
    dev_token = make_admin_token(role="developer")

    response = await client.patch(
        f"/api/v1/account/students/{student['student_id']}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_suspend_nonexistent_student_returns_404(client: AsyncClient):
    """Suspending a non-existent student returns 404."""
    token = make_admin_token(role="super_admin")
    response = await client.patch(
        f"/api/v1/account/students/{uuid.uuid4()}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suspend_already_suspended_student_returns_409(client: AsyncClient):
    """Suspending an already-suspended student returns 409."""
    pool = client._transport.app.state.pool
    student = await _create_student(pool, status="suspended")
    token = make_admin_token(role="super_admin")

    response = await client.patch(
        f"/api/v1/account/students/{student['student_id']}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cannot_change_deleted_account_status(client: AsyncClient):
    """Changing status on a deleted account returns 409."""
    pool = client._transport.app.state.pool
    student = await _create_student(pool, status="deleted")
    token = make_admin_token(role="super_admin")

    response = await client.patch(
        f"/api/v1/account/students/{student['student_id']}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


# ── Teacher status ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_suspend_teacher(client: AsyncClient):
    """product_admin can suspend a teacher."""
    pool = client._transport.app.state.pool
    school = await _create_school(pool)
    teacher = await _create_teacher(pool, school["school_id"])
    token = make_admin_token(role="product_admin")

    response = await client.patch(
        f"/api/v1/account/teachers/{teacher['teacher_id']}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["account_status"] == "suspended"


# ── School status (cascade) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_suspend_school(client: AsyncClient):
    """product_admin can suspend a school."""
    pool = client._transport.app.state.pool
    school = await _create_school(pool)
    token = make_admin_token(role="product_admin")

    with patch("src.account.router.cascade_school_suspension") as mock_cascade:
        mock_cascade.delay = lambda *a, **kw: None
        response = await client.patch(
            f"/api/v1/account/schools/{school['school_id']}/status",
            json={"status": "suspended"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


@pytest.mark.asyncio
async def test_school_suspension_requires_admin(client: AsyncClient):
    """Non-admin cannot suspend a school."""
    student_token = make_student_token()
    response = await client.patch(
        f"/api/v1/account/schools/{uuid.uuid4()}/status",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code in (401, 403)
