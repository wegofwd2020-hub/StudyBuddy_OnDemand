"""Venki's 31 Aug round — the teacher-reporting half.

Two reports, one shape between them: a number that is right on its own terms and
wrong beside the number next to it.

  * "Quiz attempts per subject … totals 73 whereas quizzes completed shows 32 —
    are we missing something?" The subject bars counted every session row
    including abandoned ones; the tile beside them counted completions. On his
    data 58 of 91 sessions were never finished, so the two disagreed by more than
    a factor of two.

  * "Units completed count is not matching / In progress count is not matching."
    Both counted every unit the student had EVER touched, in any curriculum,
    while every other screen shows only what they are served now.

Both tests use data where the right and wrong formulas DISAGREE. A fixture where
they coincide passes either way and proves nothing.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import get_student_report


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Report School{suffix}",
            "contact_email": f"rep{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _curriculum(client: AsyncClient, grade: int, units: list[str]) -> str:
    cid = f"rep-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Report Curriculum', $2, 2026, 'platform', TRUE)
            """,
            cid,
            grade,
        )
        for i, unit in enumerate(units):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, 'Mathematics', $3, $3, $4)
                """,
                unit,
                cid,
                f"Unit {unit}",
                i,
            )
    return cid


async def _enrol(client: AsyncClient, school_id: str, grade: int) -> str:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Report Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|rep-{student_id.replace('-', '')}",
            f"rep-{student_id[:8]}@example.com",
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
            f"rep-{student_id[:8]}@example.com",
            grade,
        )
    return student_id


async def _session(client, student_id, unit_id, cid, *, completed, passed) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 10, 'Mathematics', 1, $4, $5, 5, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            completed,
            passed,
        )


# ── The subject breakdown ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subject_breakdown_counts_completed_not_every_session(client, db_conn):
    """Three sessions on one unit, ONE finished. The bar must read 1, not 3."""
    school = await _school(client, "_bars")
    cid = await _curriculum(client, 10, ["REP-BAR-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    await _session(client, student_id, "REP-BAR-1", cid, completed=True, passed=True)
    await _session(client, student_id, "REP-BAR-1", cid, completed=False, passed=False)
    await _session(client, student_id, "REP-BAR-1", cid, completed=False, passed=False)

    from tests.helpers.token_factory import make_student_token

    r = await client.get(
        "/api/v1/analytics/student/stats?period=30d",
        headers={"Authorization": f"Bearer {make_student_token(student_id, 10)}"},
    )
    assert r.status_code == 200, r.text
    bars = r.json().get("subject_breakdown") or []
    total = sum(b.get("attempts", 0) for b in bars)
    assert total == 1, f"expected 1 completed quiz across the bars, got {total}"


# ── The student report ────────────────────────────────────────────────────────
#
# "Units completed count is not matching / In progress count is not matching" is
# NOT fixed here, deliberately.
#
# The obvious change -- scope both to the curricula the student is served now --
# was written, tested, and backed out. Sessions record whichever curriculum was
# resolved AT THE TIME; the resolver returns what is resolved NOW. When a
# classroom's packages change those differ, and strict scoping does not trim the
# count so much as empty it: the first version of this test returned 0 where the
# student had genuinely passed a unit. Turning "11 units completed" into "0" is a
# worse answer than the mismatch being reported.
#
# What is missing is the comparison, not the code: which screen was he comparing
# against? Until that is known, changing a definition is a guess, and this
# particular guess can erase a student's record from their own report card.
