"""
tests/test_pass_rate_bounds.py

First-attempt pass rate must never exceed 100% (issue #623).

Venki's 08/17 Unit Performance screenshot showed 200%, 200% and 300%. The
per-unit queries divide a COUNT of ROWS by a COUNT of DISTINCT STUDENTS, so a
student with several qualifying sessions on one unit produces a rate above 100%.

That is reachable because of #579 — opening a quiz page creates a session row,
and the demo already has a student with nine `attempt_number = 1` sessions on a
single unit.

Note the school-wide query in `get_overview_report` divides rows by rows and is
CORRECT as it stands (#471): aggregated across units a student has one
attempt-1 session per unit, so counting distinct students there would
under-count the denominator and inflate the rate. The two groupings genuinely
need different denominators — see the comment in the source. This file pins the
per-unit case only.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_UNIT = "G8-MATH-001"


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Pass Rate School{suffix}",
            "contact_email": f"passrate{suffix}@school.example.com",
            "country": "ZA",
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


async def _student_with_repeated_first_attempts(
    client: AsyncClient, school_id: str, sessions: int
) -> str:
    """One student, several attempt_number=1 passed sessions on the same unit.

    This is what #579 produces in the wild: re-opening a quiz page writes
    another session row rather than incrementing the attempt number.
    """
    student_id = str(uuid.uuid4())
    email = f"passrate-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Repeat Student', $3, 8, 'en', 'active', $4)
            """,
            uuid.UUID(student_id),
            f"auth0|pr-{student_id.replace('-', '')}",
            email,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', 8)
            """,
            uuid.UUID(school_id),
            email,
            uuid.UUID(student_id),
        )
        for _ in range(sessions):
            await conn.execute(
                """
                INSERT INTO progress_sessions
                    (student_id, unit_id, curriculum_id, grade, subject,
                     started_at, ended_at, score, total_questions, completed,
                     attempt_number, passed)
                VALUES ($1, $2, 'default-2026-g8', 8, 'Mathematics',
                        NOW(), NOW(), 5, 5, TRUE, 1, TRUE)
                """,
                uuid.UUID(student_id),
                _UNIT,
            )
    return student_id


@pytest.mark.asyncio
async def test_curriculum_health_pass_rate_never_exceeds_100(client, db_conn):
    """The exact table Venki screenshotted showing 200% and 300%."""
    school = await _register_school(client, "_health")
    await _student_with_repeated_first_attempts(client, school["school_id"], sessions=3)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    rates = [u["first_attempt_pass_rate_pct"] for u in r.json()["units"]]
    assert rates, "no units returned"
    for rate in rates:
        assert 0 <= rate <= 100, f"impossible pass rate: {rate}%"


@pytest.mark.asyncio
async def test_one_student_passing_first_time_reads_as_100_not_300(client, db_conn):
    """Three sessions from one student who passed first time is 100%, not 300%.

    Clamping would also satisfy the bound above while still being wrong, so this
    pins the actual value.
    """
    school = await _register_school(client, "_exact")
    await _student_with_repeated_first_attempts(client, school["school_id"], sessions=3)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["first_attempt_pass_rate_pct"] == 100.0, unit


@pytest.mark.asyncio
async def test_overview_struggle_ranking_uses_a_bounded_rate(client, db_conn):
    """The overview's struggle list ranks on the same per-unit rate.

    An inflated rate makes a struggling unit look healthy and drop off the list,
    so this is not merely cosmetic.
    """
    school = await _register_school(client, "_overview")
    await _student_with_repeated_first_attempts(client, school["school_id"], sessions=4)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/overview",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text
    # A unit passed on the first attempt must not be reported as struggling.
    assert _UNIT not in r.json()["units_with_struggles"]
