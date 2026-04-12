"""
tests/test_setup_checklist.py

Layer 1.5 — Setup checklist endpoint.

Coverage:
  GET /api/v1/schools/{id}/setup-status — returns counts + setup_complete flag

Scenarios:
  - Requires school_admin JWT (403 for plain teacher)
  - Returns zeros and setup_complete=false for a fresh school
  - teacher_count increments after provisioning a teacher
  - student_count increments after provisioning a student
  - classroom_count increments after creating a classroom
  - curriculum_assigned becomes true after assigning a package to a classroom
  - setup_complete becomes true when all four steps are done
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post("/api/v1/schools/register", json={
        "school_name": name,
        "contact_email": email,
        "country": "CA",
        "password": _PW,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _provision_teacher(client: AsyncClient, school_id: str, token: str, email: str) -> dict:
    with patch("src.email.service.send_welcome_teacher_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Test Teacher", "email": email},
            headers=_auth(token),
        )
    assert r.status_code == 201, r.text
    return r.json()


async def _provision_student(client: AsyncClient, school_id: str, token: str, email: str) -> dict:
    with patch("src.email.service.send_welcome_student_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": "Test Student", "email": email, "grade": 8},
            headers=_auth(token),
        )
    assert r.status_code == 201, r.text
    return r.json()


async def _create_classroom(client: AsyncClient, school_id: str, token: str) -> dict:
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms",
        json={"name": "Grade 8A", "grade": 8},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _assign_package(
    client: AsyncClient, school_id: str, classroom_id: str, token: str
) -> None:
    curriculum_id = f"test-{uuid.uuid4().hex[:8]}"
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id, "display_order": 1},
        headers=_auth(token),
    )
    assert r.status_code in (201, 204), r.text


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_setup_status_requires_auth(client: AsyncClient):
    """GET setup-status without a JWT returns 401."""
    r = await client.get("/api/v1/schools/00000000-0000-0000-0000-000000000001/setup-status")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_setup_status_requires_school_admin(client: AsyncClient):
    """A plain teacher (non-admin) JWT returns 403."""
    school_id = "00000000-0000-0000-0000-000000000002"
    teacher_token = make_teacher_token(
        teacher_id="00000000-0000-0000-0000-000000000010",
        school_id=school_id,
        role="teacher",
    )
    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(teacher_token),
    )
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


@pytest.mark.asyncio
async def test_setup_status_fresh_school_is_zero(client: AsyncClient):
    """A newly registered school has all counts at zero and setup_complete=false."""
    data = await _register(client, "Fresh School", "fresh@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["teacher_count"] == 0
    assert body["student_count"] == 0
    assert body["classroom_count"] == 0
    assert body["curriculum_assigned"] is False
    assert body["setup_complete"] is False


@pytest.mark.asyncio
async def test_setup_status_increments_on_teacher_provision(client: AsyncClient):
    """After provisioning a teacher, teacher_count becomes 1."""
    data = await _register(client, "Teacher Count School", "tcteacher@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    await _provision_teacher(client, school_id, token, "t1@checklist.example.com")

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["teacher_count"] == 1
    assert body["setup_complete"] is False


@pytest.mark.asyncio
async def test_setup_status_increments_on_student_provision(client: AsyncClient):
    """After provisioning a student, student_count becomes 1."""
    data = await _register(client, "Student Count School", "tsstudent@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    await _provision_student(client, school_id, token, "s1@checklist.example.com")

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["student_count"] == 1
    assert body["setup_complete"] is False


@pytest.mark.asyncio
async def test_setup_status_increments_on_classroom_create(client: AsyncClient):
    """After creating a classroom, classroom_count becomes 1."""
    data = await _register(client, "Classroom Count School", "tcclassroom@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    await _create_classroom(client, school_id, token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["classroom_count"] == 1
    assert body["setup_complete"] is False


@pytest.mark.asyncio
async def test_setup_status_curriculum_assigned_after_package(client: AsyncClient):
    """After assigning a package to a classroom, curriculum_assigned becomes true."""
    data = await _register(client, "Package School", "pkgassign@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    classroom = await _create_classroom(client, school_id, token)
    await _assign_package(client, school_id, classroom["classroom_id"], token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["curriculum_assigned"] is True
    # setup_complete still false — no teacher or student yet
    assert body["setup_complete"] is False


@pytest.mark.asyncio
async def test_setup_status_complete_when_all_steps_done(client: AsyncClient):
    """setup_complete becomes true only when all four steps are satisfied."""
    data = await _register(client, "Full Setup School", "fullsetup@checklist.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    await _provision_teacher(client, school_id, token, "ft1@checklist.example.com")
    await _provision_student(client, school_id, token, "fs1@checklist.example.com")
    classroom = await _create_classroom(client, school_id, token)
    await _assign_package(client, school_id, classroom["classroom_id"], token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/setup-status",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["teacher_count"] >= 1
    assert body["student_count"] >= 1
    assert body["classroom_count"] >= 1
    assert body["curriculum_assigned"] is True
    assert body["setup_complete"] is True
