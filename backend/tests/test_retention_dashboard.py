"""
tests/test_retention_dashboard.py

Integration tests for Phase F retention dashboard endpoints.

Endpoints under test:
  GET  /api/v1/schools/{school_id}/retention
  POST /api/v1/schools/{school_id}/curriculum/versions/{curriculum_id}/renew
  PUT  /api/v1/schools/{school_id}/grades/{grade}/curriculum

Tests seed school + teacher JWTs via the public registration API, then insert
curricula directly via the DB pool with RLS bypassed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from main import app
from tests.helpers.token_factory import make_teacher_token


# ── Test helpers ──────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    """
    Register a school and return {school_id, teacher_id, token}.

    token is a signed school_admin JWT — the registration API returns school_id
    and teacher_id; the JWT is minted here via make_teacher_token.
    """
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Dashboard Test School",
        "contact_email": f"dash-{uuid.uuid4().hex[:8]}@example.com",
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
    school_id: str,
    grade: int = 8,
    year: int = 2026,
    *,
    retention_status: str = "active",
    expires_at: datetime | None = None,
    grace_until: datetime | None = None,
) -> str:
    """Insert a curricula row directly via the app pool (RLS bypassed)."""
    curriculum_id = f"{school_id[:8]}-{year}-g{grade}-{uuid.uuid4().hex[:6]}"
    expires_at = expires_at or (datetime.now(UTC) + timedelta(days=365))

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type,
                 school_id, status, owner_type, owner_id, retention_status,
                 expires_at, grace_until)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid, 'active',
                    'school', $5::uuid, $6, $7, $8)
            ON CONFLICT (curriculum_id) DO UPDATE
                SET retention_status = EXCLUDED.retention_status,
                    expires_at       = EXCLUDED.expires_at,
                    grace_until      = EXCLUDED.grace_until
            """,
            curriculum_id, grade, year, f"Grade {grade} Curriculum ({year})",
            school_id, retention_status, expires_at, grace_until,
        )
    return curriculum_id


# ── GET /schools/{school_id}/retention ───────────────────────────────────────


@pytest.mark.asyncio
async def test_retention_dashboard_empty_school(client: AsyncClient):
    """A freshly registered school with no curricula returns empty list."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["school_id"] == school_id
    assert body["total_versions"] == 0
    assert body["active_count"] == 0
    assert body["curricula"] == []


@pytest.mark.asyncio
async def test_retention_dashboard_lists_all_statuses(client: AsyncClient):
    """Dashboard lists active, unavailable, and purged versions with correct counts."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    now = datetime.now(UTC)

    # Seed one of each status.
    await _seed_curriculum(
        school_id, grade=5, year=2026,
        retention_status="active",
        expires_at=now + timedelta(days=200),
    )
    await _seed_curriculum(
        school_id, grade=6, year=2026,
        retention_status="unavailable",
        expires_at=now - timedelta(days=10),
        grace_until=now + timedelta(days=170),
    )
    await _seed_curriculum(
        school_id, grade=7, year=2026,
        retention_status="purged",
        expires_at=now - timedelta(days=200),
    )

    r = await client.get(
        f"/api/v1/schools/{school_id}/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_versions"] == 3
    assert body["active_count"] == 1
    assert body["unavailable_count"] == 1
    assert body["purged_count"] == 1


@pytest.mark.asyncio
async def test_retention_dashboard_days_until_expiry(client: AsyncClient):
    """days_until_expiry is computed correctly for active curricula."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    expires = datetime.now(UTC) + timedelta(days=30)
    await _seed_curriculum(
        school_id, grade=8, year=2026,
        retention_status="active",
        expires_at=expires,
    )

    r = await client.get(
        f"/api/v1/schools/{school_id}/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    cur = body["curricula"][0]
    assert cur["retention_status"] == "active"
    # days_until_expiry ≈ 30 (within 1 day of clock drift)
    assert 28 <= cur["days_until_expiry"] <= 31
    assert cur["days_until_purge"] is None


@pytest.mark.asyncio
async def test_retention_dashboard_days_until_purge(client: AsyncClient):
    """days_until_purge is computed correctly for unavailable curricula."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    now = datetime.now(UTC)
    await _seed_curriculum(
        school_id, grade=9, year=2026,
        retention_status="unavailable",
        expires_at=now - timedelta(days=10),
        grace_until=now + timedelta(days=90),
    )

    r = await client.get(
        f"/api/v1/schools/{school_id}/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    cur = r.json()["curricula"][0]
    assert cur["retention_status"] == "unavailable"
    assert cur["days_until_expiry"] is None
    assert 88 <= cur["days_until_purge"] <= 91


@pytest.mark.asyncio
async def test_retention_dashboard_is_assigned_flag(client: AsyncClient):
    """is_assigned is true for curricula that appear in grade_curriculum_assignments."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(school_id, grade=10, year=2026)

    # Assign it to grade 10.
    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/10/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    r = await client.get(
        f"/api/v1/schools/{school_id}/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    cur = r.json()["curricula"][0]
    assert cur["curriculum_id"] == cid
    assert cur["is_assigned"] is True


@pytest.mark.asyncio
async def test_retention_dashboard_wrong_school_403(client: AsyncClient):
    """A teacher cannot see another school's retention dashboard."""
    reg_a = await _register_school(client)
    reg_b = await _register_school(client)
    token_a = reg_a["token"]
    school_b = reg_b["school_id"]

    r = await client.get(
        f"/api/v1/schools/{school_b}/retention",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_retention_dashboard_no_auth_401(client: AsyncClient):
    """Unauthenticated request returns 401."""
    reg = await _register_school(client)
    r = await client.get(f"/api/v1/schools/{reg['school_id']}/retention")
    assert r.status_code == 401


# ── POST /schools/{school_id}/curriculum/versions/{curriculum_id}/renew ───────


@pytest.mark.asyncio
async def test_renew_active_curriculum(client: AsyncClient):
    """Renewing an active curriculum extends expires_at by 1 year."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    old_expires = datetime.now(UTC) + timedelta(days=10)
    cid = await _seed_curriculum(
        school_id, grade=8, year=2026,
        retention_status="active",
        expires_at=old_expires,
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["curriculum_id"] == cid
    assert body["retention_status"] == "active"
    assert body["new_expires_at"] is not None

    # new_expires_at ≈ old_expires + 365 days (within 2 days to allow for clock/leap)
    new_exp = datetime.fromisoformat(body["new_expires_at"])
    old_exp = datetime.fromisoformat(body["previous_expires_at"])
    delta_days = (new_exp - old_exp).days
    assert 363 <= delta_days <= 367


@pytest.mark.asyncio
async def test_renew_unavailable_restores_access(client: AsyncClient):
    """Renewing an unavailable curriculum resets retention_status to 'active'."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    now = datetime.now(UTC)
    cid = await _seed_curriculum(
        school_id, grade=9, year=2026,
        retention_status="unavailable",
        expires_at=now - timedelta(days=5),
        grace_until=now + timedelta(days=175),
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["retention_status"] == "active"

    # Verify grace_until was cleared in DB.
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        row = await conn.fetchrow(
            "SELECT retention_status, grace_until FROM curricula WHERE curriculum_id = $1",
            cid,
        )
    assert row["retention_status"] == "active"
    assert row["grace_until"] is None


@pytest.mark.asyncio
async def test_renew_purged_returns_409(client: AsyncClient):
    """Renewing a purged curriculum returns 409 with 'already_purged' error."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(
        school_id, grade=10, year=2026,
        retention_status="purged",
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/{cid}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "already_purged"


@pytest.mark.asyncio
async def test_renew_missing_curriculum_returns_404(client: AsyncClient):
    """Renewing a non-existent curriculum returns 404."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/versions/nonexistent-id/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_renew_wrong_school_returns_403(client: AsyncClient):
    """A teacher cannot renew another school's curriculum."""
    reg_a = await _register_school(client)
    reg_b = await _register_school(client)
    token_a = reg_a["token"]
    school_b = reg_b["school_id"]

    cid = await _seed_curriculum(school_b, grade=8, year=2026)

    r = await client.post(
        f"/api/v1/schools/{school_b}/curriculum/versions/{cid}/renew",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_renew_requires_auth(client: AsyncClient):
    """Unauthenticated renew returns 401."""
    r = await client.post(
        "/api/v1/schools/some-school/curriculum/versions/some-id/renew"
    )
    assert r.status_code == 401


# ── PUT /schools/{school_id}/grades/{grade}/curriculum ───────────────────────


@pytest.mark.asyncio
async def test_assign_curriculum_to_grade_happy_path(client: AsyncClient):
    """Assigning an active curriculum to a grade returns 200 with assigned_at."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(school_id, grade=7, year=2026)

    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/7/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["school_id"] == school_id
    assert body["grade"] == 7
    assert body["curriculum_id"] == cid
    assert body["previous_curriculum_id"] is None
    assert body["assigned_at"] is not None


@pytest.mark.asyncio
async def test_assign_curriculum_idempotent(client: AsyncClient):
    """Assigning the same curriculum twice is idempotent."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(school_id, grade=8, year=2026)

    # First assignment
    r1 = await client.put(
        f"/api/v1/schools/{school_id}/grades/8/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200

    # Second assignment — same curriculum
    r2 = await client.put(
        f"/api/v1/schools/{school_id}/grades/8/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["curriculum_id"] == cid


@pytest.mark.asyncio
async def test_assign_curriculum_tracks_previous(client: AsyncClient):
    """Reassigning a grade returns the previous curriculum_id in previous_curriculum_id."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid1 = await _seed_curriculum(school_id, grade=9, year=2024)
    cid2 = await _seed_curriculum(school_id, grade=9, year=2025)

    await client.put(
        f"/api/v1/schools/{school_id}/grades/9/curriculum",
        json={"curriculum_id": cid1},
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/9/curriculum",
        json={"curriculum_id": cid2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["previous_curriculum_id"] == cid1
    assert r.json()["curriculum_id"] == cid2


@pytest.mark.asyncio
async def test_assign_unavailable_curriculum_returns_409(client: AsyncClient):
    """Cannot assign a curriculum in 'unavailable' status."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(
        school_id, grade=10, year=2026,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=5),
    )

    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/10/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "curriculum_not_active"


@pytest.mark.asyncio
async def test_assign_grade_mismatch_returns_422(client: AsyncClient):
    """Curriculum grade must match path grade."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    cid = await _seed_curriculum(school_id, grade=8, year=2026)

    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/9/curriculum",  # grade 9, but cid is grade 8
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "grade_mismatch"


@pytest.mark.asyncio
async def test_assign_missing_curriculum_returns_404(client: AsyncClient):
    """Assigning a non-existent curriculum returns 404."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = reg["token"]

    r = await client.put(
        f"/api/v1/schools/{school_id}/grades/8/curriculum",
        json={"curriculum_id": "nonexistent-id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_assign_wrong_school_returns_403(client: AsyncClient):
    """A teacher cannot assign another school's curriculum."""
    reg_a = await _register_school(client)
    reg_b = await _register_school(client)
    token_a = reg_a["token"]
    school_b = reg_b["school_id"]

    cid = await _seed_curriculum(school_b, grade=8, year=2026)

    r = await client.put(
        f"/api/v1/schools/{school_b}/grades/8/curriculum",
        json={"curriculum_id": cid},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_assign_requires_auth(client: AsyncClient):
    """Unauthenticated assign returns 401."""
    r = await client.put(
        "/api/v1/schools/some-school/grades/8/curriculum",
        json={"curriculum_id": "some-id"},
    )
    assert r.status_code == 401
