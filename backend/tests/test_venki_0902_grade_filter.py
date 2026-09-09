"""
tests/test_venki_0902_grade_filter.py

The grade filter on the Unit Performance report (Venki, 2 Sep):

    "Can we include filter option for the User to select for which Grade they
     are looking this report. You can default to all to start with."

Three things have to hold at once, and they pull in different directions:

  1. Default is ALL grades — adding a filter must not quietly narrow the
     report for someone who never touches it.
  2. Selecting a grade narrows the ROWS, the counts, and the catalog together.
     Narrowing the rows but not the catalog would list every other grade's
     units as "no activity" — the filter would manufacture coverage gaps.
  3. Selecting a grade must NOT narrow the PICKER. Options derived from the
     filtered result collapse to the one selected option and cannot be widened
     again without a page reload, which is the classic way a server-side filter
     traps the person using it.

Plus the rule that outranks all three: this is a filter WITHIN an entitlement,
never a way around one. #576 established that a teacher sees their own grades;
a `?grade=` naming someone else's must be refused, not ignored.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import get_curriculum_health
from tests.helpers.token_factory import make_teacher_token


async def _school(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Grade Filter School",
            "contact_email": f"gradefilter{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _curriculum(client: AsyncClient, grade: int, unit_id: str) -> str:
    """A school-owned curriculum, so these units cannot collide with the
    platform defaults that other suites count."""
    cid = f"gf-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Grade Filter Curriculum', $2, 2026, 'platform', FALSE)
            """,
            cid,
            grade,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, $3, $4, $4, 0)
            """,
            unit_id,
            cid,
            f"G{grade}-SCI",
            f"Unit {unit_id}",
        )
    return cid


async def _enrol(client: AsyncClient, school_id: str, grade: int) -> str:
    student_id = str(uuid.uuid4())
    email = f"gf-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Grade Filter Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|gf-{student_id.replace('-', '')}",
            email,
            grade,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_id, student_email, grade, status)
            VALUES ($1, $2, $3, $4, 'active')
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
            email,
            grade,
        )
    return student_id


async def _activity(client, student_id: str, unit_id: str, cid: str, grade: int) -> None:
    """A lesson view plus one passing attempt — enough for the unit to tier as
    something other than `no_activity`."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            "INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)"
            " VALUES ($1, $2, $3, 120)",
            uuid.UUID(student_id),
            unit_id,
            cid,
        )
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, $4, $5, 1, TRUE, TRUE, 7, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            grade,
            f"G{grade}-SCI",
        )


async def _two_grade_school(client) -> tuple[str, str, str]:
    """A school with a Grade 5 unit and a Grade 10 unit, each with activity."""
    school_id = await _school(client)
    cid5 = await _curriculum(client, 5, "GF-G5-001")
    cid10 = await _curriculum(client, 10, "GF-G10-001")
    s5 = await _enrol(client, school_id, 5)
    s10 = await _enrol(client, school_id, 10)
    await _activity(client, s5, "GF-G5-001", cid5, 5)
    await _activity(client, s10, "GF-G10-001", cid10, 10)
    return school_id, "GF-G5-001", "GF-G10-001"


def _ids(report: dict) -> set[str]:
    return {u["unit_id"] for u in report["units"]}


# ── Rule 1: the default does not narrow ───────────────────────────────────────


@pytest.mark.asyncio
async def test_no_filter_still_covers_every_grade(client, db_conn):
    """"You can default to all to start with." Adding the parameter must leave
    the unfiltered report exactly as it was."""
    school_id, g5_unit, g10_unit = await _two_grade_school(client)

    report = await get_curriculum_health(db_conn, school_id)

    assert {g5_unit, g10_unit} <= _ids(report)
    assert report["selected_grade"] is None


# ── Rule 2: selecting narrows the rows AND the counts ─────────────────────────


@pytest.mark.asyncio
async def test_filtering_to_one_grade_drops_the_other_grades_units(client, db_conn):
    school_id, g5_unit, g10_unit = await _two_grade_school(client)

    report = await get_curriculum_health(db_conn, school_id, grade=5)

    assert g5_unit in _ids(report)
    assert g10_unit not in _ids(report), "a Grade 10 unit has no place in a Grade 5 report"
    assert report["selected_grade"] == 5


@pytest.mark.asyncio
async def test_the_counts_describe_the_filtered_set_not_the_school(client, db_conn):
    """`total_units` and the tier counts are read as headline figures. If they
    kept describing the whole school while the table below them showed one
    grade, the two halves of the page would disagree."""
    school_id, _, _ = await _two_grade_school(client)

    everything = await get_curriculum_health(db_conn, school_id)
    just_g5 = await get_curriculum_health(db_conn, school_id, grade=5)

    assert just_g5["total_units"] == len(just_g5["units"])
    assert just_g5["total_units"] < everything["total_units"]


# ── Rule 3: the picker does not collapse ──────────────────────────────────────


@pytest.mark.asyncio
async def test_selecting_a_grade_does_not_remove_the_others_from_the_picker(client, db_conn):
    """The trap this exists to prevent: options sourced from the filtered
    result. Pick Grade 5, and the only grade still on offer is Grade 5 — the
    filter is a one-way door and "All grades" is unreachable."""
    school_id, _, _ = await _two_grade_school(client)

    unfiltered = await get_curriculum_health(db_conn, school_id)
    filtered = await get_curriculum_health(db_conn, school_id, grade=5)

    assert unfiltered["available_grades"] == [5, 10]
    assert filtered["available_grades"] == [5, 10], "picking a grade must not shrink the picker"


@pytest.mark.asyncio
async def test_a_grade_with_students_but_no_activity_is_still_offered(client, db_conn):
    """"No activity in Grade 10" is a real answer and one a teacher may need.
    Only a grade with nobody enrolled is a dead end worth hiding."""
    school_id = await _school(client)
    cid5 = await _curriculum(client, 5, "GF-Q-G5")
    s5 = await _enrol(client, school_id, 5)
    await _activity(client, s5, "GF-Q-G5", cid5, 5)
    await _enrol(client, school_id, 10)  # enrolled, never opened anything

    report = await get_curriculum_health(db_conn, school_id)

    assert report["available_grades"] == [5, 10]


@pytest.mark.asyncio
async def test_an_empty_grade_still_reports_the_full_picker(client, db_conn):
    """Filtering to a grade whose cohort is empty takes the early return. If
    that path dropped `available_grades`, the teacher would land on an empty
    report with no control to leave it."""
    school_id = await _school(client)
    cid5 = await _curriculum(client, 5, "GF-E-G5")
    s5 = await _enrol(client, school_id, 5)
    await _activity(client, s5, "GF-E-G5", cid5, 5)

    report = await get_curriculum_health(db_conn, school_id, grade=9)

    assert report["units"] == []
    assert report["total_units"] == 0
    assert report["available_grades"] == [5], "the way back must survive the empty case"
    assert report["selected_grade"] == 9


# ── The rule that outranks the feature: entitlement (#576) ────────────────────


async def _teacher(client: AsyncClient, school_id: str, grades: list[int]) -> dict:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider, name, email,
                 role, account_status)
            VALUES ($1, $2, $3, 'local', 'Filter Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"local:{teacher_id}",
            f"gf-teacher-{teacher_id[:8]}@example.com",
        )
        for grade in grades:
            await conn.execute(
                "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
                " VALUES ($1, $2, $3)",
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                grade,
            )
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role="teacher")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_a_teacher_cannot_filter_to_a_grade_they_do_not_teach(client, db_conn):
    """The same one-parameter exploit the roster was hardened against (#576).
    A new filter is a new place to try it."""
    school_id, _, _ = await _two_grade_school(client)
    headers = await _teacher(client, school_id, grades=[5])

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers=headers,
        params={"grade": 10},
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_a_teacher_is_only_offered_their_own_grades(client, db_conn):
    """The picker is scoped too. Offering Grade 10 to a Grade 5 teacher would
    advertise the existence of a cohort they cannot see, and every click on it
    would 403 — leaking roster shape through a control that never works."""
    school_id, g5_unit, g10_unit = await _two_grade_school(client)
    headers = await _teacher(client, school_id, grades=[5])

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health", headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["available_grades"] == [5]
    assert g10_unit not in {u["unit_id"] for u in body["units"]}
    assert g5_unit in {u["unit_id"] for u in body["units"]}


@pytest.mark.asyncio
async def test_a_teacher_may_still_filter_within_their_own_grades(client, db_conn):
    """Scoping must not break the legitimate case — a teacher of two grades
    asking about one of them."""
    school_id, g5_unit, g10_unit = await _two_grade_school(client)
    headers = await _teacher(client, school_id, grades=[5, 10])

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers=headers,
        params={"grade": 10},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["selected_grade"] == 10
    assert g10_unit in {u["unit_id"] for u in body["units"]}
    assert g5_unit not in {u["unit_id"] for u in body["units"]}
    assert body["available_grades"] == [5, 10], "both remain selectable"
