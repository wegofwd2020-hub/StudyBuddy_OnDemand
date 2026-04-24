"""
tests/test_auth_dependencies_coverage.py

Targeted coverage of src/auth/dependencies.py — next-round PR C of #261.

Covers the branches at 0% on main (lines 66, 78-79, 92, 112, 149,
162-165, 175-176, 187, 218):

  - get_current_student — missing student_id (L66); suspended (L78-79);
                           demo_student blacklisted (L92); account
                           deleted (L112)
  - get_current_teacher — missing teacher_id (L149); demo_teacher
                           blacklisted (L162-165); suspended (L175-176);
                           account pending (L187)
  - get_current_admin   — role not in admin set (L218)

The tests hit a real FastAPI route that uses each dependency and
assert on the status code + error envelope produced by dependencies.py.
The handler logic never executes because the dependency raises first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from tests.helpers.token_factory import (
    JWT_ALGORITHM,
    TEST_ADMIN_JWT_SECRET,
    TEST_JWT_SECRET,
    make_demo_student_token,
    make_demo_teacher_token,
    make_student_token,
    make_teacher_token,
)


def _craft_token(payload: dict, secret: str = TEST_JWT_SECRET) -> str:
    """Craft a JWT with arbitrary payload — for branches where token_factory
    would always include the missing-field we want to test."""
    now = datetime.now(tz=UTC)
    default = {
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode({**default, **payload}, secret, algorithm=JWT_ALGORITHM)


# ── get_current_student branches ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_student_token_missing_student_id_returns_401(client: AsyncClient):
    """role=student, student_id absent → 401 invalid_token (L66)."""
    token = _craft_token({"role": "student", "account_status": "active"})
    r = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_student_suspended_in_redis_returns_403(
    client: AsyncClient, fake_redis
):
    """Suspended:{student_id} present in redis → 403 (L78-79)."""
    client._transport.app.state.redis = fake_redis

    student_id = "d1500000-0000-0000-0000-000000000099"
    await fake_redis.set(f"suspended:{student_id}", "1")

    token = make_student_token(student_id=student_id)
    r = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "account_suspended"


@pytest.mark.asyncio
async def test_demo_student_blacklisted_jti_returns_401(
    client: AsyncClient, fake_redis
):
    """demo_student with blacklisted JTI → 401 (L92)."""
    client._transport.app.state.redis = fake_redis

    token = make_demo_student_token()
    # Decode to read the jti (random per call).
    payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])
    await fake_redis.set(f"demo_blacklist:{payload['jti']}", "1")

    r = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_student_deleted_account_status_returns_401(client: AsyncClient):
    """account_status=deleted → 401 unauthenticated (L112)."""
    token = make_student_token(account_status="deleted")
    r = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


# ── get_current_teacher branches ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_token_missing_teacher_id_returns_401(client: AsyncClient):
    """role=teacher, teacher_id absent → 401 invalid_token (L149)."""
    token = _craft_token(
        {
            "role": "teacher",
            "school_id": "d3000000-0000-0000-0000-000000000001",
            "account_status": "active",
        }
    )
    school_id = "d3000000-0000-0000-0000-000000000001"
    r = await client.get(
        f"/api/v1/analytics/school/{school_id}/class",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_demo_teacher_blacklisted_jti_returns_401(
    client: AsyncClient, fake_redis
):
    """demo_teacher with blacklisted JTI → 401 (L162-165)."""
    client._transport.app.state.redis = fake_redis

    token = make_demo_teacher_token()
    payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])
    await fake_redis.set(f"demo_teacher_blacklist:{payload['jti']}", "1")

    # Any teacher-gated route works.
    r = await client.get(
        "/api/v1/analytics/school/d3000000-0000-0000-0000-000000000001/class",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_teacher_suspended_in_redis_returns_403(
    client: AsyncClient, fake_redis
):
    """Suspended:{teacher_id} key → 403 (L175-176)."""
    client._transport.app.state.redis = fake_redis

    teacher_id = "d2500000-0000-0000-0000-000000000099"
    await fake_redis.set(f"suspended:{teacher_id}", "1")

    token = make_teacher_token(teacher_id=teacher_id)
    r = await client.get(
        "/api/v1/analytics/school/d3000000-0000-0000-0000-000000000001/class",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "account_suspended"


@pytest.mark.asyncio
async def test_teacher_pending_account_status_returns_403(client: AsyncClient):
    """account_status=pending → 403 account_pending (L187)."""
    token = make_teacher_token(account_status="pending")
    r = await client.get(
        "/api/v1/analytics/school/d3000000-0000-0000-0000-000000000001/class",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "account_pending"


# ── get_current_admin branch ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_token_with_invalid_role_returns_403(client: AsyncClient):
    """Admin JWT with a role outside the admin set → 403 forbidden (L218)."""
    # Craft an admin-signed token with a non-admin role.
    token = _craft_token(
        {"admin_id": "d4500000-0000-0000-0000-000000000099", "role": "student"},
        secret=TEST_ADMIN_JWT_SECRET,
    )

    # A route that uses get_current_admin — GET /admin/schools.
    r = await client.get(
        "/api/v1/admin/schools",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Role check is the first dependency-layer rejection, so 403.
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"
