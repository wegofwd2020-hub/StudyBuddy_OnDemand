"""
tests/test_units_done_numerator_655.py

"Units done" must count DISTINCT UNITS, not passed sessions (issue #655).

#638 fixed the denominator of "Units done 5/56" — it summed every stream at the
student's grade. The numerator on the same line was never looked at, and it was
wrong too:

    SUM(CASE WHEN ps.passed THEN 1 ELSE 0 END)   AS units_completed

That counts passed SESSIONS. Retake a unit you already passed and you gain
another "unit done" without touching a new unit. The denominator is a count of
distinct units in the curriculum (#638), so the fraction compared two different
things and could exceed 100%.

Live on the demo when this was found — every affected student inflated by ~67%:

    Davis Charlie           reported 10   actually  6
    Venkatesh T (Student)   reported 10   actually  6
    Venky_Gr11              reported  5   actually  3

Venky_Gr11 is the student from #638. So of the reported "5/56", the 56 was
fixed and the 5 was left — and was also wrong.

## Why it survived

Four sites in the codebase count units with

    COUNT(DISTINCT unit_id) FILTER (WHERE passed)

and two used the SUM form. The two outliers are the two that counted retakes,
and both are on the screens a teacher reads: the student progress roster and the
at-risk report. A metric defined in six places drifts in exactly this way.

In the at-risk report the count also feeds the `low_pass_rate` gate, so an
inflated value could assert a student had done work they had not.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_YEAR = 2026


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Numerator School{suffix}",
            "contact_email": f"numer{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _headers(reg: dict) -> dict:
    return {
        "Authorization": "Bearer "
        + make_teacher_token(
            teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
        )
    }


async def _seed_curriculum(client: AsyncClient, curriculum_id: str, grade: int, n_units: int):
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, $2, $3, $4, 'platform', TRUE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id,
            f"Seeded {curriculum_id}",
            grade,
            _YEAR,
        )
        for i in range(1, n_units + 1):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, 'Numerator', $3, $3, $4)
                ON CONFLICT DO NOTHING
                """,
                f"{curriculum_id}-U{i}",
                curriculum_id,
                f"Unit {i}",
                i,
            )


async def _enrol(client: AsyncClient, school_id: str, grade: int, name: str) -> str:
    student_id = str(uuid.uuid4())
    email = f"numer-{student_id[:8]}@example.com"
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
            f"auth0|numer-{student_id.replace('-', '')}",
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
    return student_id


async def _pass_unit(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
    grade: int,
    attempt: int,
    *,
    ago: timedelta = timedelta(0),
):
    """One completed, PASSED session on `unit_id`.

    `ago` defaults to ZERO, and that is not laziness. The roster counts only
    sessions with `started_at >= school_enrolments.added_at`, and the enrolment
    is created moments before by `_enrol`, so ANY backdated session — even five
    minutes — is correctly excluded. That guard stops a school adding a known
    email address and reading the student's history at another school.

    The at-risk report has no such guard (it needs to see old work precisely to
    call someone inactive), which is why that test can pass `ago=40 days`.
    """
    pool = client._transport.app.state.pool
    when = datetime.now(UTC) - ago
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, $4, 'Numerator', $5, $5, 8, 10, TRUE, $6, TRUE)
            """,
            uuid.UUID(student_id),
            unit_id,
            curriculum_id,
            grade,
            when,
            attempt,
        )


# ── The student progress roster — the screen Venki reported ───────────────────


@pytest.mark.asyncio
async def test_retaking_a_passed_unit_does_not_count_as_a_second_unit(client, db_conn):
    """The reported case: two passes of ONE unit is 1 done, not 2."""
    cid = f"default-{_YEAR}-g5"
    await _seed_curriculum(client, cid, 5, 4)
    school = await _register_school(client, "_retake")
    student = await _enrol(client, school["school_id"], 5, "Retaking Student")

    await _pass_unit(client, student, f"{cid}-U1", cid, 5, attempt=1)
    await _pass_unit(client, student, f"{cid}-U1", cid, 5, attempt=2)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/roster", headers=_headers(school)
    )
    assert r.status_code == 200, r.text
    row = r.json()["students"][0]
    assert row["units_completed"] == 1, f"counted passed sessions, not units: {row}"


@pytest.mark.asyncio
async def test_distinct_units_are_each_counted_once(client, db_conn):
    """Guard against the opposite error — collapsing genuinely different units."""
    cid = f"default-{_YEAR}-g5"
    await _seed_curriculum(client, cid, 5, 4)
    school = await _register_school(client, "_distinct")
    student = await _enrol(client, school["school_id"], 5, "Broad Student")

    for i in (1, 2, 3):
        await _pass_unit(client, student, f"{cid}-U{i}", cid, 5, attempt=1)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/roster", headers=_headers(school)
    )
    row = r.json()["students"][0]
    assert row["units_completed"] == 3, row


@pytest.mark.asyncio
async def test_units_done_can_never_exceed_the_curriculum_total(client, db_conn):
    """The invariant the two definitions broke between them.

    Four retakes of the only two units in a 2-unit curriculum used to report
    4/2. Whatever else changes, the fraction must stay a fraction.
    """
    cid = f"default-{_YEAR}-g5"
    await _seed_curriculum(client, cid, 5, 4)
    school = await _register_school(client, "_invariant")
    student = await _enrol(client, school["school_id"], 5, "Persistent Student")

    for unit in (1, 2):
        for attempt in (1, 2):
            await _pass_unit(client, student, f"{cid}-U{unit}", cid, 5, attempt=attempt)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/roster", headers=_headers(school)
    )
    row = r.json()["students"][0]
    assert row["units_completed"] <= row["total_units"], row
    assert row["units_completed"] == 2, row


# ── The at-risk report — the second site ──────────────────────────────────────


@pytest.mark.asyncio
async def test_at_risk_report_counts_distinct_units_too(client, db_conn):
    """Same fault, and here it also gates the low_pass_rate flag."""
    cid = f"default-{_YEAR}-g5"
    await _seed_curriculum(client, cid, 5, 4)
    school = await _register_school(client, "_atrisk_num")
    student = await _enrol(client, school["school_id"], 5, "At Risk Retaker")

    # Long enough ago to be flagged inactive, so the student is listed at all.
    await _pass_unit(client, student, f"{cid}-U1", cid, 5, attempt=1, ago=timedelta(days=40))
    await _pass_unit(client, student, f"{cid}-U1", cid, 5, attempt=2, ago=timedelta(days=39))

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/at-risk", headers=_headers(school)
    )
    assert r.status_code == 200, r.text
    listed = r.json()["students"]
    assert listed, "expected the inactive student to be listed"
    assert listed[0]["units_completed"] == 1, listed[0]
