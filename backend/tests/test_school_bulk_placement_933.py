"""
tests/test_school_bulk_placement_933.py

Issue #933 PR 2 — post-enrolment placement of enrolled students.

Coverage:
  POST /api/v1/schools/{id}/students/placement — grade, stream, classroom and teacher

Fixtures are committed through the pool because the HTTP client runs on its own
connection and cannot see uncommitted rows.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"
_YEAR = 2026


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register_school(client: AsyncClient, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Bulk School {uuid.uuid4().hex[:6]}",
            "contact_email": email,
            "country": "CA",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_stream(client: AsyncClient, *, grade: int) -> dict:
    code = f"b{uuid.uuid4().hex[:8]}"
    curriculum_id = f"bulk-{code}-g{grade}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO streams (code, display_name, is_system, is_archived)
            VALUES ($1, $2, FALSE, FALSE)
            """,
            code,
            f"Stream {code}",
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, is_default, stream_code)
            VALUES ($1, $2, $3, $4, 'platform', FALSE, $5)
            """,
            curriculum_id,
            f"Stream {code}",
            grade,
            _YEAR,
            code,
        )
    return {"code": code, "curriculum_id": curriculum_id}


async def _seed_grade_default(client: AsyncClient, *, grade: int) -> str:
    curriculum_id = f"bulk-default-{uuid.uuid4().hex[:8]}-g{grade}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Grade default', $2, $3, 'platform', TRUE)
            """,
            curriculum_id,
            grade,
            _YEAR,
        )
    return curriculum_id


async def _seed_teacher(client: AsyncClient, school_id: str, grades: list[int]) -> str:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, name, email, role, account_status)
            VALUES ($1, $2, $3, 'Bulk Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"auth0|bulk-{teacher_id.replace('-', '')}",
            f"bulk-{teacher_id[:8]}@example.com",
        )
        for g in grades:
            await conn.execute(
                """
                INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
                """,
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                g,
            )
    return teacher_id


async def _classroom(
    client: AsyncClient, school_id: str, token: str, grade: int, teacher_id: str | None
) -> str:
    body: dict = {"name": f"Room {uuid.uuid4().hex[:6]}", "grade": grade}
    if teacher_id is not None:
        body["teacher_id"] = teacher_id
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms", json=body, headers=_auth(token)
    )
    assert r.status_code == 201, r.text
    return r.json()["classroom_id"]


async def _assign_package(
    client: AsyncClient, school_id: str, token: str, classroom_id: str, curriculum_id: str
) -> None:
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id, "sort_order": 0},
        headers=_auth(token),
    )
    assert r.status_code == 204, r.text


async def _provision(client: AsyncClient, school_id: str, token: str, grade: int) -> str:
    r = await client.post(
        f"/api/v1/schools/{school_id}/students",
        json={
            "name": "Bulk Student",
            "email": f"bulk-{uuid.uuid4().hex[:8]}@example.com",
            "grade": grade,
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["student_id"]


async def _place(client: AsyncClient, school_id: str, token: str, body: dict):
    return await client.post(
        f"/api/v1/schools/{school_id}/students/placement",
        json=body,
        headers=_auth(token),
    )


async def _classroom_student_ids(client: AsyncClient, classroom_id: str) -> set[str]:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        rows = await conn.fetch(
            "SELECT student_id::text AS sid FROM classroom_students WHERE classroom_id = $1",
            uuid.UUID(classroom_id),
        )
    return {r["sid"] for r in rows}


async def _classroom_package_ids(client: AsyncClient, classroom_id: str) -> set[str]:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        rows = await conn.fetch(
            "SELECT curriculum_id FROM classroom_packages WHERE classroom_id = $1",
            uuid.UUID(classroom_id),
        )
    return {r["curriculum_id"] for r in rows}


@pytest.fixture
def no_welcome_email():
    with patch("src.email.service.send_welcome_student_email", new=AsyncMock()):
        yield


@pytest.mark.asyncio
async def test_places_every_student_with_stream_and_classroom_teacher(
    client: AsyncClient, no_welcome_email
):
    data = await _register_school(client, f"s933p2a-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    teacher_id = await _seed_teacher(client, school_id, grades=[9])
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=teacher_id)
    s1 = await _provision(client, school_id, token, grade=9)
    s2 = await _provision(client, school_id, token, grade=9)

    r = await _place(
        client,
        school_id,
        token,
        {
            "student_ids": [s1, s2],
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["placed"] == 2
    assert body["failed"] == 0
    assert {x["status"] for x in body["results"]} == {"placed"}
    assert await _classroom_student_ids(client, classroom_id) == {s1, s2}
    assert stream["curriculum_id"] in await _classroom_package_ids(client, classroom_id)


@pytest.mark.asyncio
async def test_teacher_not_assigned_to_grade_fails_every_student(
    client: AsyncClient, no_welcome_email
):
    data = await _register_school(client, f"s933p2b-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    teacher_id = await _seed_teacher(client, school_id, grades=[10])
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=teacher_id)
    s1 = await _provision(client, school_id, token, grade=9)

    r = await _place(
        client,
        school_id,
        token,
        {"student_ids": [s1], "grade": 9, "classroom_id": classroom_id},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["placed"] == 0
    assert body["failed"] == 1
    assert "teacher is not assigned to grade 9" in body["results"][0]["reason"]
    assert await _classroom_student_ids(client, classroom_id) == set()


@pytest.mark.asyncio
async def test_classroom_without_teacher_fails_every_student(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933p2c-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=None)
    s1 = await _provision(client, school_id, token, grade=9)
    s2 = await _provision(client, school_id, token, grade=9)

    r = await _place(
        client,
        school_id,
        token,
        {"student_ids": [s1, s2], "grade": 9, "classroom_id": classroom_id},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["placed"] == 0
    assert body["failed"] == 2
    assert {x["reason"] for x in body["results"]} == {"classroom has no teacher"}
    assert await _classroom_student_ids(client, classroom_id) == set()


async def test_failed_stream_placement_leaves_no_package(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933p2e-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=None)
    s1 = await _provision(client, school_id, token, grade=9)

    r = await _place(
        client,
        school_id,
        token,
        {
            "student_ids": [s1],
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 200, r.text
    assert r.json()["placed"] == 0
    assert await _classroom_package_ids(client, classroom_id) == set()


@pytest.mark.asyncio
async def test_unenrolled_student_fails_and_others_still_place(
    client: AsyncClient, no_welcome_email
):
    data = await _register_school(client, f"s933p2d-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    teacher_id = await _seed_teacher(client, school_id, grades=[9])
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=teacher_id)
    enrolled = await _provision(client, school_id, token, grade=9)
    stranger = str(uuid.uuid4())

    r = await _place(
        client,
        school_id,
        token,
        {"student_ids": [stranger, enrolled], "grade": 9, "classroom_id": classroom_id},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["placed"] == 1
    assert body["failed"] == 1
    by_id = {x["student_id"]: x for x in body["results"]}
    assert by_id[stranger]["status"] == "failed"
    assert by_id[stranger]["reason"] == "student is not enrolled in this school"
    assert by_id[enrolled]["status"] == "placed"
    assert await _classroom_student_ids(client, classroom_id) == {enrolled}


@pytest.mark.asyncio
async def test_refused_stream_returns_409_and_places_nobody(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933p2e-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    default_id = await _seed_grade_default(client, grade=9)
    teacher_id = await _seed_teacher(client, school_id, grades=[9])
    classroom_id = await _classroom(client, school_id, token, grade=9, teacher_id=teacher_id)
    await _assign_package(client, school_id, token, classroom_id, default_id)
    s1 = await _provision(client, school_id, token, grade=9)

    r = await _place(
        client,
        school_id,
        token,
        {
            "student_ids": [s1],
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 409, r.text
    assert r.json()["error"] == "placement_conflict"
    assert await _classroom_student_ids(client, classroom_id) == set()
    assert stream["curriculum_id"] not in await _classroom_package_ids(client, classroom_id)


@pytest.mark.asyncio
async def test_non_admin_teacher_is_forbidden(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933p2f-{uuid.uuid4().hex[:6]}@example.com")
    school_id = data["school_id"]
    teacher_id = await _seed_teacher(client, school_id, grades=[9])
    classroom_id = await _classroom(
        client, school_id, data["access_token"], grade=9, teacher_id=teacher_id
    )
    s1 = await _provision(client, school_id, data["access_token"], grade=9)
    plain_token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role="teacher")

    r = await _place(
        client,
        school_id,
        plain_token,
        {"student_ids": [s1], "grade": 9, "classroom_id": classroom_id},
    )

    assert r.status_code == 403, r.text
    assert await _classroom_student_ids(client, classroom_id) == set()
