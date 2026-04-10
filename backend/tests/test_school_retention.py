"""
tests/test_school_retention.py

Tests for the school curriculum version retention endpoint:
  DELETE /api/v1/schools/{school_id}/curriculum/versions/{curriculum_id}

Covers:
  - Happy path delete (frees version slot)
  - Version cap: 4 existing allows upload of a 5th
  - Version cap: 5 existing blocks a 6th upload (409 version_cap_reached)
  - Cap freed after delete: delete + re-upload succeeds
  - Idempotent re-upload of the same curriculum_id does not increment version count
  - Delete blocked when version is assigned to a grade (409 version_assigned)
  - Delete blocked when a pipeline job is running (409 pipeline_active)
  - Wrong school returns 403
  - Plain teacher (not school_admin) returns 403
  - Missing curriculum returns 404
"""

from __future__ import annotations

import io
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from main import app
from tests.helpers.token_factory import make_teacher_token


# ── Helpers ───────────────────────────────────────────────────────────────────


def _grade_json(grade: int, suffix: str = "") -> bytes:
    """Minimal valid grade JSON. suffix differentiates unit IDs between versions."""
    return json.dumps({
        "grade": grade,
        "subjects": [
            {
                "name": "Mathematics",
                "units": [
                    {"unit_id": f"G{grade}-MATH-001{suffix}", "title": "Algebra Basics"},
                ],
            },
        ],
    }).encode()


async def _register_school(client: AsyncClient) -> dict:
    """Register a school. Returns {school_id, teacher_id, access_token}."""
    unique_email = f"retention-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Retention Test School",
        "contact_email": unique_email,
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _upload(
    client: AsyncClient,
    school_id: str,
    token: str,
    grade: int,
    year: int,
) -> str:
    """Upload a curriculum JSON and return the curriculum_id."""
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": (
            f"grade{grade}_{year}.json",
            io.BytesIO(_grade_json(grade, f"-{year}")),
            "application/json",
        )},
        params={"year": year},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    return r.json()["curriculum_id"]


async def _delete_version(
    client: AsyncClient,
    school_id: str,
    curriculum_id: str,
    token: str,
) -> tuple[int, dict]:
    r = await client.delete(
        f"/api/v1/schools/{school_id}/curriculum/versions/{curriculum_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.status_code, r.json()


# ── Delete happy path ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_curriculum_version_happy_path(client: AsyncClient):
    """Deleting an existing version returns 200 with deleted=True and decrements version_count."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    curriculum_id = await _upload(client, school_id, token, grade=9, year=2026)

    status, data = await _delete_version(client, school_id, curriculum_id, token)
    assert status == 200, data
    assert data["deleted"] is True
    assert data["curriculum_id"] == curriculum_id
    assert data["grade"] == 9
    assert data["version_count"] == 0


# ── Version cap enforcement ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_allowed_at_version_4(client: AsyncClient):
    """A school with 4 versions for a grade can still upload a 5th."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    # Upload 4 versions (different years → different curriculum_ids)
    for year in range(2024, 2028):
        cid = await _upload(client, school_id, token, grade=7, year=year)
        assert cid == f"{school_id}-{year}-g7"

    # 5th upload must succeed
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": (
            "grade7_2028.json",
            io.BytesIO(_grade_json(7, "-2028")),
            "application/json",
        )},
        params={"year": 2028},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["version_count"] == 5


@pytest.mark.asyncio
async def test_upload_blocked_at_version_cap(client: AsyncClient):
    """A school with 5 versions for a grade gets 409 version_cap_reached on the 6th."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    for year in range(2024, 2029):
        await _upload(client, school_id, token, grade=6, year=year)

    # 6th upload must be blocked
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": (
            "grade6_2029.json",
            io.BytesIO(_grade_json(6, "-2029")),
            "application/json",
        )},
        params={"year": 2029},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409, r.text
    data = r.json()
    assert data["error"] == "version_cap_reached"
    assert data["cap"] == 5
    assert data["current_count"] == 5


@pytest.mark.asyncio
async def test_delete_frees_cap_slot(client: AsyncClient):
    """After deleting one of 5 versions, a new upload succeeds."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    # Fill the cap for grade 11
    cids = []
    for year in range(2024, 2029):
        cid = await _upload(client, school_id, token, grade=11, year=year)
        cids.append(cid)

    # Delete the oldest version
    status, data = await _delete_version(client, school_id, cids[0], token)
    assert status == 200, data
    assert data["version_count"] == 4

    # Now the 6th upload should succeed
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": (
            "grade11_2029.json",
            io.BytesIO(_grade_json(11, "-2029")),
            "application/json",
        )},
        params={"year": 2029},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["version_count"] == 5


# ── Idempotent re-upload ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reupload_same_curriculum_is_idempotent(client: AsyncClient):
    """Re-uploading the same school+year+grade does not increment version_count."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    cid1 = await _upload(client, school_id, token, grade=8, year=2026)

    # Upload again — same year, same grade → same curriculum_id
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": (
            "grade8_2026_v2.json",
            io.BytesIO(_grade_json(8, "-2026")),
            "application/json",
        )},
        params={"year": 2026},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["curriculum_id"] == cid1  # same ID
    assert data["version_count"] == 1     # still 1 version, not 2


# ── Delete blocked: version assigned to a grade ───────────────────────────────


@pytest.mark.asyncio
async def test_delete_blocked_when_version_assigned_to_grade(client: AsyncClient):
    """Delete returns 409 version_assigned if the curriculum is pinned to a grade."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    curriculum_id = await _upload(client, school_id, token, grade=10, year=2026)

    # Directly insert a grade_curriculum_assignment to simulate a pinned version.
    # Phase F (PUT /schools/{id}/grades/{grade}/curriculum-version) is not yet built —
    # we seed the row directly via the test pool with RLS bypassed (session-level).
    async with app.state.pool.acquire() as conn:
        # session-level (false) so it persists across the implicit autocommit statements
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO grade_curriculum_assignments (school_id, grade, curriculum_id)
            VALUES ($1::uuid, $2, $3)
            ON CONFLICT (school_id, grade) DO UPDATE SET curriculum_id = EXCLUDED.curriculum_id
            """,
            school_id, 10, curriculum_id,
        )

    status, data = await _delete_version(client, school_id, curriculum_id, token)
    assert status == 409, data
    assert data["error"] == "version_assigned"
    assert 10 in data["assigned_grades"]


# ── Delete blocked: active pipeline job ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_blocked_when_pipeline_running(client: AsyncClient):
    """Delete returns 409 pipeline_active if a job is queued or running for the version."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    curriculum_id = await _upload(client, school_id, token, grade=12, year=2026)

    # Inject a 'running' pipeline job directly via the test pool (RLS bypassed).
    job_id = str(uuid.uuid4())
    async with app.state.pool.acquire() as conn:
        # session-level bypass so it covers the subsequent INSERT
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO pipeline_jobs
                (job_id, curriculum_id, grade, langs, force, status, school_id)
            VALUES ($1, $2, 12, 'en', false, 'running', $3::uuid)
            """,
            job_id, curriculum_id, school_id,
        )

    status, data = await _delete_version(client, school_id, curriculum_id, token)
    assert status == 409, data
    assert data["error"] == "pipeline_active"
    assert data["job_id"] == job_id


# ── Access control ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_wrong_school_returns_404(client: AsyncClient):
    """Cross-school version delete returns 404 (not 403) to avoid revealing other school's data."""
    reg = await _register_school(client)
    other_reg = await _register_school(client)

    school_id = reg["school_id"]
    other_school_id = other_reg["school_id"]
    my_token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )
    other_token = make_teacher_token(
        teacher_id=other_reg["teacher_id"],
        school_id=other_school_id,
        role="school_admin",
    )

    # Upload curriculum in other school
    other_cid = await _upload(client, other_school_id, other_token, grade=9, year=2026)

    # Try to delete it using my token (wrong school_id in path).
    # Returns 404 — not 403 — so we don't reveal that the other school's curriculum exists.
    status, data = await _delete_version(client, school_id, other_cid, my_token)
    assert status == 404, data


@pytest.mark.asyncio
async def test_delete_plain_teacher_returns_403(client: AsyncClient):
    """A teacher with role='teacher' (not school_admin) is rejected with 403."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    admin_token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )
    curriculum_id = await _upload(client, school_id, admin_token, grade=8, year=2026)

    # Issue a plain teacher token (not school_admin)
    teacher_token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="teacher"
    )

    status, data = await _delete_version(client, school_id, curriculum_id, teacher_token)
    assert status == 403, data


@pytest.mark.asyncio
async def test_delete_missing_curriculum_returns_404(client: AsyncClient):
    """Deleting a curriculum_id that doesn't exist returns 404."""
    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    fake_id = f"{school_id}-2099-g5"
    status, data = await _delete_version(client, school_id, fake_id, token)
    assert status == 404, data
    assert data["error"] == "not_found"


@pytest.mark.asyncio
async def test_delete_requires_auth(client: AsyncClient):
    """Delete without a JWT returns 401."""
    r = await client.delete(
        f"/api/v1/schools/{uuid.uuid4()}/curriculum/versions/fake-id"
    )
    assert r.status_code == 401
