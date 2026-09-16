"""
tests/test_overview_filters_773.py

Filters and grouping on the admin overview (Venki, 14 Sep — #773):

    "1. Filter options for Grade/Subject
     2. Group subjects by Grade in 'Units with Struggles'
     3. Group subjects by Grade in 'Units with no activity'
     4. Display format similar to Reports->Engagement->Units with zero activity"

Points 2-4 were not merely unimplemented — they were INEXPRESSIBLE. Both lists
were `list[str]` of raw unit ids, so the screen showed "G8-MATH-002" with no
grade to group on and no subject to read. The contract change to
`OverviewUnitRef` is therefore the substance of this issue, not a detail of it.

The two filters deliberately act at DIFFERENT levels, and the tests below pin
that difference because getting it wrong invents a number:

  * `grade` narrows the COHORT, so every figure moves with it — enrolled
    students, pass rate, the unit lists, the catalog. Same rule as
    `get_curriculum_health`.
  * `subject` narrows only the two UNIT LISTS. A subject is a property of a
    unit, not of a student, so "Commerce" cannot mean a different set of
    enrolled students or a different pass rate. Applying it to the headline
    tiles would report a figure the data cannot support.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import get_overview
from tests.helpers.token_factory import make_teacher_token

_YEAR = 2026


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Overview Filter School{suffix}",
            "contact_email": f"ovf{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _headers(reg: dict) -> dict:
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
    )
    return {"Authorization": f"Bearer {token}"}


async def _curriculum(client: AsyncClient, grade: int, units: list[tuple[str, str, str]]) -> str:
    """`units` is [(unit_id, subject_code, subject_display_name)]."""
    cid = f"ovf-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Overview Filter Curriculum', $2, $3, 'platform', FALSE)
            """,
            cid,
            grade,
            _YEAR,
        )
        for unit_id, code, _name in units:
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, 0)
                """,
                unit_id,
                cid,
                code,
                f"Name of {unit_id}",
            )
        for _u, code, name in units:
            await conn.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, subject_name, version_number, status)
                VALUES ($1, $2, $3, 1, 'published')
                ON CONFLICT DO NOTHING
                """,
                cid,
                code,
                name,
            )
    return cid


async def _enrol(client: AsyncClient, school_id: str, grade: int, cid: str) -> str:
    student_id = str(uuid.uuid4())
    email = f"ovf-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'OVF Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|ovf-{student_id.replace('-', '')}",
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
        classroom_id = await conn.fetchval(
            "INSERT INTO classrooms (school_id, name, grade) VALUES ($1, $2, $3)"
            " RETURNING classroom_id",
            uuid.UUID(school_id),
            f"OVF Room {student_id[:6]}",
            grade,
        )
        await conn.execute(
            "INSERT INTO classroom_packages (classroom_id, curriculum_id) VALUES ($1, $2)",
            classroom_id,
            cid,
        )
        await conn.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) VALUES ($1, $2)",
            classroom_id,
            uuid.UUID(student_id),
        )
    return student_id


async def _two_grade_school(client, suffix: str) -> str:
    """Grade 8 Mathematics + Grade 11 Accountancy, nothing touched — so both
    units land in `units_no_activity`."""
    reg = await _school(client, suffix)
    g8 = await _curriculum(client, 8, [("OVF-G8-MATH", "G8-MATH", "Mathematics")])
    g11 = await _curriculum(client, 11, [("OVF-G11-ACC", "G11-ACC", "Accountancy")])
    await _enrol(client, reg["school_id"], 8, g8)
    await _enrol(client, reg["school_id"], 11, g11)
    return reg["school_id"]


def _ids(rows: list[dict]) -> set[str]:
    return {u["unit_id"] for u in rows}


# ── The contract change: rows that can be grouped and read ────────────────────


@pytest.mark.asyncio
async def test_units_carry_name_subject_and_grade(client, db_conn, fake_redis):
    """Points 2-4 of the issue need these. Without them the screen has a code
    and nothing to group on."""
    school_id = await _two_grade_school(client, "_shape")
    pool = client._transport.app.state.pool

    report = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis
    )
    by_id = {u["unit_id"]: u for u in report["units_no_activity"]}

    assert by_id["OVF-G8-MATH"]["grade"] == 8
    assert by_id["OVF-G8-MATH"]["unit_name"] == "Name of OVF-G8-MATH"
    assert by_id["OVF-G11-ACC"]["grade"] == 11


@pytest.mark.asyncio
async def test_subject_is_a_display_name_not_a_code(client, db_conn, fake_redis):
    """`curriculum_units.subject` holds a CODE for every stream curriculum
    (pitfall #32). This list must not be the one column that shows it — the
    other two reports resolve, and a teacher reads them side by side."""
    school_id = await _two_grade_school(client, "_label")
    pool = client._transport.app.state.pool

    report = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis
    )
    by_id = {u["unit_id"]: u for u in report["units_no_activity"]}

    assert by_id["OVF-G11-ACC"]["subject"] == "Accountancy"
    assert "-" not in by_id["OVF-G11-ACC"]["subject"], "that is a code, not a name"


# ── Grade narrows the whole cohort ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grade_narrows_the_units_and_the_catalog(client, db_conn, fake_redis):
    """The catalog has to narrow with the cohort, or Grade 11's units are
    reported as untouched inside a Grade 8 report and the filter manufactures
    coverage gaps it exists to measure."""
    school_id = await _two_grade_school(client, "_grade")
    pool = client._transport.app.state.pool

    report = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, grade=8
    )

    assert "OVF-G8-MATH" in _ids(report["units_no_activity"])
    assert "OVF-G11-ACC" not in _ids(report["units_no_activity"])
    assert report["selected_grade"] == 8


@pytest.mark.asyncio
async def test_grade_moves_the_headline_figures_too(client, db_conn, fake_redis):
    """A cohort filter that left `enrolled_students` describing the school
    would put a figure on screen that the table below contradicts."""
    school_id = await _two_grade_school(client, "_head")
    pool = client._transport.app.state.pool

    everything = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis
    )
    just_g8 = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, grade=8
    )

    assert everything["enrolled_students"] == 2
    assert just_g8["enrolled_students"] == 1


# ── Subject narrows ONLY the unit lists ───────────────────────────────────────


@pytest.mark.asyncio
async def test_subject_narrows_the_unit_lists(client, db_conn, fake_redis):
    school_id = await _two_grade_school(client, "_subj")
    pool = client._transport.app.state.pool

    report = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, subject="Accountancy"
    )

    assert _ids(report["units_no_activity"]) == {"OVF-G11-ACC"}
    assert report["selected_subject"] == "Accountancy"


@pytest.mark.asyncio
async def test_subject_does_NOT_change_the_headline_figures(client, db_conn, fake_redis):
    """The distinction that matters. A subject is a property of a unit, not of a
    student — "Accountancy" cannot mean a different number of enrolled students.
    Narrowing the tiles by it would report a figure the data cannot support."""
    school_id = await _two_grade_school(client, "_subjhead")
    pool = client._transport.app.state.pool

    everything = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis
    )
    just_acc = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, subject="Accountancy"
    )

    assert just_acc["enrolled_students"] == everything["enrolled_students"] == 2
    assert just_acc["unreviewed_feedback_count"] == everything["unreviewed_feedback_count"]


# ── The pickers ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_selecting_a_subject_does_not_shrink_the_subject_picker(client, db_conn, fake_redis):
    """The classic trap: options sourced from the filtered result. Pick
    Accountancy and it becomes the only option, with no way back."""
    school_id = await _two_grade_school(client, "_picker")
    pool = client._transport.app.state.pool

    filtered = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, subject="Accountancy"
    )

    assert filtered["available_subjects"] == ["Accountancy", "Mathematics"]
    assert filtered["available_grades"] == [8, 11]


@pytest.mark.asyncio
async def test_an_empty_cohort_still_reports_the_way_back(client, db_conn, fake_redis):
    school_id = await _two_grade_school(client, "_empty")
    pool = client._transport.app.state.pool

    report = await get_overview(
        db_conn, school_id, "30d", None, pool=pool, redis=fake_redis, grade=12
    )

    assert report["units_no_activity"] == []
    assert report["available_grades"] == [8, 11], "the picker survives an empty result"
    assert report["selected_grade"] == 12


# ── Entitlement outranks the filter ───────────────────────────────────────────


async def _teacher_of(client: AsyncClient, school_id: str, grades: list[int]) -> dict:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider, name, email,
                 role, account_status)
            VALUES ($1, $2, $3, 'local', 'OVF Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"local:{teacher_id}",
            f"ovf-teacher-{teacher_id[:8]}@example.com",
        )
        for g in grades:
            await conn.execute(
                "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
                " VALUES ($1, $2, $3)",
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                g,
            )
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role="teacher")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_a_teacher_cannot_filter_to_a_grade_they_do_not_teach(client, db_conn):
    """A new filter is a new place to try the #576 one-parameter exploit."""
    school_id = await _two_grade_school(client, "_deny")
    headers = await _teacher_of(client, school_id, grades=[8])

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/overview",
        headers=headers,
        params={"period": "30d", "grade": 11},
    )
    assert r.status_code == 403, r.text
