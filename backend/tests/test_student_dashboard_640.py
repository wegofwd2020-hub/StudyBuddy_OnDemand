"""
tests/test_student_dashboard_640.py

The student dashboard's first slice (issue #640, design §11).

Decided 2026-08-26: the product owner's four questions in Venki's layout. Two of
them ship without the academic calendar and are covered here —

    Q3  my subjects and scores        -> subject_progress
    Q4  my standing in the class      -> standing
    Q1  what am I doing next (part)   -> next_unit

Q1's "am I on pace" and Q2 entirely need ADR-007 and are deliberately absent
rather than approximated.

## What was wrong with the endpoint before

`/student/dashboard` existed but the web dashboard never called it, and it
derived the curriculum as

    WHERE cu.curriculum_id IN (
        SELECT curriculum_id FROM progress_sessions WHERE student_id = $1
        UNION
        SELECT curriculum_id FROM lesson_views   WHERE student_id = $1
    )

which is pitfall #31 — re-deriving instead of calling `resolve_curriculum_id`.
It fails in the two states §4.2 calls the common ones: a brand-new student
matches nothing (blank dashboard for the student who most needs direction), and
a student on a school FORK matches a curriculum holding no units.

It also read `mv_student_curriculum_progress.status = 'completed'` — a THIRD
definition of "units done" beside the two reconciled in #655, and one served
from a materialized view that can be stale.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token

_YEAR = 2026
_GRADE = 8


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _school(client: AsyncClient, suffix: str) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Dashboard School{suffix}",
            "contact_email": f"dash{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _school_curriculum(
    client: AsyncClient,
    school_id: str,
    units: list[tuple[str, str]],
    *,
    source_curriculum_id: str | None = None,
) -> str:
    """A school-OWNED curriculum, so each test gets its own.

    Resolution step 1 matches `c.school_id = s.school_id AND c.grade = s.grade`,
    so this exercises the real resolver while avoiding the shared
    `default-{year}-g{grade}` rows other test files seed with different unit
    counts.

    `units` is a list of (unit_id, subject). Passing `source_curriculum_id` with
    an empty `units` builds a FORK — no units of its own, exactly like the forks
    the teacher import flow creates.
    """
    curriculum_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id,
                 is_default, source_curriculum_id)
            VALUES ($1, 'Dashboard Curriculum', $2, $3, 'school', $4, FALSE, $5)
            """,
            curriculum_id,
            _GRADE,
            _YEAR,
            uuid.UUID(school_id),
            source_curriculum_id,
        )
        for i, (unit_id, subject) in enumerate(units, start=1):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, $5)
                """,
                unit_id,
                curriculum_id,
                subject,
                f"Title {unit_id}",
                i,
            )
    return curriculum_id


async def _platform_curriculum(client: AsyncClient, units: list[tuple[str, str]]) -> str:
    """A platform curriculum to serve as a fork SOURCE."""
    curriculum_id = f"source-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Source Curriculum', $2, $3, 'platform', FALSE)
            """,
            curriculum_id,
            _GRADE,
            _YEAR,
        )
        for i, (unit_id, subject) in enumerate(units, start=1):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, $5)
                """,
                unit_id,
                curriculum_id,
                subject,
                f"Title {unit_id}",
                i,
            )
    return curriculum_id


async def _student(client: AsyncClient, school_id: str | None, name: str = "Dash Student") -> str:
    student_id = str(uuid.uuid4())
    email = f"dash-{student_id[:8]}@example.com"
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
            f"auth0|dash-{student_id.replace('-', '')}",
            name,
            email,
            _GRADE,
            uuid.UUID(school_id) if school_id else None,
        )
        if school_id:
            await conn.execute(
                """
                INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
                VALUES ($1, $2, $3, 'active', $4)
                """,
                uuid.UUID(school_id),
                email,
                uuid.UUID(student_id),
                _GRADE,
            )
    return student_id


async def _quiz(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
    *,
    score: int,
    total: int,
    passed: bool,
    attempt: int = 1,
):
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, $4, 'Dash', NOW(), NOW(), $5, $6, TRUE, $7, $8)
            """,
            uuid.UUID(student_id),
            unit_id,
            curriculum_id,
            _GRADE,
            score,
            total,
            attempt,
            passed,
        )


async def _dashboard(client: AsyncClient, student_id: str) -> dict:
    token = make_student_token(student_id=student_id, grade=_GRADE)
    r = await client.get("/api/v1/student/dashboard", headers=_auth(token))
    assert r.status_code == 200, r.text
    return r.json()


# ── Q3: my subjects ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_new_student_sees_their_subjects_before_doing_anything(client, db_conn):
    """The empty state, which is the common one — and used to render blank.

    Deriving the curriculum from the student's own sessions means a student with
    no sessions matches no curriculum, so every subject tile was empty on the
    first screen they ever see.
    """
    school = await _school(client, "_new")
    await _school_curriculum(client, school, [("NEW-M1", "Maths"), ("NEW-S1", "Science")])
    student = await _student(client, school)

    data = await _dashboard(client, student)
    subjects = {s["subject"]: s for s in data["subject_progress"]}

    assert set(subjects) == {"Maths", "Science"}, data["subject_progress"]
    assert subjects["Maths"]["units_total"] == 1
    assert subjects["Maths"]["units_completed"] == 0
    # Not 0.0 — a student who has answered nothing has not scored zero.
    assert subjects["Maths"]["avg_score"] is None, subjects["Maths"]


@pytest.mark.asyncio
async def test_a_fork_curriculum_reports_its_sources_units(client, db_conn):
    """School forks hold no units of their own — they live under the source.

    The same fault as the #650 regression, in a different report.
    """
    source = await _platform_curriculum(client, [("FORK-M1", "Maths"), ("FORK-M2", "Maths")])
    school = await _school(client, "_fork")
    await _school_curriculum(client, school, [], source_curriculum_id=source)
    student = await _student(client, school)

    data = await _dashboard(client, student)
    subjects = {s["subject"]: s for s in data["subject_progress"]}
    assert subjects.get("Maths", {}).get("units_total") == 2, data["subject_progress"]


@pytest.mark.asyncio
async def test_avg_score_is_weighted_by_questions_not_an_average_of_percentages(client, db_conn):
    """A 1-question quiz must not weigh the same as a 20-question one.

    1/1 (100%) and 5/20 (25%):
        average of percentages -> 62.5   (wrong, and flatters)
        questions right / asked -> 6/21 = 28.6
    """
    school = await _school(client, "_weight")
    cid = await _school_curriculum(client, school, [("W-1", "Maths"), ("W-2", "Maths")])
    student = await _student(client, school)

    await _quiz(client, student, "W-1", cid, score=1, total=1, passed=True)
    await _quiz(client, student, "W-2", cid, score=5, total=20, passed=False)

    data = await _dashboard(client, student)
    maths = next(s for s in data["subject_progress"] if s["subject"] == "Maths")
    assert maths["avg_score"] == pytest.approx(28.6, abs=0.1), maths


@pytest.mark.asyncio
async def test_retaking_a_unit_does_not_count_it_twice(client, db_conn):
    """Same invariant as #655, enforced on the student's own screen.

    The two numbers a student and their teacher read must agree.
    """
    school = await _school(client, "_retake")
    cid = await _school_curriculum(client, school, [("R-1", "Maths"), ("R-2", "Maths")])
    student = await _student(client, school)

    await _quiz(client, student, "R-1", cid, score=8, total=10, passed=True, attempt=1)
    await _quiz(client, student, "R-1", cid, score=9, total=10, passed=True, attempt=2)

    data = await _dashboard(client, student)
    maths = next(s for s in data["subject_progress"] if s["subject"] == "Maths")
    assert maths["units_completed"] == 1, maths
    assert maths["units_completed"] <= maths["units_total"], maths


# ── Q1 (part): what is next ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_next_unit_is_the_first_unpassed_unit_in_curriculum_order(client, db_conn):
    school = await _school(client, "_next")
    cid = await _school_curriculum(
        client, school, [("N-1", "Maths"), ("N-2", "Maths"), ("N-3", "Maths")]
    )
    student = await _student(client, school)
    await _quiz(client, student, "N-1", cid, score=9, total=10, passed=True)

    data = await _dashboard(client, student)
    assert data["next_unit"]["unit_id"] == "N-2", data["next_unit"]


@pytest.mark.asyncio
async def test_next_unit_is_absent_once_everything_is_passed(client, db_conn):
    """No unit to suggest is a real state, not an error."""
    school = await _school(client, "_done")
    cid = await _school_curriculum(client, school, [("D-1", "Maths")])
    student = await _student(client, school)
    await _quiz(client, student, "D-1", cid, score=10, total=10, passed=True)

    data = await _dashboard(client, student)
    assert data["next_unit"] is None, data["next_unit"]


# ── Q4: standing in the class ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_standing_is_withheld_from_a_cohort_too_small_to_aggregate(client, db_conn):
    """A privacy control, not a noise threshold.

    With a cohort of two, "you 80, class 70" tells the student the other member
    scored exactly 60 — an individual's educational record, derived from an
    aggregate.
    """
    school = await _school(client, "_small")
    cid = await _school_curriculum(client, school, [("SM-1", "Maths")])
    student = await _student(client, school)
    await _quiz(client, student, "SM-1", cid, score=8, total=10, passed=True)

    other = await _student(client, school, "Other Student")
    await _quiz(client, other, "SM-1", cid, score=6, total=10, passed=True)

    data = await _dashboard(client, student)
    assert data["standing"] is None, data["standing"]


@pytest.mark.asyncio
async def test_standing_appears_once_the_cohort_is_large_enough(client, db_conn):
    school = await _school(client, "_cohort")
    cid = await _school_curriculum(client, school, [("CO-1", "Maths")])

    student = await _student(client, school)
    await _quiz(client, student, "CO-1", cid, score=8, total=10, passed=True)
    for i in range(4):
        peer = await _student(client, school, f"Peer {i}")
        await _quiz(client, peer, "CO-1", cid, score=5, total=10, passed=False)

    data = await _dashboard(client, student)
    standing = data["standing"]
    assert standing is not None, data
    assert standing["cohort_size"] == 5, standing
    assert standing["you"] == pytest.approx(80.0, abs=0.1), standing
    # (80 + 50 + 50 + 50 + 50) / 5 = 56
    assert standing["cohort"] == pytest.approx(56.0, abs=0.1), standing


@pytest.mark.asyncio
async def test_a_student_with_no_school_has_no_standing(client, db_conn):
    """Self-registered students have no cohort to stand in."""
    student = await _student(client, None)
    data = await _dashboard(client, student)
    assert data["standing"] is None, data["standing"]
