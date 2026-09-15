"""
tests/test_reports_grade_scoping.py

Teacher grade scoping on report endpoints (issue #576).

Verified live on the demo 2026-08-11: a `role: "teacher"` account assigned only
Grade 8 could read a Grade 10 student's full report card — unit names, quiz
attempts, best scores, pass/fail — by changing a query parameter. Every reports
endpoint was gated by `_check_school()` alone, which confirms the school matches
and nothing else.

The product already models this: `teacher_grade_assignments` (migration 0023),
and roster upload already refuses to link a student to a teacher not assigned to
that grade (`enrolment_service.py:75-90`). The reports layer never wired the
same check in. These tests hold it to the model the rest of the product uses.

Two deliberate rules encoded here:
  - `school_admin` keeps full visibility — it is a teacher superset (ADR-005)
  - a teacher with NO grade assignments has no cohort, so sees no students
    rather than all of them
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Scoping School{suffix}",
            "contact_email": f"scoping{suffix}@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_teacher(
    client: AsyncClient, school_id: str, grades: list[int], role: str = "teacher"
) -> dict:
    """Create a teacher with explicit grade assignments and return auth headers."""
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider, name, email,
                 role, account_status)
            VALUES ($1, $2, $3, 'local', 'Scoped Teacher', $4, $5, 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"local:{teacher_id}",
            f"scoped-{teacher_id[:8]}@example.com",
            role,
        )
        for grade in grades:
            await conn.execute(
                """
                INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                VALUES ($1, $2, $3)
                """,
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                grade,
            )
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role=role)
    return {"Authorization": f"Bearer {token}"}


async def _enrol_student(client: AsyncClient, school_id: str, grade: int) -> str:
    """Create an enrolled student in a given grade; returns student_id."""
    student_id = str(uuid.uuid4())
    email = f"scoped-student-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Scoped Student', $3, $4, 'en', 'active', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|scoped-{student_id.replace('-', '')}",
            email,
            grade,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', $4)
            """,
            uuid.UUID(school_id),
            email,
            uuid.UUID(student_id),
            grade,
        )
    return student_id


# ── The reported exposure ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_cannot_read_a_student_outside_their_grades(client, db_conn):
    """The exact case verified on the demo: Grade-8 teacher, Grade-10 student."""
    school = await _register_school(client, "_leak")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[8])
    grade10_student = await _enrol_student(client, school_id, grade=10)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{grade10_student}", headers=headers
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_teacher_can_read_a_student_in_their_own_grade(client, db_conn):
    """Scoping must not break the legitimate case."""
    school = await _register_school(client, "_ok")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[8])
    grade8_student = await _enrol_student(client, school_id, grade=8)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{grade8_student}", headers=headers
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_roster_rejects_a_grade_the_teacher_does_not_teach(client, db_conn):
    """`?grade=10` from a Grade-8 teacher was the one-parameter exploit."""
    school = await _register_school(client, "_roster")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[8])
    await _enrol_student(client, school_id, grade=10)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/roster", headers=headers, params={"grade": 10}
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_unfiltered_roster_shows_only_the_teachers_own_grades(client, db_conn):
    """With no filter, a teacher must still not see other grades' students.

    Rejecting only the explicit `?grade=` would leave the wider door open.
    """
    school = await _register_school(client, "_mixed")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[8])
    mine = await _enrol_student(client, school_id, grade=8)
    theirs = await _enrol_student(client, school_id, grade=10)

    r = await client.get(f"/api/v1/reports/school/{school_id}/roster", headers=headers)
    assert r.status_code == 200, r.text
    ids = {row["student_id"] for row in r.json()["students"]}
    assert mine in ids
    assert theirs not in ids, "a Grade-10 student appeared in a Grade-8 teacher's roster"


# ── The rules that keep this usable ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_school_admin_keeps_full_visibility(client, db_conn):
    """school_admin is a teacher superset (ADR-005) — scoping must not gate them."""
    school = await _register_school(client, "_admin")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[8], role="school_admin")
    grade10_student = await _enrol_student(client, school_id, grade=10)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{grade10_student}", headers=headers
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_teacher_with_no_assignments_sees_no_students(client, db_conn):
    """No grades assigned means no cohort — so no students, not every student.

    This is a deliberate behaviour change: such a teacher previously saw the
    whole school.
    """
    school = await _register_school(client, "_none")
    school_id = school["school_id"]
    headers = await _make_teacher(client, school_id, grades=[])
    student = await _enrol_student(client, school_id, grade=8)

    roster = await client.get(f"/api/v1/reports/school/{school_id}/roster", headers=headers)
    assert roster.status_code == 200, roster.text
    assert roster.json()["students"] == []

    report = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{student}", headers=headers
    )
    assert report.status_code == 403, report.text


@pytest.mark.asyncio
async def test_cross_school_access_is_still_refused(client, db_conn):
    """The existing school check must survive the new scoping."""
    mine = await _register_school(client, "_mineschool")
    other = await _register_school(client, "_otherschool")
    headers = await _make_teacher(client, mine["school_id"], grades=[8])
    their_student = await _enrol_student(client, other["school_id"], grade=8)

    r = await client.get(
        f"/api/v1/reports/school/{other['school_id']}/student/{their_student}", headers=headers
    )
    assert r.status_code == 403, r.text
