"""
tests/test_reports_grade_scoping_sweep.py

Grade scoping on the AGGREGATE report endpoints (issue #576, second half).

#622 scoped the two endpoints that were reported — the roster and the individual
student report — and stopped there, because the remaining six are aggregate
shaped and the right fix depended on a product decision: is a *grade* the right
entitlement unit at all, or should it be a classroom?

Decision taken 2026-08-24: **grade now, classroom later.** Classrooms exist
(migration 0038) but are largely unpopulated, so enforcing them today would show
teachers an empty product. These endpoints are therefore scoped to the same
`teacher_grade_assignments` model the rest of the product already enforces.

The six, and what each leaked to a teacher assigned only Grade 8:

    overview           school-wide counts; other grades' unit codes
    unit/{unit_id}     per-unit performance for any grade
    curriculum-health  every unit's health tier
    feedback           student feedback across grades
    trends             school-wide trend lines
    at-risk            NAMED at-risk students from other grades

`at-risk` is the sharpest: it names individual students flagged as struggling,
which is an educational record under FERPA for a student the teacher was never
assigned to.

Five of the six draw their cohort from `_enrolled_ids()`, so the filter belongs
there rather than repeated per endpoint. `at-risk` builds its own `enrolled` CTE
and is scoped separately — the tests below cover it explicitly for that reason.

Rules preserved from #622:
  - `school_admin` keeps full visibility (teacher superset, ADR-005)
  - a teacher with NO assignments has no cohort, so sees nothing rather than
    everything
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_G8_UNIT = "G8-MATH-001"
_G10_UNIT = "G10-MATH-001"


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Sweep School{suffix}",
            "contact_email": f"sweep{suffix}@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_teacher(
    client: AsyncClient, school_id: str, grades: list[int], role: str = "teacher"
) -> dict:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider, name, email,
                 role, account_status)
            VALUES ($1, $2, $3, 'local', 'Sweep Teacher', $4, $5, 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"local:{teacher_id}",
            f"sweep-t-{teacher_id[:8]}@example.com",
            role,
        )
        for grade in grades:
            await conn.execute(
                "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
                " VALUES ($1, $2, $3)",
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                grade,
            )
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role=role)
    return {"Authorization": f"Bearer {token}"}


async def _enrol_student_with_work(
    client: AsyncClient,
    school_id: str,
    grade: int,
    unit_id: str,
    *,
    name: str,
    passed: bool = True,
    stale_days: int = 0,
) -> str:
    """An enrolled student with one completed quiz session and a lesson view.

    `stale_days` backdates the activity so the student trips the at-risk
    inactivity threshold.
    """
    student_id = str(uuid.uuid4())
    email = f"sweep-s-{student_id[:8]}@example.com"
    when = datetime.now(UTC) - timedelta(days=stale_days)
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, $3, $4, $5, 'en', 'active', $6)
            """,
            uuid.UUID(student_id),
            f"auth0|sweep-{student_id.replace('-', '')}",
            name,
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
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, $4, 'Mathematics', $5, $5, $6, 8, TRUE, 1, $7)
            """,
            uuid.UUID(student_id),
            unit_id,
            f"default-2026-g{grade}",
            grade,
            when,
            7 if passed else 2,
            passed,
        )
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, started_at, ended_at, duration_s, audio_played)
            VALUES ($1, $2, $3, $4, $4, 120, FALSE)
            """,
            uuid.UUID(student_id),
            unit_id,
            f"default-2026-g{grade}",
            when,
        )
    return student_id


async def _school_with_two_grades(client: AsyncClient, suffix: str) -> dict:
    """One Grade 8 student and one Grade 10 student, each with real activity."""
    school = await _register_school(client, suffix)
    g8 = await _enrol_student_with_work(
        client, school["school_id"], 8, _G8_UNIT, name="Grade Eight Pupil"
    )
    g10 = await _enrol_student_with_work(
        client, school["school_id"], 10, _G10_UNIT, name="Grade Ten Pupil"
    )
    return {**school, "g8_student": g8, "g10_student": g10}


def _url(school_id: str, path: str) -> str:
    return f"/api/v1/reports/school/{school_id}/{path}"


# ── overview ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overview_counts_only_the_teachers_grades(client, db_conn):
    """The dashboard summary. Two students enrolled, one in the teacher's grade."""
    s = await _school_with_two_grades(client, "_ov")
    headers = await _make_teacher(client, s["school_id"], [8])

    r = await client.get(_url(s["school_id"], "overview"), headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["enrolled_students"] == 1, r.json()


@pytest.mark.asyncio
async def test_overview_does_not_leak_other_grade_unit_codes(client, db_conn):
    """"Units needing attention" listed G10 codes on a G8 teacher's landing page.

    Both students FAIL here on purpose. With passing students no unit is
    struggling, so the lists are empty and the test would pass without any
    scoping at all — it has to be able to fail before it can prove anything.
    """
    school = await _register_school(client, "_ovu")
    await _enrol_student_with_work(
        client, school["school_id"], 8, _G8_UNIT, name="G8 Struggler", passed=False
    )
    await _enrol_student_with_work(
        client, school["school_id"], 10, _G10_UNIT, name="G10 Struggler", passed=False
    )
    s = school
    headers = await _make_teacher(client, s["school_id"], [8])

    r = await client.get(_url(s["school_id"], "overview"), headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    leaked = [
        u
        for key in ("units_with_struggles", "units_no_activity")
        for u in body.get(key, [])
        if str(u).startswith("G10-")
    ]
    assert leaked == [], body


@pytest.mark.asyncio
async def test_overview_unrestricted_for_school_admin(client, db_conn):
    """school_admin is a teacher superset (ADR-005) and still sees the school."""
    s = await _school_with_two_grades(client, "_ovadmin")
    headers = await _make_teacher(client, s["school_id"], [], role="school_admin")

    r = await client.get(_url(s["school_id"], "overview"), headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["enrolled_students"] == 2, r.json()


@pytest.mark.asyncio
async def test_overview_empty_for_a_teacher_with_no_assignments(client, db_conn):
    """No cohort means no students — not every student."""
    s = await _school_with_two_grades(client, "_ovnone")
    headers = await _make_teacher(client, s["school_id"], [])

    r = await client.get(_url(s["school_id"], "overview"), headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["enrolled_students"] == 0, r.json()


# ── at-risk — the one that names students ─────────────────────────────────────


@pytest.mark.asyncio
async def test_at_risk_does_not_name_students_from_other_grades(client, db_conn):
    """The sharpest leak: a named educational record for an unassigned student."""
    school = await _register_school(client, "_risk")
    await _enrol_student_with_work(
        client, school["school_id"], 8, _G8_UNIT,
        name="Grade Eight AtRisk", passed=False, stale_days=60,
    )
    await _enrol_student_with_work(
        client, school["school_id"], 10, _G10_UNIT,
        name="Grade Ten AtRisk", passed=False, stale_days=60,
    )
    headers = await _make_teacher(client, school["school_id"], [8])

    r = await client.get(_url(school["school_id"], "at-risk"), headers=headers)
    assert r.status_code == 200, r.text
    listed = r.json()["students"]
    names = [s["student_name"] for s in listed]
    assert "Grade Ten AtRisk" not in names, names
    # Stronger than the name check: no row may carry an unassigned grade.
    assert all(s["grade"] == 8 for s in listed), listed


@pytest.mark.asyncio
async def test_at_risk_still_lists_the_teachers_own_grade(client, db_conn):
    """Scoping must not empty the report the teacher legitimately needs."""
    school = await _register_school(client, "_riskown")
    await _enrol_student_with_work(
        client, school["school_id"], 8, _G8_UNIT,
        name="Grade Eight AtRisk", passed=False, stale_days=60,
    )
    headers = await _make_teacher(client, school["school_id"], [8])

    r = await client.get(_url(school["school_id"], "at-risk"), headers=headers)
    assert r.status_code == 200, r.text
    names = [s["student_name"] for s in r.json()["students"]]
    assert "Grade Eight AtRisk" in names, names


# ── curriculum-health / trends / feedback / unit ──────────────────────────────


@pytest.mark.asyncio
async def test_curriculum_health_excludes_other_grade_units(client, db_conn):
    s = await _school_with_two_grades(client, "_ch")
    headers = await _make_teacher(client, s["school_id"], [8])

    r = await client.get(_url(s["school_id"], "curriculum-health"), headers=headers)
    assert r.status_code == 200, r.text
    units = [u["unit_id"] for u in r.json()["units"]]
    assert _G10_UNIT not in units, units
    assert _G8_UNIT in units, units


@pytest.mark.asyncio
async def test_trends_exclude_other_grade_activity(client, db_conn):
    """A G8 teacher's trend line must not aggregate G10 work.

    Compared against the school_admin view of the same school so the assertion
    is about scoping rather than a hard-coded number.
    """
    s = await _school_with_two_grades(client, "_tr")
    teacher = await _make_teacher(client, s["school_id"], [8])
    admin = await _make_teacher(client, s["school_id"], [], role="school_admin")

    scoped = await client.get(_url(s["school_id"], "trends"), headers=teacher)
    whole = await client.get(_url(s["school_id"], "trends"), headers=admin)
    assert scoped.status_code == 200, scoped.text
    assert whole.status_code == 200, whole.text

    def total(body: dict) -> int:
        return sum(w.get("quiz_attempts", 0) for w in body.get("weeks", []))

    assert total(scoped.json()) < total(whole.json()), (scoped.json(), whole.json())


@pytest.mark.asyncio
async def test_unit_report_refuses_a_unit_outside_the_teachers_grades(client, db_conn):
    """A G8 teacher asking for a G10 unit gets nothing about it.

    Either a 403 or an empty cohort is acceptable — what must not happen is
    real Grade 10 performance data coming back.
    """
    s = await _school_with_two_grades(client, "_unit")
    headers = await _make_teacher(client, s["school_id"], [8])

    r = await client.get(
        _url(s["school_id"], f"unit/{_G10_UNIT}") + "?period=30d", headers=headers
    )
    assert r.status_code in (200, 403), r.text
    if r.status_code == 200:
        body = r.json()
        assert body.get("students_attempted", 0) == 0, body


@pytest.mark.asyncio
async def test_feedback_report_excludes_other_grade_students(client, db_conn):
    """Feedback carries student voice — same boundary as their records."""
    s = await _school_with_two_grades(client, "_fb")
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for student_id, unit in ((s["g8_student"], _G8_UNIT), (s["g10_student"], _G10_UNIT)):
            await conn.execute(
                """
                INSERT INTO feedback (student_id, unit_id, category, message, rating)
                VALUES ($1, $2, 'content', $3, 3)
                """,
                uuid.UUID(student_id),
                unit,
                f"Feedback about {unit}",
            )

    headers = await _make_teacher(client, s["school_id"], [8])
    r = await client.get(_url(s["school_id"], "feedback"), headers=headers)
    assert r.status_code == 200, r.text
    units = [i.get("unit_id") for i in r.json().get("items", [])]
    assert _G10_UNIT not in units, r.json()
