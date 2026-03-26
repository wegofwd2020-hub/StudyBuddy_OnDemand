"""
tests/test_enrolment.py

Tests for Phase 9 enrolment endpoints and curriculum resolver:
  POST /api/v1/schools/{school_id}/enrolment  — upload student email roster
  GET  /api/v1/schools/{school_id}/enrolment  — get roster
  PUT  /api/v1/curriculum/{curriculum_id}/activate — activate curriculum
  Curriculum resolver: resolver unit tests
  Auth exchange: enrolment auto-link on student login
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token, make_teacher_token

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_school(client: AsyncClient, suffix: str = "") -> dict:
    """Register a school; return full response JSON."""
    r = await client.post("/api/v1/schools/register", json={
        "school_name": f"Enrolment School{suffix}",
        "contact_email": f"enrol{suffix}@school.example.com",
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _upload_curriculum(client: AsyncClient, headers: dict, grade: int = 8) -> str:
    """Upload a minimal valid curriculum; return curriculum_id."""
    r = await client.post("/api/v1/curriculum/upload", json={
        "grade": grade,
        "year": 2026,
        "name": f"Test Curriculum Grade {grade}",
        "units": [
            {
                "subject": "Mathematics",
                "unit_name": "Algebra",
                "unit_id": f"MATH-00{grade}",
                "objectives": ["Solve equations", "Graph functions"],
                "has_lab": False,
                "lab_description": None,
            },
            {
                "subject": "Science",
                "unit_name": "Density",
                "unit_id": f"SCI-00{grade}",
                "objectives": ["Apply density formula", "Use equipment safely"],
                "has_lab": True,
                "lab_description": "Measure density of solids.",
            },
        ],
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["curriculum_id"]


# ── POST /schools/{school_id}/enrolment ───────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_roster_succeeds(client: AsyncClient):
    """school_admin can upload a student email roster."""
    school = await _register_school(client, "-roster")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    r = await client.post(
        f"/api/v1/schools/{school_id}/enrolment",
        json={"student_emails": ["alice@example.com", "bob@example.com"]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["enrolled"] == 2
    assert data["already_enrolled"] == 0


@pytest.mark.asyncio
async def test_upload_roster_deduplicates(client: AsyncClient):
    """Re-uploading the same email does not create a duplicate row."""
    school = await _register_school(client, "-dedup")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    payload = {"student_emails": ["dedup@example.com"]}
    r1 = await client.post(f"/api/v1/schools/{school_id}/enrolment", json=payload, headers=headers)
    assert r1.status_code == 201
    assert r1.json()["enrolled"] == 1

    r2 = await client.post(f"/api/v1/schools/{school_id}/enrolment", json=payload, headers=headers)
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["enrolled"] == 0
    assert data2["already_enrolled"] == 1


@pytest.mark.asyncio
async def test_upload_roster_non_admin_returns_403(client: AsyncClient):
    """Regular teacher cannot upload a roster."""
    school = await _register_school(client, "-ra403")
    school_id = school["school_id"]
    teacher_token = make_teacher_token(school_id=school_id, role="teacher")
    headers = {"Authorization": f"Bearer {teacher_token}"}

    r = await client.post(
        f"/api/v1/schools/{school_id}/enrolment",
        json={"student_emails": ["x@x.com"]},
        headers=headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_upload_roster_wrong_school_returns_403(client: AsyncClient):
    """school_admin cannot upload a roster to a different school."""
    school = await _register_school(client, "-ws403")
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    r = await client.post(
        f"/api/v1/schools/{uuid.uuid4()}/enrolment",
        json={"student_emails": ["x@x.com"]},
        headers=headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_upload_roster_requires_auth(client: AsyncClient):
    """Roster upload without JWT returns 403."""
    r = await client.post(
        "/api/v1/schools/some-id/enrolment",
        json={"student_emails": ["x@x.com"]},
    )
    assert r.status_code == 403


# ── GET /schools/{school_id}/enrolment ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_roster_returns_uploaded_emails(client: AsyncClient):
    """GET roster returns emails that were uploaded."""
    school = await _register_school(client, "-getroster")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    await client.post(
        f"/api/v1/schools/{school_id}/enrolment",
        json={"student_emails": ["get1@example.com", "get2@example.com"]},
        headers=headers,
    )

    r = await client.get(f"/api/v1/schools/{school_id}/enrolment", headers=headers)
    assert r.status_code == 200, r.text
    roster = r.json()["roster"]
    emails = [item["student_email"] for item in roster]
    assert "get1@example.com" in emails
    assert "get2@example.com" in emails


@pytest.mark.asyncio
async def test_get_roster_empty_for_new_school(client: AsyncClient):
    """GET roster on a school with no roster returns empty list."""
    school = await _register_school(client, "-emptyroster")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    r = await client.get(f"/api/v1/schools/{school_id}/enrolment", headers=headers)
    assert r.status_code == 200
    assert r.json()["roster"] == []


@pytest.mark.asyncio
async def test_get_roster_non_admin_returns_403(client: AsyncClient):
    """Regular teacher cannot view the roster."""
    school = await _register_school(client, "-gr403")
    school_id = school["school_id"]
    teacher_token = make_teacher_token(school_id=school_id, role="teacher")
    headers = {"Authorization": f"Bearer {teacher_token}"}

    r = await client.get(f"/api/v1/schools/{school_id}/enrolment", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_roster_requires_auth(client: AsyncClient):
    """Roster GET without JWT returns 403."""
    r = await client.get("/api/v1/schools/some-id/enrolment")
    assert r.status_code == 403


# ── PUT /curriculum/{curriculum_id}/activate ──────────────────────────────────

@pytest.mark.asyncio
async def test_activate_curriculum_succeeds(client: AsyncClient):
    """school_admin can activate a draft curriculum."""
    school = await _register_school(client, "-activate")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    curriculum_id = await _upload_curriculum(client, headers)

    r = await client.put(
        f"/api/v1/curriculum/{curriculum_id}/activate",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["curriculum_id"] == curriculum_id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_activate_nonexistent_curriculum_returns_404(client: AsyncClient):
    """Activating a non-existent curriculum returns 404."""
    school = await _register_school(client, "-act404")
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    r = await client.put(
        f"/api/v1/curriculum/{uuid.uuid4()}/activate",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_activate_curriculum_archives_previous(client: AsyncClient):
    """Activating a new curriculum archives the previous active one for same grade/year."""
    school = await _register_school(client, "-archive")
    school_id = school["school_id"]
    headers = {"Authorization": f"Bearer {school['access_token']}"}

    # Upload and activate first curriculum.
    c1_id = await _upload_curriculum(client, headers, grade=9)
    r1 = await client.put(f"/api/v1/curriculum/{c1_id}/activate", headers=headers)
    assert r1.status_code == 200

    # Upload second curriculum for the same grade/year.
    c2_id = await _upload_curriculum(client, headers, grade=9)
    r2 = await client.put(f"/api/v1/curriculum/{c2_id}/activate", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["archived_count"] >= 1


@pytest.mark.asyncio
async def test_activate_curriculum_wrong_school_returns_403(client: AsyncClient):
    """A school_admin cannot activate a curriculum belonging to another school."""
    school_a = await _register_school(client, "-actws-a")
    school_b = await _register_school(client, "-actws-b")
    headers_a = {"Authorization": f"Bearer {school_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {school_b['access_token']}"}

    curriculum_b_id = await _upload_curriculum(client, headers_b, grade=7)

    r = await client.put(
        f"/api/v1/curriculum/{curriculum_b_id}/activate",
        headers=headers_a,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_activate_curriculum_requires_auth(client: AsyncClient):
    """Activate endpoint without JWT returns 403."""
    r = await client.put(f"/api/v1/curriculum/{uuid.uuid4()}/activate")
    assert r.status_code == 403


# ── Curriculum resolver unit tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolver_returns_default_for_student_without_school():
    """Unaffiliated student gets default-{year}-g{grade} curriculum."""
    from src.curriculum.resolver import _resolve_from_db

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    result = await _resolve_from_db(mock_pool, str(uuid.uuid4()), 8, school_id=None)
    assert result == f"default-{year}-g8"


@pytest.mark.asyncio
async def test_resolver_uses_school_curriculum_when_active():
    """Student with school_id gets school's active curriculum."""
    from src.curriculum.resolver import _resolve_from_db

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    school_curriculum_id = str(uuid.uuid4())
    mock_conn.fetchrow = AsyncMock(return_value={
        "curriculum_id": school_curriculum_id,
        "restrict_access": False,
    })
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    result = await _resolve_from_db(mock_pool, str(uuid.uuid4()), 8, school_id=str(uuid.uuid4()))
    assert result == school_curriculum_id


@pytest.mark.asyncio
async def test_resolver_raises_403_for_restricted_unenrolled_student():
    """restrict_access=True + no active enrolment → 403."""
    from fastapi import HTTPException
    from src.curriculum.resolver import _resolve_from_db

    student_id = str(uuid.uuid4())
    school_id = str(uuid.uuid4())

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    # First fetchrow returns an active restricted curriculum.
    # Second fetchrow (enrolment check) returns None (not enrolled).
    mock_conn.fetchrow = AsyncMock(side_effect=[
        {"curriculum_id": str(uuid.uuid4()), "restrict_access": True},
        None,
    ])
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with pytest.raises(HTTPException) as exc_info:
        await _resolve_from_db(mock_pool, student_id, 8, school_id=school_id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "not_enrolled"
