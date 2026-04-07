"""
tests/test_school_storage.py

Tests for the school storage metering endpoint:
  GET /api/v1/schools/{school_id}/storage

Covers:
  - Happy path: returns quota + zero breakdown for a new school
  - Breakdown populated from pipeline_jobs with payload_bytes
  - Only completed jobs count (queued/running/failed excluded)
  - Multiple curricula appear as separate breakdown entries
  - plain teacher (not school_admin) returns 403
  - Wrong school returns 403
  - Unauthenticated returns 401
  - over_quota flag set when used_bytes > total_gb * 1073741824
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from main import app
from tests.helpers.token_factory import make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    unique_email = f"storage-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Storage Test School",
        "contact_email": unique_email,
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_pipeline_job(
    school_id: str,
    curriculum_id: str,
    grade: int,
    payload_bytes: int,
    status: str = "completed",
) -> str:
    """Insert a pipeline_jobs row directly via the app pool and return job_id."""
    job_id = str(uuid.uuid4())
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO pipeline_jobs
                (job_id, curriculum_id, grade, langs, force, status,
                 school_id, payload_bytes)
            VALUES ($1, $2, $3, 'en', false, $4, $5::uuid, $6)
            """,
            job_id, curriculum_id, grade, status, school_id, payload_bytes,
        )
    return job_id


async def _get_storage(
    client: AsyncClient,
    school_id: str,
    token: str,
) -> tuple[int, dict]:
    r = await client.get(
        f"/api/v1/schools/{school_id}/storage",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.status_code, r.json()


# ── Happy path — new school (no jobs yet) ────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_new_school_zero_usage(client: AsyncClient):
    """A newly registered school has 5 GB quota and 0 used_bytes."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    status, data = await _get_storage(client, school_id, token)
    assert status == 200, data
    assert data["school_id"] == school_id
    assert data["base_gb"] == 5
    assert data["purchased_gb"] == 0
    assert data["total_gb"] == 5
    assert data["used_bytes"] == 0
    assert data["used_gb"] == 0.0
    assert data["used_pct"] == 0.0
    assert data["over_quota"] is False
    assert data["breakdown"] == []


# ── Breakdown from completed pipeline jobs ────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_breakdown_from_completed_jobs(client: AsyncClient):
    """Completed jobs with payload_bytes appear in the breakdown."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    curriculum_id = f"{school_id}-2026-g8"

    # Seed two completed jobs for the same curriculum
    await _seed_pipeline_job(school_id, curriculum_id, 8, 100_000_000)
    await _seed_pipeline_job(school_id, curriculum_id, 8, 50_000_000)

    status, data = await _get_storage(client, school_id, token)
    assert status == 200, data

    assert len(data["breakdown"]) == 1
    entry = data["breakdown"][0]
    assert entry["curriculum_id"] == curriculum_id
    assert entry["grade"] == 8
    assert entry["bytes_used"] == 150_000_000
    assert entry["job_count"] == 2
    assert entry["gb_used"] > 0


@pytest.mark.asyncio
async def test_storage_only_completed_jobs_counted(client: AsyncClient):
    """Queued, running, and failed jobs do not contribute to breakdown."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    curriculum_id = f"{school_id}-2026-g9"

    await _seed_pipeline_job(school_id, curriculum_id, 9, 80_000_000, status="completed")
    await _seed_pipeline_job(school_id, curriculum_id, 9, 80_000_000, status="queued")
    await _seed_pipeline_job(school_id, curriculum_id, 9, 80_000_000, status="running")
    await _seed_pipeline_job(school_id, curriculum_id, 9, 80_000_000, status="failed")

    status, data = await _get_storage(client, school_id, token)
    assert status == 200, data
    assert len(data["breakdown"]) == 1
    assert data["breakdown"][0]["bytes_used"] == 80_000_000  # only the completed one
    assert data["breakdown"][0]["job_count"] == 1


@pytest.mark.asyncio
async def test_storage_multiple_curricula_separate_entries(client: AsyncClient):
    """Multiple curricula for the same school appear as separate breakdown rows."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    cid_g8 = f"{school_id}-2026-g8"
    cid_g9 = f"{school_id}-2026-g9"

    await _seed_pipeline_job(school_id, cid_g8, 8, 200_000_000)
    await _seed_pipeline_job(school_id, cid_g9, 9, 100_000_000)

    status, data = await _get_storage(client, school_id, token)
    assert status == 200, data

    assert len(data["breakdown"]) == 2
    # Breakdown is ordered by bytes_used DESC
    assert data["breakdown"][0]["bytes_used"] == 200_000_000
    assert data["breakdown"][1]["bytes_used"] == 100_000_000


@pytest.mark.asyncio
async def test_storage_over_quota_flag(client: AsyncClient):
    """over_quota is True when used_bytes exceeds total_gb * 1 073 741 824."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    # 5 GB quota = 5 * 1073741824 = 5_368_709_120 bytes
    # Push used_bytes over limit via school_storage_quotas directly
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            UPDATE school_storage_quotas
            SET used_bytes = 6000000000
            WHERE school_id = $1::uuid
            """,
            school_id,
        )

    status, data = await _get_storage(client, school_id, token)
    assert status == 200, data
    assert data["over_quota"] is True
    assert data["used_bytes"] == 6_000_000_000
    assert data["used_pct"] > 100


# ── Access control ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_plain_teacher_returns_403(client: AsyncClient):
    """A teacher (not school_admin) cannot view storage."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="teacher"
    )

    status, data = await _get_storage(client, school_id, token)
    assert status == 403, data


@pytest.mark.asyncio
async def test_storage_wrong_school_returns_403(client: AsyncClient):
    """A school_admin cannot view another school's storage."""
    reg = await _register_school(client)
    other_reg = await _register_school(client)

    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
    )
    status, data = await _get_storage(client, other_reg["school_id"], token)
    assert status == 403, data


@pytest.mark.asyncio
async def test_storage_requires_auth(client: AsyncClient):
    """Storage endpoint without JWT returns 401."""
    r = await client.get(f"/api/v1/schools/{uuid.uuid4()}/storage")
    assert r.status_code == 401
