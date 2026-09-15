"""
tests/test_report_scope_640.py

A report must say what population its figures cover (issue #640, design §10).

Since #576 a teacher's numbers mean THEIR GRADES and a school admin's mean the
whole school. Same tile, same label, two different populations — with nothing on
screen saying which. That silence is the defect the dashboard redesign was
actually reported for; §10 puts it plainly: "never the layout but the silence
about what the numbers cover".

Venki reported the symptom without recognising it as one:

    "Teacher Management shows Gr 8, 10, 11 but Student Progress offers
     8, 10, 11, 12"

Both lists were correct. They answer different questions — *what am I assigned
to teach* versus *what grades exist here* — and the page never said so.

## Why the SERVER reports it

The scope is derived from the same `_grade_filter` that scoped the query, and
returned alongside the numbers. Re-deriving it in the client would let the
caption drift from the data it describes: the page would keep saying "your
grades: 8, 10" after the filter had changed, which is worse than no caption at
all.

## The three states

    school            school_admin — unrestricted
    grades [8, 10]    a teacher, restricted
    grades []         a teacher with NO assignments

The third is real and distinct: they see nothing because nothing is in their
scope. Collapsing it into "school" is the pre-#576 bug (a teacher with no
assignments saw every student). Rendering it as a blank caption is the §4.2
empty-state problem — a grid of zeroes with no way to tell "not set up" from
"broken".
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_GRADE_A = 8
_GRADE_B = 10


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Scope School{suffix}",
            "contact_email": f"scope{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _add_teacher(client: AsyncClient, school_id: str, grades: list[int]) -> str:
    """A plain teacher (not school_admin) with the given grade assignments."""
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, name, email, role, account_status)
            VALUES ($1, $2, $3, 'Scope Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"auth0|scope-{teacher_id.replace('-', '')}",
            f"scope-{teacher_id[:8]}@example.com",
        )
        for g in grades:
            await conn.execute(
                """
                INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                g,
            )
    return teacher_id


async def _overview(client: AsyncClient, school_id: str, token: str) -> dict:
    r = await client.get(
        f"/api/v1/reports/school/{school_id}/overview?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_a_school_admin_is_told_the_figures_cover_the_whole_school(client, db_conn):
    school = await _register_school(client, "_admin")
    token = make_teacher_token(
        teacher_id=school["teacher_id"], school_id=school["school_id"], role="school_admin"
    )

    body = await _overview(client, school["school_id"], token)
    assert body["scope"]["kind"] == "school", body["scope"]
    assert body["scope"]["grades"] == [], body["scope"]


@pytest.mark.asyncio
async def test_a_teacher_is_told_which_grades_the_figures_cover(client, db_conn):
    school = await _register_school(client, "_teacher")
    teacher_id = await _add_teacher(client, school["school_id"], [_GRADE_A, _GRADE_B])
    token = make_teacher_token(
        teacher_id=teacher_id, school_id=school["school_id"], role="teacher"
    )

    body = await _overview(client, school["school_id"], token)
    assert body["scope"]["kind"] == "grades", body["scope"]
    assert sorted(body["scope"]["grades"]) == [_GRADE_A, _GRADE_B], body["scope"]


@pytest.mark.asyncio
async def test_a_teacher_with_no_assignments_is_a_distinct_state_not_school_wide(
    client, db_conn
):
    """The state that must never be collapsed into "school".

    Collapsing it is the pre-#576 bug — a teacher with no assignments saw every
    student in the school. The empty list is what lets the page explain its own
    zeroes instead of looking broken.
    """
    school = await _register_school(client, "_nograde")
    teacher_id = await _add_teacher(client, school["school_id"], [])
    token = make_teacher_token(
        teacher_id=teacher_id, school_id=school["school_id"], role="teacher"
    )

    body = await _overview(client, school["school_id"], token)
    assert body["scope"]["kind"] == "grades", body["scope"]
    assert body["scope"]["grades"] == [], body["scope"]


@pytest.mark.asyncio
async def test_the_reported_scope_matches_the_population_actually_counted(client, db_conn):
    """The caption must describe the data, not a guess about it.

    A teacher assigned only Grade 8 must not be told "whole school" while the
    query counted one grade — that mismatch is exactly what the client-side
    version of this would eventually produce.
    """
    school = await _register_school(client, "_match")
    teacher_id = await _add_teacher(client, school["school_id"], [_GRADE_A])
    token = make_teacher_token(
        teacher_id=teacher_id, school_id=school["school_id"], role="teacher"
    )

    body = await _overview(client, school["school_id"], token)
    admin_token = make_teacher_token(
        teacher_id=school["teacher_id"], school_id=school["school_id"], role="school_admin"
    )
    admin_body = await _overview(client, school["school_id"], admin_token)

    assert body["scope"]["grades"] == [_GRADE_A]
    assert admin_body["scope"]["kind"] == "school"
    # The admin's population is a superset — the two must not report the same
    # scope while returning differently-scoped numbers.
    assert body["scope"] != admin_body["scope"], (body["scope"], admin_body["scope"])
