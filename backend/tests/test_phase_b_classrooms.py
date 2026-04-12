"""
tests/test_phase_b_classrooms.py

Phase B — Classroom lifecycle tests.

Coverage:
  POST   /api/v1/schools/{id}/classrooms                               — create
  GET    /api/v1/schools/{id}/classrooms                               — list
  GET    /api/v1/schools/{id}/classrooms/{cid}                         — detail
  PATCH  /api/v1/schools/{id}/classrooms/{cid}                         — update
  POST   /api/v1/schools/{id}/classrooms/{cid}/packages                — assign package
  PATCH  /api/v1/schools/{id}/classrooms/{cid}/packages/{pid}          — reorder package
  DELETE /api/v1/schools/{id}/classrooms/{cid}/packages/{pid}          — remove package
  POST   /api/v1/schools/{id}/classrooms/{cid}/students                — assign student
  DELETE /api/v1/schools/{id}/classrooms/{cid}/students/{sid}          — remove student
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient, name: str, email: str) -> dict:
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


async def _create_classroom(
    client: AsyncClient,
    school_id: str,
    token: str,
    name: str = "Grade 8 — Section A",
    grade: int | None = 8,
) -> dict:
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms",
        json={"name": name, "grade": grade},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _provision_student(client: AsyncClient, school_id: str, token: str, email: str) -> dict:
    from unittest.mock import patch, AsyncMock
    with patch("src.email.service.send_welcome_student_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": "Test Student", "email": email, "grade": 8},
            headers=_auth(token),
        )
    assert r.status_code == 201, r.text
    return r.json()


def _fake_curriculum_id() -> str:
    """
    Return a fabricated curriculum_id string.

    classroom_packages.curriculum_id has no FK to curricula (TEXT PK with platform
    IDs like "default-2026-g8" that may not exist in the test DB). Application logic
    is the enforcement layer; tests use arbitrary TEXT IDs.
    """
    return f"test-cls-{uuid.uuid4().hex[:8]}"


# ── CREATE ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_classroom_returns_201(client: AsyncClient):
    """School admin can create a classroom."""
    data = await _register_school(client, "Create School", "create-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    room = await _create_classroom(client, school_id, token)
    assert room["name"] == "Grade 8 — Section A"
    assert room["grade"] == 8
    assert room["status"] == "active"
    assert room["school_id"] == school_id


@pytest.mark.asyncio
async def test_create_classroom_no_grade(client: AsyncClient):
    """A classroom with no grade (cross-grade) is valid."""
    data = await _register_school(client, "NoGrade School", "nograde-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms",
        json={"name": "Mixed Cohort"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    assert r.json()["grade"] is None


@pytest.mark.asyncio
async def test_create_classroom_wrong_school_returns_403(client: AsyncClient):
    """A teacher cannot create a classroom in a different school."""
    data = await _register_school(client, "Own School", "own-cls@classroom.example.com")
    token = data["access_token"]
    other_school_id = str(uuid.uuid4())

    r = await client.post(
        f"/api/v1/schools/{other_school_id}/classrooms",
        json={"name": "Sneaky Classroom"},
        headers=_auth(token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_classroom_invalid_grade_returns_422(client: AsyncClient):
    """Grade outside 1–12 is rejected."""
    data = await _register_school(client, "Grade School", "grade-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms",
        json={"name": "Bad Grade", "grade": 99},
        headers=_auth(token),
    )
    assert r.status_code == 422


# ── LIST ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_classrooms_empty(client: AsyncClient):
    """A new school has an empty classroom list."""
    data = await _register_school(client, "Empty School", "empty-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    r = await client.get(f"/api/v1/schools/{school_id}/classrooms", headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_classrooms_returns_all(client: AsyncClient):
    """All classrooms for the school are returned."""
    data = await _register_school(client, "List School", "list-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    await _create_classroom(client, school_id, token, "Room A", 7)
    await _create_classroom(client, school_id, token, "Room B", 8)

    r = await client.get(f"/api/v1/schools/{school_id}/classrooms", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_classrooms_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/schools/some-school/classrooms")
    assert r.status_code == 401


# ── DETAIL ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_classroom_detail(client: AsyncClient):
    """Detail endpoint returns classroom with empty packages and students."""
    data = await _register_school(client, "Detail School", "detail-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert r.status_code == 200
    detail = r.json()
    assert detail["classroom_id"] == classroom_id
    assert detail["packages"] == []
    assert detail["students"] == []


@pytest.mark.asyncio
async def test_get_classroom_detail_not_found(client: AsyncClient):
    data = await _register_school(client, "Miss School", "miss-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{uuid.uuid4()}",
        headers=_auth(token),
    )
    assert r.status_code == 404


# ── UPDATE ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_classroom_name(client: AsyncClient):
    """PATCH can rename a classroom."""
    data = await _register_school(client, "Update School", "update-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    r = await client.patch(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        json={"name": "Grade 9 — Section B"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Grade 9 — Section B"


@pytest.mark.asyncio
async def test_archive_classroom(client: AsyncClient):
    """Status can be set to 'archived'."""
    data = await _register_school(client, "Archive School", "archive-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    r = await client.patch(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        json={"status": "archived"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_update_classroom_invalid_status_returns_422(client: AsyncClient):
    data = await _register_school(client, "BadStat School", "badstat-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    r = await client.patch(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        json={"status": "deleted"},
        headers=_auth(token),
    )
    assert r.status_code == 422


# ── PACKAGES ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_package_to_classroom(client: AsyncClient):
    """A curriculum package can be assigned to a classroom."""
    data = await _register_school(client, "Pkg School", "pkg-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    curriculum_id = _fake_curriculum_id()

    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id, "sort_order": 0},
        headers=_auth(token),
    )
    assert r.status_code == 204

    # Verify it appears in the detail view.
    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    pkgs = detail.json()["packages"]
    assert len(pkgs) == 1
    assert pkgs[0]["curriculum_id"] == curriculum_id


@pytest.mark.asyncio
async def test_assign_package_idempotent(client: AsyncClient):
    """Assigning the same package twice is idempotent — no duplicate rows."""
    data = await _register_school(client, "IdempPkg School", "idemppkg-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]
    curriculum_id = _fake_curriculum_id()

    await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id},
        headers=_auth(token),
    )
    await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id},
        headers=_auth(token),
    )

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert len(detail.json()["packages"]) == 1


@pytest.mark.asyncio
async def test_reorder_package_in_classroom(client: AsyncClient):
    """sort_order of a package can be updated."""
    data = await _register_school(client, "Reorder School", "reorder-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]
    curriculum_id = _fake_curriculum_id()

    await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id, "sort_order": 0},
        headers=_auth(token),
    )

    r = await client.patch(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages/{curriculum_id}",
        json={"sort_order": 5},
        headers=_auth(token),
    )
    assert r.status_code == 204

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert detail.json()["packages"][0]["sort_order"] == 5


@pytest.mark.asyncio
async def test_remove_package_from_classroom(client: AsyncClient):
    """A package can be removed from a classroom."""
    data = await _register_school(client, "RmPkg School", "rmpkg-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]
    curriculum_id = _fake_curriculum_id()

    await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id},
        headers=_auth(token),
    )

    r = await client.delete(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages/{curriculum_id}",
        headers=_auth(token),
    )
    assert r.status_code == 204

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert detail.json()["packages"] == []


# ── STUDENTS ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_student_to_classroom(client: AsyncClient):
    """A provisioned student can be assigned to a classroom."""
    from unittest.mock import patch, AsyncMock

    data = await _register_school(client, "Stu School", "stu-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]

    student = await _provision_student(
        client, school_id, token, "stu-assign@classroom.example.com"
    )
    student_id = student["student_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/students",
        json={"student_id": student_id},
        headers=_auth(token),
    )
    assert r.status_code == 204

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    students = detail.json()["students"]
    assert len(students) == 1
    assert students[0]["student_id"] == student_id


@pytest.mark.asyncio
async def test_assign_student_to_classroom_idempotent(client: AsyncClient):
    """Assigning the same student twice creates only one membership row."""
    from unittest.mock import patch, AsyncMock

    data = await _register_school(client, "IdemStu School", "idemstu-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]
    student = await _provision_student(
        client, school_id, token, "idemstu@classroom.example.com"
    )
    student_id = student["student_id"]

    for _ in range(2):
        await client.post(
            f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/students",
            json={"student_id": student_id},
            headers=_auth(token),
        )

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert len(detail.json()["students"]) == 1


@pytest.mark.asyncio
async def test_student_may_be_in_multiple_classrooms(client: AsyncClient):
    """
    A student can belong to more than one classroom (Q17 — temporal reassignment).
    Both memberships coexist simultaneously.
    """
    from unittest.mock import patch, AsyncMock

    data = await _register_school(client, "Multi School", "multi-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]

    room_a = await _create_classroom(client, school_id, token, "Room A")
    room_b = await _create_classroom(client, school_id, token, "Room B")
    student = await _provision_student(
        client, school_id, token, "multiroom@classroom.example.com"
    )
    student_id = student["student_id"]

    for cid in [room_a["classroom_id"], room_b["classroom_id"]]:
        r = await client.post(
            f"/api/v1/schools/{school_id}/classrooms/{cid}/students",
            json={"student_id": student_id},
            headers=_auth(token),
        )
        assert r.status_code == 204

    for room in [room_a, room_b]:
        detail = await client.get(
            f"/api/v1/schools/{school_id}/classrooms/{room['classroom_id']}",
            headers=_auth(token),
        )
        assert any(s["student_id"] == student_id for s in detail.json()["students"])


@pytest.mark.asyncio
async def test_assign_student_from_other_school_returns_404(client: AsyncClient):
    """Student must belong to the same school — cross-school assignment is rejected."""
    school_a = await _register_school(client, "School A", "schoola-cls@classroom.example.com")
    school_b = await _register_school(client, "School B", "schoolb-cls@classroom.example.com")

    token_a = school_a["access_token"]
    school_id_a = school_a["school_id"]
    room_a = await _create_classroom(client, school_id_a, token_a)

    from unittest.mock import patch, AsyncMock
    student_b = await _provision_student(
        client, school_b["school_id"], school_b["access_token"],
        "foreign-stu@classroom.example.com"
    )

    r = await client.post(
        f"/api/v1/schools/{school_id_a}/classrooms/{room_a['classroom_id']}/students",
        json={"student_id": student_b["student_id"]},
        headers=_auth(token_a),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_student_from_classroom(client: AsyncClient):
    """A student can be removed from a classroom."""
    from unittest.mock import patch, AsyncMock

    data = await _register_school(client, "RmStu School", "rmstu-cls@classroom.example.com")
    token = data["access_token"]
    school_id = data["school_id"]
    room = await _create_classroom(client, school_id, token)
    classroom_id = room["classroom_id"]
    student = await _provision_student(
        client, school_id, token, "rmstu@classroom.example.com"
    )
    student_id = student["student_id"]

    await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/students",
        json={"student_id": student_id},
        headers=_auth(token),
    )

    r = await client.delete(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/students/{student_id}",
        headers=_auth(token),
    )
    assert r.status_code == 204

    detail = await client.get(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}",
        headers=_auth(token),
    )
    assert detail.json()["students"] == []
