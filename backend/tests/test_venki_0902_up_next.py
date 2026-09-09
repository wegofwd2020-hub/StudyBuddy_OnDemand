"""
tests/test_venki_0902_up_next.py

"Up next" on the student dashboard (Venki, 2 Sep):

    "Whether any pattern is followed to show this in the Dash board ?"

There was meant to be one -- "the first unit in curriculum order you have not
passed" -- and it was not working. The query ordered by `curriculum_units.
sort_order` alone, and that column does not sequence units: on the demo it holds
at most 5-6 distinct values across ~19 units (it groups by SUBJECT), and in 8
curricula, including the Grade 10 one he was looking at, it is 0 for every row.

With every key tied, Postgres makes no promise about which row comes first, so
"the first unpassed unit" was whichever one the planner happened to return --
and could move after any update or replan. His card offered a Technology unit
while four Science units sat unpassed.

The fix orders identically to the Subjects page the student actually browses
(`curriculum/router.py`): subject, then sort_order, then unit_id. That makes the
rule statable ("the first unpassed unit in the order you already see") and makes
it stable, which is the part a test can hold.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

# The UNCACHED builder on purpose. `get_dashboard` sits behind an L1
# TTLCache plus L2 Redis, so calling it five times would answer from cache
# and the determinism test below would pass without ever re-running the
# query it exists to pin.
from src.student.service import _build_dashboard


async def _school(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Up Next School",
            "contact_email": f"upnext{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _curriculum_all_tied(
    client: AsyncClient, school_id: str, grade: int
) -> tuple[str, list[str]]:
    """A curriculum whose `sort_order` is 0 for every unit -- the demo's actual
    shape for Grade 10, and the condition that made the ordering arbitrary.

    Units are inserted in an order that does NOT match the intended one, so a
    query relying on insertion/physical order would pick the wrong unit.
    """
    cid = f"upnext-{uuid.uuid4().hex[:8]}"
    units = [
        ("UN-TECH-001", "Technology"),
        ("UN-SCI-002", "Science"),
        ("UN-SCI-001", "Science"),
        ("UN-MATH-001", "Mathematics"),
    ]
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id, is_default)
            VALUES ($1, 'Up Next Curriculum', $2, 2026, 'school', $3, FALSE)
            """,
            cid,
            grade,
            uuid.UUID(school_id),
        )
        for unit_id, subject in units:
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, 0)
                """,
                unit_id,
                cid,
                subject,
                f"Title {unit_id}",
            )
    return cid, [u for u, _ in units]


async def _student(client: AsyncClient, school_id: str, grade: int) -> str:
    student_id = str(uuid.uuid4())
    email = f"upnext-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Up Next Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|upnext-{student_id.replace('-', '')}",
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


async def _pass(client, student_id: str, unit_id: str, cid: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 10, 'Science', 1, TRUE, TRUE, 7, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
        )



async def _next_unit_of(client, db_conn, fake_redis, student_id: str):
    """One uncached dashboard build."""
    return await _build_dashboard(
        db_conn,
        fake_redis,
        student_id,
        pool=client._transport.app.state.pool,
        grade=10,
    )


@pytest.mark.asyncio
async def test_up_next_follows_the_order_the_student_browses(client, db_conn, fake_redis):
    """Subject, then unit id -- the same order as the Subjects page.

    With `sort_order` tied at 0 the old query returned an arbitrary row; here it
    must be Mathematics before Science before Technology, so `UN-MATH-001`.
    """
    school_id = await _school(client)
    cid, _ = await _curriculum_all_tied(client, school_id, 10)
    student_id = await _student(client, school_id, 10)

    dash = await _next_unit_of(client, db_conn, fake_redis, student_id)

    assert dash["next_unit"] is not None
    assert dash["next_unit"]["unit_id"] == "UN-MATH-001"


@pytest.mark.asyncio
async def test_up_next_advances_only_past_units_actually_passed(client, db_conn, fake_redis):
    """Passing the first unit moves the card to the next one in that same order,
    not to an arbitrary other subject."""
    school_id = await _school(client)
    cid, _ = await _curriculum_all_tied(client, school_id, 10)
    student_id = await _student(client, school_id, 10)

    await _pass(client, student_id, "UN-MATH-001", cid)
    dash = await _next_unit_of(client, db_conn, fake_redis, student_id)
    assert dash["next_unit"]["unit_id"] == "UN-SCI-001", "Science 001 before Science 002"

    await _pass(client, student_id, "UN-SCI-001", cid)
    dash = await _next_unit_of(client, db_conn, fake_redis, student_id)
    assert dash["next_unit"]["unit_id"] == "UN-SCI-002"

    await _pass(client, student_id, "UN-SCI-002", cid)
    dash = await _next_unit_of(client, db_conn, fake_redis, student_id)
    assert dash["next_unit"]["unit_id"] == "UN-TECH-001", "Technology last, not first"


@pytest.mark.asyncio
async def test_up_next_does_not_move_between_loads(client, db_conn, fake_redis):
    """A weaker guard than the two ordering tests above, and deliberately kept.

    Restoring the old `ORDER BY cu.sort_order` does NOT fail this one: Postgres
    returns a consistent order for the same query against unchanged data, so
    repetition alone cannot expose an unspecified sort. The tests that actually
    catch the bug are the two above, which pin WHICH unit comes first.

    This holds the property going forward -- that the card does not move between
    loads -- which is what a future change (a new index, a plan flip, a parallel
    scan) would otherwise break silently.
    """
    school_id = await _school(client)
    cid, _ = await _curriculum_all_tied(client, school_id, 10)
    student_id = await _student(client, school_id, 10)

    seen = {
        (await _next_unit_of(client, db_conn, fake_redis, student_id))["next_unit"]["unit_id"]
        for _ in range(5)
    }
    assert len(seen) == 1, f"'Up next' moved between loads: {seen}"


@pytest.mark.asyncio
async def test_no_next_unit_once_everything_is_passed(client, db_conn, fake_redis):
    """The card gives way to "you've passed every unit" rather than repeating
    the last one."""
    school_id = await _school(client)
    cid, units = await _curriculum_all_tied(client, school_id, 10)
    student_id = await _student(client, school_id, 10)

    for unit_id in units:
        await _pass(client, student_id, unit_id, cid)

    dash = await _next_unit_of(client, db_conn, fake_redis, student_id)
    assert dash["next_unit"] is None
