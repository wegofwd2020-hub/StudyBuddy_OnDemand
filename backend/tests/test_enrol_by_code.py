"""
tests/test_enrol_by_code.py

Enrolment by school code (issue #609).

The school portal builds an invite URL from `schools.enrolment_code` and gives
admins a copy button, so schools are actively told to send `/enrol/{code}` links
to students. `POST /school/enrol/confirm` never existed, so every student who
followed one hit a dead end.

Three things this must not become, hence the tests below:
  - a way to bypass the plan's student seat limit
  - a way to silently move a student from one school to another
  - a way to probe which enrolment codes are valid
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Enrol Code School{suffix}",
            "contact_email": f"enrolcode{suffix}@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _enrolment_code(client: AsyncClient, school_id: str) -> str:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetchval(
            "SELECT enrolment_code FROM schools WHERE school_id = $1", uuid.UUID(school_id)
        )


async def _make_student(client: AsyncClient, email: str) -> tuple[str, dict]:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Code Student', $3, 8, 'en', 'active')
        """,
        uuid.UUID(student_id),
        f"auth0|code-{student_id.replace('-', '')}",
        email,
    )
    headers = {"Authorization": f"Bearer {make_student_token(student_id=student_id)}"}
    return student_id, headers


async def _set_subscription(client: AsyncClient, school_id: str, max_students: int) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_subscriptions
                (school_id, plan, status, max_students, max_teachers,
                 stripe_customer_id, stripe_subscription_id)
            VALUES ($1, 'professional', 'active', $2, 10,
                    'cus_test_enrol', 'sub_test_enrol')
            """,
            uuid.UUID(school_id),
            max_students,
        )


@pytest.mark.asyncio
async def test_valid_code_enrols_the_student(client, db_conn):
    """The reported gap: following the invite link actually works."""
    school = await _register_school(client, "_ok")
    code = await _enrolment_code(client, school["school_id"])
    _, headers = await _make_student(client, f"code-ok-{uuid.uuid4().hex[:6]}@example.com")

    r = await client.post("/api/v1/school/enrol/confirm", json={"token": code}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["school_name"] == "Enrol Code School_ok"


@pytest.mark.asyncio
async def test_enrolment_is_recorded_against_the_school(client, db_conn):
    """The student must actually appear on the roster, not just get a nice page."""
    school = await _register_school(client, "_rec")
    school_id = school["school_id"]
    code = await _enrolment_code(client, school_id)
    student_id, headers = await _make_student(client, f"code-rec-{uuid.uuid4().hex[:6]}@example.com")

    r = await client.post("/api/v1/school/enrol/confirm", json={"token": code}, headers=headers)
    assert r.status_code == 200, r.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        enrolled = await conn.fetchval(
            """
            SELECT COUNT(*) FROM school_enrolments
            WHERE school_id = $1 AND student_id = $2 AND status = 'active'
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
        )
        school_on_student = await conn.fetchval(
            "SELECT school_id::text FROM students WHERE student_id = $1", uuid.UUID(student_id)
        )
    assert enrolled == 1
    assert school_on_student == school_id


@pytest.mark.asyncio
async def test_repeating_the_link_is_harmless(client, db_conn):
    """Students re-open links. A second visit must not error or duplicate."""
    school = await _register_school(client, "_again")
    code = await _enrolment_code(client, school["school_id"])
    student_id, headers = await _make_student(
        client, f"code-again-{uuid.uuid4().hex[:6]}@example.com"
    )

    first = await client.post("/api/v1/school/enrol/confirm", json={"token": code}, headers=headers)
    assert first.status_code == 200, first.text
    second = await client.post("/api/v1/school/enrol/confirm", json={"token": code}, headers=headers)
    assert second.status_code == 200, second.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        rows = await conn.fetchval(
            "SELECT COUNT(*) FROM school_enrolments WHERE student_id = $1",
            uuid.UUID(student_id),
        )
    assert rows == 1, "a second visit created a duplicate enrolment"


@pytest.mark.asyncio
async def test_unknown_code_is_refused_without_confirming_anything(client, db_conn):
    """A wrong code must not reveal whether it nearly matched."""
    _, headers = await _make_student(client, f"code-bad-{uuid.uuid4().hex[:6]}@example.com")

    # A real school exists; the code given is wrong. The response must not
    # confirm or deny anything about it.
    school = await _register_school(client, "_secret")
    real_code = await _enrolment_code(client, school["school_id"])

    r = await client.post(
        "/api/v1/school/enrol/confirm", json={"token": "NOPE-9999"}, headers=headers
    )
    assert r.status_code == 404, r.text
    detail = r.json()["detail"]
    assert "Enrol Code School_secret" not in detail, detail
    assert school["school_id"] not in detail, detail
    assert real_code not in detail, detail


@pytest.mark.asyncio
async def test_a_student_already_at_another_school_is_not_moved_silently(client, db_conn):
    """Switching schools is an administrative act, not a link click.

    Silently transferring would detach the student from their existing school's
    roster and curriculum without anyone at either school knowing.
    """
    first_school = await _register_school(client, "_first")
    second_school = await _register_school(client, "_second")
    first_code = await _enrolment_code(client, first_school["school_id"])
    second_code = await _enrolment_code(client, second_school["school_id"])
    student_id, headers = await _make_student(
        client, f"code-move-{uuid.uuid4().hex[:6]}@example.com"
    )

    joined = await client.post(
        "/api/v1/school/enrol/confirm", json={"token": first_code}, headers=headers
    )
    assert joined.status_code == 200, joined.text

    moved = await client.post(
        "/api/v1/school/enrol/confirm", json={"token": second_code}, headers=headers
    )
    assert moved.status_code == 409, moved.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        still = await conn.fetchval(
            "SELECT school_id::text FROM students WHERE student_id = $1", uuid.UUID(student_id)
        )
    assert still == first_school["school_id"], "the student was moved by a link click"


@pytest.mark.asyncio
async def test_seat_limit_is_enforced(client, db_conn):
    """Self-serve enrolment must not become a way around the plan's seat limit."""
    school = await _register_school(client, "_seats")
    school_id = school["school_id"]
    await _set_subscription(client, school_id, max_students=1)
    code = await _enrolment_code(client, school_id)

    _, first_headers = await _make_student(client, f"seat-a-{uuid.uuid4().hex[:6]}@example.com")
    first = await client.post(
        "/api/v1/school/enrol/confirm", json={"token": code}, headers=first_headers
    )
    assert first.status_code == 200, first.text

    _, second_headers = await _make_student(client, f"seat-b-{uuid.uuid4().hex[:6]}@example.com")
    second = await client.post(
        "/api/v1/school/enrol/confirm", json={"token": code}, headers=second_headers
    )
    assert second.status_code == 402, second.text


@pytest.mark.asyncio
async def test_requires_a_signed_in_student(client, db_conn):
    """The link only makes sense for someone with an account."""
    r = await client.post("/api/v1/school/enrol/confirm", json={"token": "ANY-CODE"})
    assert r.status_code == 401
