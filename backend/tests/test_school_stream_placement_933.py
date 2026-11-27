"""
tests/test_school_stream_placement_933.py

Issue #933 PR 1 — stream picker on Add Student.

Coverage:
  GET  /api/v1/schools/{id}/streams?grade=N[&classroom_id=]   — selectable streams
  POST /api/v1/schools/{id}/students (classroom_id, stream_code) — atomic placement

Fixtures are committed through the pool (as in test_additive_packages_651.py) because
the HTTP client runs on its own connection and cannot see uncommitted rows.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

_PW = "SecureTestPwd1!"
_YEAR = 2026


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register_school(client: AsyncClient, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Stream School {uuid.uuid4().hex[:6]}",
            "contact_email": email,
            "country": "CA",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_stream(client: AsyncClient, *, grade: int) -> dict:
    """A stream with a platform curriculum at `grade`. Returns code, name, curriculum_id."""
    code = f"s{uuid.uuid4().hex[:8]}"
    name = f"Stream {code}"
    curriculum_id = f"stream-{code}-g{grade}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO streams (code, display_name, is_system, is_archived)
            VALUES ($1, $2, FALSE, FALSE)
            """,
            code,
            name,
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, is_default, stream_code)
            VALUES ($1, $2, $3, $4, 'platform', FALSE, $5)
            """,
            curriculum_id,
            name,
            grade,
            _YEAR,
            code,
        )
    return {"code": code, "name": name, "curriculum_id": curriculum_id}


async def _seed_grade_default(client: AsyncClient, *, grade: int) -> str:
    """A platform curriculum with no stream: the grade default a classroom may hold."""
    curriculum_id = f"default-{uuid.uuid4().hex[:8]}-g{grade}"
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


async def _classroom(client: AsyncClient, school_id: str, token: str, grade: int) -> str:
    r = await client.post(
        f"/api/v1/schools/{school_id}/classrooms",
        json={"name": f"Room {uuid.uuid4().hex[:6]}", "grade": grade},
        headers=_auth(token),
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


async def _stream_options(
    client: AsyncClient, school_id: str, token: str, grade: int, classroom_id: str | None = None
) -> dict[str, dict]:
    params = {"grade": grade}
    if classroom_id is not None:
        params["classroom_id"] = classroom_id
    r = await client.get(
        f"/api/v1/schools/{school_id}/streams", params=params, headers=_auth(token)
    )
    assert r.status_code == 200, r.text
    return {s["stream_code"]: s for s in r.json()["streams"]}


async def _provision(
    client: AsyncClient, school_id: str, token: str, body: dict
):
    return await client.post(
        f"/api/v1/schools/{school_id}/students",
        json=body,
        headers=_auth(token),
    )


async def _count_students(client: AsyncClient, email: str) -> int:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetchval("SELECT COUNT(*) FROM students WHERE email = $1", email)


async def _classroom_student_ids(client: AsyncClient, classroom_id: str) -> set[str]:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        rows = await conn.fetch(
            "SELECT student_id::text AS sid FROM classroom_students WHERE classroom_id = $1",
            uuid.UUID(classroom_id),
        )
    return {r["sid"] for r in rows}


@pytest.fixture
def no_welcome_email():
    with patch("src.email.service.send_welcome_student_email", new=AsyncMock()):
        yield


@pytest.mark.asyncio
async def test_streams_all_selectable_without_classroom(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933a-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)

    options = await _stream_options(client, school_id, token, grade=9)

    assert options[stream["code"]]["selectable"] is True
    assert options[stream["code"]]["reason"] is None
    assert options[stream["code"]]["display_name"] == stream["name"]


@pytest.mark.asyncio
async def test_grade_default_in_classroom_blocks_every_stream(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933b-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    default_id = await _seed_grade_default(client, grade=9)
    classroom_id = await _classroom(client, school_id, token, grade=9)
    await _assign_package(client, school_id, token, classroom_id, default_id)

    options = await _stream_options(client, school_id, token, grade=9, classroom_id=classroom_id)

    assert options[stream["code"]]["selectable"] is False
    assert "grade default" in options[stream["code"]]["reason"]


@pytest.mark.asyncio
async def test_stream_package_restricts_classroom_to_that_stream(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933c-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    serving = await _seed_stream(client, grade=9)
    other = await _seed_stream(client, grade=9)
    classroom_id = await _classroom(client, school_id, token, grade=9)
    await _assign_package(client, school_id, token, classroom_id, serving["curriculum_id"])

    options = await _stream_options(client, school_id, token, grade=9, classroom_id=classroom_id)

    assert options[serving["code"]]["selectable"] is True
    assert options[other["code"]]["selectable"] is False
    assert f"serves {serving['name']}" in options[other["code"]]["reason"]


@pytest.mark.asyncio
async def test_add_student_with_stream_places_them_in_classroom(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933d-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    classroom_id = await _classroom(client, school_id, token, grade=9)
    email = f"placed-{uuid.uuid4().hex[:6]}@example.com"

    r = await _provision(
        client,
        school_id,
        token,
        {
            "name": "Placed Student",
            "email": email,
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 201, r.text
    student_id = r.json()["student_id"]
    assert student_id in await _classroom_student_ids(client, classroom_id)
    options = await _stream_options(client, school_id, token, grade=9, classroom_id=classroom_id)
    assert options[stream["code"]]["selectable"] is True


@pytest.mark.asyncio
async def test_stream_into_grade_default_classroom_is_refused_and_creates_nothing(
    client: AsyncClient, no_welcome_email
):
    data = await _register_school(client, f"s933e-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)
    default_id = await _seed_grade_default(client, grade=9)
    classroom_id = await _classroom(client, school_id, token, grade=9)
    await _assign_package(client, school_id, token, classroom_id, default_id)
    email = f"refused-{uuid.uuid4().hex[:6]}@example.com"

    r = await _provision(
        client,
        school_id,
        token,
        {
            "name": "Refused Student",
            "email": email,
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 409, r.text
    assert r.json()["error"] == "placement_conflict"
    assert await _count_students(client, email) == 0


@pytest.mark.asyncio
async def test_stream_without_classroom_is_rejected(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933f-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    stream = await _seed_stream(client, grade=9)

    r = await _provision(
        client,
        school_id,
        token,
        {
            "name": "No Room",
            "email": f"noroom-{uuid.uuid4().hex[:6]}@example.com",
            "grade": 9,
            "stream_code": stream["code"],
        },
    )

    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_unknown_stream_is_rejected(client: AsyncClient, no_welcome_email):
    data = await _register_school(client, f"s933g-{uuid.uuid4().hex[:6]}@example.com")
    token, school_id = data["access_token"], data["school_id"]
    classroom_id = await _classroom(client, school_id, token, grade=9)
    email = f"unknown-{uuid.uuid4().hex[:6]}@example.com"

    r = await _provision(
        client,
        school_id,
        token,
        {
            "name": "Unknown Stream",
            "email": email,
            "grade": 9,
            "classroom_id": classroom_id,
            "stream_code": "no-such-stream",
        },
    )

    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invalid_stream"
    assert await _count_students(client, email) == 0
