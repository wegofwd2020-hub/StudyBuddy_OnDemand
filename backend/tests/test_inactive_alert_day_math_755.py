"""
tests/test_inactive_alert_day_math_755.py

"Incorrect day calculations" on the alerts screen (Venki, 14 Sep — #755):

    Shows "Not active – Open since 10 Sep 2026"
    Shows "nothing opened in 17 days" — but this calculation appears incorrect

The arithmetic was right. Both numbers were right. The screen was wrong.

`triggered_at` is when the ALERT opened; `days_inactive` is how long the
STUDENT has been away. They rarely match, because the alert fires only once a
student crosses the threshold — a student idle since 27 Aug trips a 14-day
threshold on 10 Sep and is at 17 days by the 14th. Rendered side by side with
nothing saying which is which, a reader reconciles them, fails, and reports a
calculation bug. That is what happened.

Checked against the demo while diagnosing: Davis Charlie's card read "Open
since 10 Sep" next to "nothing opened in 66 days" — 66 days back is 12 July.
Correct, and unreadable.

The second defect is real rather than cosmetic. `last_active_at` floors at
`se.added_at`, so for a student who has NEVER opened anything `days_inactive`
counts days since ENROLMENT. Three students on the demo — zero lesson_views,
zero progress_sessions — were being reported as "nothing opened in 101 days",
which is true and misleading: they did not lapse, they never began. Those need
onboarding, not re-engagement, and the alert could not tell a teacher which.
Same distinction #590 drew between `not_started` and `in_progress` for units.

`never_active` is therefore reported as its own fact rather than inferred from
a day count that means two different things.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.reports.service import find_inactive_students, raise_inactive_student_alert


async def _school(client: AsyncClient, suffix: str) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Inactive Alert School{suffix}",
            "contact_email": f"ina{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _student(
    client: AsyncClient,
    school_id: str,
    *,
    enrolled_days_ago: int,
    last_active_days_ago: int | None,
) -> str:
    """`last_active_days_ago=None` means the student has NEVER opened anything."""
    student_id = str(uuid.uuid4())
    email = f"ina-{student_id[:8]}@example.com"
    added_at = datetime.now(UTC) - timedelta(days=enrolled_days_ago)
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Inactive Student', 8, 'en', $4)
            """,
            uuid.UUID(student_id),
            f"auth0|ina-{student_id.replace('-', '')}",
            email,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_id, student_email, grade, status, added_at)
            VALUES ($1, $2, $3, 8, 'active', $4)
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
            email,
            added_at,
        )
        if last_active_days_ago is not None:
            await conn.execute(
                """
                INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s, started_at)
                VALUES ($1, 'INA-UNIT-1', 'default-2026-g8', 60, $2)
                """,
                uuid.UUID(student_id),
                datetime.now(UTC) - timedelta(days=last_active_days_ago),
            )
    return student_id


def _row_for(rows, student_id: str):
    return next((r for r in rows if r["student_id"] == student_id), None)


def _about(actual: int, expected: int) -> bool:
    """Within a day of `expected`.

    `NOW()` in Postgres is the TRANSACTION start time, not the statement time.
    These tests insert their timestamps from Python's clock after that
    transaction has already begun, so the interval is a hair under a whole
    number of days and `EXTRACT(DAY ...)` truncates down. Production is
    unaffected — the daily Celery task opens a fresh connection per run — so the
    tolerance belongs here rather than a `clock_timestamp()` in the query, which
    would change live behaviour to suit a fixture.

    The tolerance costs nothing that matters: every assertion below distinguishes
    days-since-ACTIVITY from days-since-ENROLMENT, and those differ by tens of
    days, not one.
    """
    return abs(actual - expected) <= 1


# ── The real defect: "never started" is not "stopped" ─────────────────────────


@pytest.mark.asyncio
async def test_a_student_who_never_started_is_flagged_as_such(client, db_conn):
    """Three students on the demo had ZERO activity and were reported as
    "nothing opened in 101 days" — days since enrolment wearing the label of
    days since activity."""
    school_id = await _school(client, "_never")
    sid = await _student(client, school_id, enrolled_days_ago=101, last_active_days_ago=None)

    rows = await find_inactive_students(db_conn, school_id, 14)
    row = _row_for(rows, sid)

    assert row is not None, "a student who never started is still inactive"
    assert row["never_active"] is True
    # The count is days since ENROLMENT for this student, which is exactly why
    # it must be labelled differently on screen.
    assert _about(row["days_inactive"], 101)


@pytest.mark.asyncio
async def test_a_student_who_lapsed_is_not_flagged_as_never_active(client, db_conn):
    """The negative case. Without it, `never_active` could be hardcoded true
    and every assertion above would still pass."""
    school_id = await _school(client, "_lapsed")
    sid = await _student(client, school_id, enrolled_days_ago=97, last_active_days_ago=66)

    rows = await find_inactive_students(db_conn, school_id, 14)
    row = _row_for(rows, sid)

    assert row is not None
    assert row["never_active"] is False
    # Days since ACTIVITY, not since enrolment — the two differ by 31 here, and
    # a single label covering both is what made the screen unreadable.
    assert _about(row["days_inactive"], 66)
    # The point: 66 is days since ACTIVITY, not the 97 since enrolment.
    assert not _about(row["days_inactive"], 97)


@pytest.mark.asyncio
async def test_activity_via_quiz_alone_still_counts_as_started(client, db_conn):
    """`never_active` must consider BOTH activity tables. Reading only
    lesson_views would label a student who takes quizzes as never having
    started — the #569 shape, where one of two view types was the only one
    counted."""
    school_id = await _school(client, "_quiz")
    sid = await _student(client, school_id, enrolled_days_ago=90, last_active_days_ago=None)
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions, started_at)
            VALUES ($1, 'INA-UNIT-1', 'default-2026-g8', 8, 'Mathematics',
                    1, TRUE, TRUE, 7, 8, $2)
            """,
            uuid.UUID(sid),
            datetime.now(UTC) - timedelta(days=40),
        )

    rows = await find_inactive_students(db_conn, school_id, 14)
    row = _row_for(rows, sid)

    assert row is not None
    assert row["never_active"] is False, "a quiz is activity"
    assert _about(row["days_inactive"], 40)


# ── The threshold still behaves ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_recently_enrolled_student_is_not_flagged(client, db_conn):
    """`added_at` as the floor is the reason this works: without it a student
    enrolled yesterday who has opened nothing would read as inactive since the
    epoch and be alerted on immediately."""
    school_id = await _school(client, "_new")
    sid = await _student(client, school_id, enrolled_days_ago=2, last_active_days_ago=None)

    rows = await find_inactive_students(db_conn, school_id, 14)

    assert _row_for(rows, sid) is None, "two days enrolled is not inactivity"


@pytest.mark.asyncio
async def test_an_active_student_is_not_flagged(client, db_conn):
    school_id = await _school(client, "_active")
    sid = await _student(client, school_id, enrolled_days_ago=90, last_active_days_ago=1)

    rows = await find_inactive_students(db_conn, school_id, 14)

    assert _row_for(rows, sid) is None


# ── The flag survives into the alert the screen reads ─────────────────────────


@pytest.mark.asyncio
async def test_never_active_reaches_the_alert_details(client, db_conn):
    """The screen renders from `details`, so the flag is worth nothing unless it
    lands there."""
    school_id = await _school(client, "_details")
    sid = await _student(client, school_id, enrolled_days_ago=101, last_active_days_ago=None)

    await raise_inactive_student_alert(db_conn, school_id, sid, 101, never_active=True)

    row = await db_conn.fetchrow(
        """
        SELECT details FROM report_alerts
        WHERE school_id = $1 AND alert_type = 'inactive_students'
          AND details->>'student_id' = $2
        """,
        uuid.UUID(school_id),
        sid,
    )
    assert row is not None
    import json

    details = json.loads(row["details"]) if isinstance(row["details"], str) else row["details"]
    assert details["never_active"] is True
    assert details["days_inactive"] == 101


@pytest.mark.asyncio
async def test_refreshing_an_alert_updates_the_flag_and_the_count(client, db_conn):
    """A student who finally opens something while the alert is still open
    stops being `never_active`. The alert must not keep saying they never
    started — that is the stale-snapshot failure the day count was already
    designed to avoid."""
    school_id = await _school(client, "_refresh")
    sid = await _student(client, school_id, enrolled_days_ago=101, last_active_days_ago=None)

    await raise_inactive_student_alert(db_conn, school_id, sid, 101, never_active=True)
    await raise_inactive_student_alert(db_conn, school_id, sid, 20, never_active=False)

    rows = await db_conn.fetch(
        """
        SELECT details FROM report_alerts
        WHERE school_id = $1 AND alert_type = 'inactive_students'
          AND details->>'student_id' = $2 AND resolved_at IS NULL
        """,
        uuid.UUID(school_id),
        sid,
    )
    assert len(rows) == 1, "refreshing must not open a second alert"

    import json

    d = rows[0]["details"]
    details = json.loads(d) if isinstance(d, str) else d
    assert details["never_active"] is False
    assert details["days_inactive"] == 20
