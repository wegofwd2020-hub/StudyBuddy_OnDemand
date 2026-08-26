"""
tests/test_units_done_denominator_638.py

"Units done" must be measured against the student's OWN curriculum (issue #638).

Reported by Venki 2026-08-25: *"For Venky_Gr11 Units done shows 4/56 — can you
check where it is taking the count of 56?"*

The denominator counted every default curriculum at the student's grade, and
since Epic 8 a grade has one default per stream:

    default-2026-g11             19 units   (STEM)
    default-2026-g11-commerce     6
    default-2026-g11-humanities   2
    default-2026-g11-science     29
                                 ──
                                 56   ← what was shown

So a Grade 11 student was measured against four streams they are not all taking.

It looks correct for Grades 8 and 10 purely because those have a single default
curriculum each — which is why it survived: the bug is invisible in exactly the
grades most testing uses. Grade 12 (3 curricula, 54 units) was wrong too.

## Why the fix resolves rather than re-queries

The denominator now comes from `resolve_curriculum_id()` — the same three-step
resolution that decides which content the student is actually served
(school-owned → classroom package → `default-{year}-g{grade}`).

Expressing that resolution a second time in SQL is exactly the mistake behind
pitfall #31, where `get_curriculum_tree` re-derived the curriculum with a
simpler query and quietly served stream students the wrong subjects. One
resolver, called by everything, is the point.

Two sites had the fault and both are covered here: the reports roster and the
at-risk report.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_YEAR = 2026


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Denominator School{suffix}",
            "contact_email": f"denom{suffix}@school.example.com",
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


async def _seed_curriculum(
    client: AsyncClient, curriculum_id: str, grade: int, n_units: int, *, subject: str
) -> None:
    """A platform-default curriculum for `grade` with `n_units` units."""
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
                VALUES ($1, $2, $3, $4, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                f"{curriculum_id}-U{i}",
                curriculum_id,
                subject,
                f"Unit {i}",
                i,
            )


async def _enrol(client: AsyncClient, school_id: str, grade: int, name: str) -> str:
    student_id = str(uuid.uuid4())
    email = f"denom-{student_id[:8]}@example.com"
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
            f"auth0|denom-{student_id.replace('-', '')}",
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


async def _roster(client: AsyncClient, school: dict) -> list[dict]:
    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/roster", headers=_headers(school)
    )
    assert r.status_code == 200, r.text
    return r.json()["students"]


# ── The reported case ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_denominator_is_the_students_own_curriculum_not_every_stream(client, db_conn):
    """A grade with several stream curricula must not sum them.

    Grade 11 here has a 3-unit STEM default and a 5-unit science stream. A
    student resolving to the STEM default is 0/3, never 0/8.
    """
    await _seed_curriculum(client, f"default-{_YEAR}-g11", 11, 3, subject="G11-STEM")
    await _seed_curriculum(client, f"default-{_YEAR}-g11-science", 11, 5, subject="G11-SCI")

    school = await _register_school(client, "_streams")
    await _enrol(client, school["school_id"], 11, "Stream Student")

    rows = await _roster(client, school)
    assert rows, "roster was empty"
    total = rows[0]["total_units"]
    assert total == 3, f"denominator summed the streams: expected 3, got {total}"


@pytest.mark.asyncio
async def test_a_single_curriculum_grade_is_unaffected(client, db_conn):
    """Grades 8 and 10 read correctly today and must keep doing so.

    They have one default curriculum each, which is why the bug was invisible
    there. This pins that the fix does not disturb them.
    """
    await _seed_curriculum(client, f"default-{_YEAR}-g10", 10, 4, subject="G10-STEM")

    school = await _register_school(client, "_single")
    await _enrol(client, school["school_id"], 10, "Single Curriculum Student")

    rows = await _roster(client, school)
    assert rows[0]["total_units"] == 4, rows[0]


@pytest.mark.asyncio
async def test_a_school_owned_curriculum_wins_over_the_platform_default(client, db_conn):
    """Resolution step 1: a school's own curriculum is what its students take."""
    await _seed_curriculum(client, f"default-{_YEAR}-g9", 9, 7, subject="G9-STEM")

    school = await _register_school(client, "_owned")
    school_curriculum = f"school-{uuid.uuid4().hex[:8]}-g9"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id, is_default)
            VALUES ($1, 'School Own G9', 9, $2, 'school', $3, FALSE)
            """,
            school_curriculum,
            _YEAR,
            uuid.UUID(school["school_id"]),
        )
        for i in range(1, 3):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, 'G9-OWN', $3, $3, $4)
                """,
                f"{school_curriculum}-U{i}",
                school_curriculum,
                f"Own Unit {i}",
                i,
            )

    await _enrol(client, school["school_id"], 9, "School Curriculum Student")

    rows = await _roster(client, school)
    assert rows[0]["total_units"] == 2, (
        f"used the platform default instead of the school's own: {rows[0]}"
    )


@pytest.mark.asyncio
async def test_at_risk_report_uses_the_same_denominator(client, db_conn):
    """The second site with the identical fault.

    `get_at_risk_students` built its own `total_units` CTE grouped by grade over
    every default curriculum — the same sum, in a report that also names the
    students it is wrong about.
    """
    await _seed_curriculum(client, f"default-{_YEAR}-g12", 12, 3, subject="G12-STEM")
    await _seed_curriculum(client, f"default-{_YEAR}-g12-commerce", 12, 6, subject="G12-COM")

    school = await _register_school(client, "_atrisk")
    await _enrol(client, school["school_id"], 12, "At Risk Student")

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/at-risk", headers=_headers(school)
    )
    assert r.status_code == 200, r.text
    listed = r.json()["students"]
    assert listed, "expected an inactive student to be listed"
    total = listed[0]["total_units"]
    assert total == 3, f"at-risk denominator summed the streams: expected 3, got {total}"


@pytest.mark.asyncio
async def test_a_school_fork_counts_its_source_curriculums_units(client, db_conn):
    """Regression caught on the demo minutes after #638 shipped.

    School FORK curricula carry no rows in `curriculum_units` — the units live
    under the source OOB curriculum (`source_curriculum_id`), which is why
    content serving swaps fork -> source before reading. Counting the fork
    directly returns ZERO, so a student on a forked curriculum went from a
    wrong denominator (56) to an impossible one (0).

    Venky_Gr11 on the demo resolves through a classroom package to fork
    `0be6dbbd-...` ("Grade 8 STEM 2026"), which has 0 own units and 20 under
    `default-2026-g8`.

    This is the pitfall #31 family again: using the resolver but not the full
    serving path.
    """
    source = f"default-{_YEAR}-g7"
    await _seed_curriculum(client, source, 7, 6, subject="G7-STEM")

    school = await _register_school(client, "_fork")
    fork_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id,
                 is_default, source_curriculum_id)
            VALUES ($1, 'Forked G7', 7, $2, 'school', $3, FALSE, $4)
            """,
            fork_id,
            _YEAR,
            uuid.UUID(school["school_id"]),
            source,
        )

    await _enrol(client, school["school_id"], 7, "Fork Student")

    rows = await _roster(client, school)
    assert rows[0]["total_units"] == 6, (
        f"a fork with no units of its own must count its source's: {rows[0]}"
    )
