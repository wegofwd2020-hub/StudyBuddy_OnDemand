"""
tests/test_reset_password_ownership_665.py

Only a student's PRIMARY school may reset their password (issue #665).

Venki 2026-08-27 hit "Reset failed. Please try again." resetting
`venky50905@gmail.com`. On the demo that student is enrolled at two schools —
ABC School (their primary) and a second one — and the reset was attempted from
the second.

`reset_student_password` matched on `students.school_id`, so from any school
other than the primary it updated nothing, returned `{}`, and the router raised
a bare 404 that the UI rendered as a generic "try again" for something that can
never succeed.

## Why this is NOT fixed by widening the lookup

The obvious repair — match on `school_enrolments` instead — would open a
cross-school account takeover:

  - the endpoint returns the new plain-text password to the CALLING admin;
  - since #572 a school can attach an existing student by email address alone
    (#648 tracks the bulk path);
  - so "any enrolled school may reset" means: attach by email, reset, read the
    password, and hold that student's single account — including their records
    at their real school.

Credential control therefore stays with the primary school, matching #572's
existing rule that content resolution follows the primary school only. The
defect being fixed is the SILENCE, not the restriction: the other school is now
told which school manages the student's sign-in details.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_GRADE = 8


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Reset School{suffix}",
            "contact_email": f"reset{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _hdr(reg: dict) -> dict:
    return {
        "Authorization": "Bearer "
        + make_teacher_token(
            teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
        )
    }


async def _student_at(client: AsyncClient, primary: str, also: list[str] | None = None) -> str:
    """A student whose PRIMARY school is `primary`, also enrolled at `also`."""
    student_id = str(uuid.uuid4())
    email = f"reset-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale,
                 account_status, school_id, auth_provider)
            VALUES ($1, $2, 'Reset Student', $3, $4, 'en', 'active', $5, 'local')
            """,
            uuid.UUID(student_id),
            f"auth0|reset-{student_id.replace('-', '')}",
            email,
            _GRADE,
            uuid.UUID(primary),
        )
        for school_id in [primary, *(also or [])]:
            await conn.execute(
                """
                INSERT INTO school_enrolments
                    (school_id, student_email, student_id, status, grade)
                VALUES ($1, $2, $3, 'active', $4)
                """,
                uuid.UUID(school_id),
                email,
                uuid.UUID(student_id),
                _GRADE,
            )
    return student_id


async def _reset(client: AsyncClient, school: dict, student_id: str):
    return await client.post(
        f"/api/v1/schools/{school['school_id']}/students/{student_id}/reset-password",
        headers=_hdr(school),
    )


@pytest.mark.asyncio
async def test_the_primary_school_can_reset(client, db_conn):
    """The normal case must keep working."""
    primary = await _school(client, "_primary")
    student = await _student_at(client, primary["school_id"])

    r = await _reset(client, primary, student)
    assert r.status_code == 200, r.text
    assert r.json()["temp_password"], r.json()


@pytest.mark.asyncio
async def test_a_second_school_is_told_who_owns_the_credentials(client, db_conn):
    """The reported case. 409 with a reason, not a bare 404.

    The student IS on this roster, so "not found" was both wrong and
    unactionable — it invited retrying something that cannot succeed here.
    """
    primary = await _school(client, "_owner")
    other = await _school(client, "_other")
    student = await _student_at(client, primary["school_id"], also=[other["school_id"]])

    r = await _reset(client, other, student)
    assert r.status_code == 409, r.text
    # The app's exception handler flattens `detail` onto the top level, so the
    # body is {error, detail, correlation_id} rather than a nested object.
    body = r.json()
    assert body["error"] == "not_primary_school", body
    # Names the school that CAN do it, so the admin knows who to ask.
    assert "Reset School_owner" in body["detail"], body


@pytest.mark.asyncio
async def test_a_second_school_cannot_read_the_students_password(client, db_conn):
    """The takeover this restriction exists to prevent.

    A school can attach an existing student by email alone (#572), and reset
    returns the new plain-text password to the caller. If a non-primary school
    could reset, it would own that student's single cross-school account.
    """
    primary = await _school(client, "_victim")
    attacker = await _school(client, "_attacker")
    student = await _student_at(client, primary["school_id"], also=[attacker["school_id"]])

    r = await _reset(client, attacker, student)
    assert r.status_code != 200, r.text
    assert "temp_password" not in r.text, r.text


@pytest.mark.asyncio
async def test_a_school_the_student_is_not_enrolled_at_still_gets_404(client, db_conn):
    """Unrelated schools must not learn that the student exists at all."""
    primary = await _school(client, "_home")
    stranger = await _school(client, "_stranger")
    student = await _student_at(client, primary["school_id"])

    r = await _reset(client, stranger, student)
    assert r.status_code == 404, r.text
    # Must not name the primary school to a school with no relationship.
    assert "Reset School_home" not in r.text, r.text
