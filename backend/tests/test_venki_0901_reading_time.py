"""Venki's 1 Sep round — "still feel there is some issue in the calculation of
Reading time & time shown against each unit."

He had already been answered once on this and came back, which is usually a sign
the answer addressed the wrong thing. It had: the tile and the column were two
different quantities over two different populations, so no arithmetic a teacher
might try could reconcile them.

  * the "Reading time" tile was SUM(duration_s) over every one of the student's
    lesson_views rows;
  * the per-unit "Time" column was AVG(lv.duration_s) — an average, under a
    heading that reads as a total;
  * and the table was built FROM progress_sessions, so a unit the student READ
    but never quizzed had no row at all, while its minutes were still inside the
    tile and it was still counted by `units_in_progress` (which reads
    lesson_views).

So the tile counted units the table would not show, and the column held a
different kind of number from the tile. Both are fixed by aggregating each side
to one row per unit and joining them FULL OUTER.

Every fixture below uses durations that DIFFER between sum and average. Equal
values would pass either formula and prove nothing — which is the trap the
earlier round's tests fell into.
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
            "school_name": f"Time School{suffix}",
            "contact_email": f"time{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _curriculum(client: AsyncClient, grade: int, units: list[str]) -> str:
    cid = f"time-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Time Curriculum', $2, 2026, 'platform', TRUE)
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
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Time Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|time-{student_id.replace('-', '')}",
            f"time-{student_id[:8]}@example.com",
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
            f"time-{student_id[:8]}@example.com",
            grade,
        )
    return student_id


async def _view(client, student_id, unit_id, cid, duration_s: int | None) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, duration_s)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            duration_s,
        )


async def _session(client, student_id, unit_id, cid) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 10, 'Mathematics', 1, TRUE, TRUE, 5, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
        )


def _row(report: dict, unit_id: str) -> dict | None:
    for u in report["per_unit"]:
        if u["unit_id"] == unit_id:
            return u
    return None


# ── The column is a total, not an average ─────────────────────────────────────


@pytest.mark.asyncio
async def test_per_unit_time_is_the_sum_of_the_views(client, db_conn):
    """Three views of 300s each: 900 total, 300 average. The two differ, so this
    fixture can tell which formula ran — the point Venki's report turned on."""
    school = await _school(client, "_sum")
    cid = await _curriculum(client, 10, ["TIME-SUM-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    await _session(client, student_id, "TIME-SUM-1", cid)
    for _ in range(3):
        await _view(client, student_id, "TIME-SUM-1", cid, 300)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    assert _row(report, "TIME-SUM-1")["total_duration_s"] == 900


@pytest.mark.asyncio
async def test_the_column_adds_up_to_the_tile(client, db_conn):
    """The reconciliation itself. A teacher who adds the column must reach the
    "Reading time" tile — the arithmetic the screen invites and used to refuse.

    Uneven durations across two units, so a wrong grouping cannot land on the
    right total by accident.
    """
    school = await _school(client, "_recon")
    cid = await _curriculum(client, 10, ["TIME-REC-1", "TIME-REC-2"])
    student_id = await _enrol(client, school["school_id"], 10)

    await _session(client, student_id, "TIME-REC-1", cid)
    await _view(client, student_id, "TIME-REC-1", cid, 120)
    await _view(client, student_id, "TIME-REC-1", cid, 60)
    await _session(client, student_id, "TIME-REC-2", cid)
    await _view(client, student_id, "TIME-REC-2", cid, 400)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    column_total = sum(u["total_duration_s"] for u in report["per_unit"])
    assert column_total == report["total_time_spent_s"] == 580


@pytest.mark.asyncio
async def test_many_quiz_attempts_do_not_multiply_the_time(client, db_conn):
    """The old query joined sessions to views without collapsing either side.
    That did not distort AVG — a uniform cartesian averages to the same number —
    but it does distort a SUM, which is why each side is aggregated BEFORE the
    join rather than the function simply being swapped.

    Four sessions, one 200s view: the answer is 200, not 800.
    """
    school = await _school(client, "_fanout")
    cid = await _curriculum(client, 10, ["TIME-FAN-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    for _ in range(4):
        await _session(client, student_id, "TIME-FAN-1", cid)
    await _view(client, student_id, "TIME-FAN-1", cid, 200)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    assert _row(report, "TIME-FAN-1")["total_duration_s"] == 200


# ── A unit that was read but never quizzed still appears ──────────────────────


@pytest.mark.asyncio
async def test_a_unit_read_but_never_quizzed_gets_a_row(client, db_conn):
    """This is what made the screen irreconcilable rather than merely wrong.

    The table came FROM progress_sessions. A unit the student opened and read but
    never took a quiz on had NO row — while its minutes sat inside the "Reading
    time" tile and `units_in_progress` counted it. The tiles counted units the
    table would not show.
    """
    school = await _school(client, "_readonly")
    cid = await _curriculum(client, 10, ["TIME-READ-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    # Read it, never quizzed it.
    await _view(client, student_id, "TIME-READ-1", cid, 240)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    row = _row(report, "TIME-READ-1")
    assert row is not None, "a unit the student read must appear in the table"
    assert row["total_duration_s"] == 240
    assert row["lesson_viewed"] is True
    assert row["quiz_attempts"] == 0
    assert row["best_score"] is None
    assert row["passed"] is False
    # And it reconciles, which is the whole reason the row has to exist.
    assert sum(u["total_duration_s"] for u in report["per_unit"]) == (
        report["total_time_spent_s"]
    )


@pytest.mark.asyncio
async def test_a_unit_quizzed_but_never_read_still_appears(client, db_conn):
    """The other side of the FULL OUTER join. Quizzes can currently be taken
    without opening the lesson, so this row is real — it must show zero reading
    time rather than vanish."""
    school = await _school(client, "_quizonly")
    cid = await _curriculum(client, 10, ["TIME-QUIZ-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    await _session(client, student_id, "TIME-QUIZ-1", cid)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    row = _row(report, "TIME-QUIZ-1")
    assert row is not None
    assert row["total_duration_s"] == 0
    assert row["lesson_viewed"] is False
    assert row["quiz_attempts"] == 1


@pytest.mark.asyncio
async def test_a_view_with_no_recorded_duration_does_not_break_the_total(client, db_conn):
    """`duration_s` is NULL when the end beacon never arrived (#464). SUM skips
    NULLs on both sides, so a lost beacon costs minutes but never desynchronises
    the tile from the column.

    Three views — NULL, 150 and 250 — chosen so SUM (400) and AVG (200) differ.
    With only NULL and 150 both formulas answer 150, and this test passed against
    the very implementation it is meant to reject.
    """
    school = await _school(client, "_nulldur")
    cid = await _curriculum(client, 10, ["TIME-NULL-1"])
    student_id = await _enrol(client, school["school_id"], 10)

    await _session(client, student_id, "TIME-NULL-1", cid)
    await _view(client, student_id, "TIME-NULL-1", cid, None)
    await _view(client, student_id, "TIME-NULL-1", cid, 150)
    await _view(client, student_id, "TIME-NULL-1", cid, 250)

    report = await get_student_report(db_conn, school["school_id"], student_id)
    row = _row(report, "TIME-NULL-1")
    assert row["total_duration_s"] == 400
    assert row["lesson_viewed"] is True
    assert sum(u["total_duration_s"] for u in report["per_unit"]) == (
        report["total_time_spent_s"]
    )
