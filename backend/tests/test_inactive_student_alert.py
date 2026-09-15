"""A student who has stopped working produces a signal.

`inactive_days_threshold` has been settable since migration 0010 and read by
nothing. `evaluate_report_alerts_task` even SELECTed it and then never
referenced the value, so a school admin could set it, watch it persist, and
never get an alert (#735).

Two properties here matter more than the happy path:

  - a newly enrolled student is NOT instantly N days inactive (silence is
    measured from `added_at`, not from epoch), or the first thing a school sees
    after uploading a roster is an inbox full of alerts about students who have
    not had a chance to log in;

  - the alert reaches a grade-restricted TEACHER. It carries no unit, and
    `get_alerts` resolved grade only through `details->>'unit_id'` and withholds
    NULL-grade alerts from restricted teachers -- so without the student-grade
    fallback the alert would exist and be visible only to school admins, which
    for "your student has stopped working" is the wrong audience entirely.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from src.reports.service import (
    find_inactive_students,
    raise_inactive_student_alert,
    resolve_cleared_inactive_alerts,
)
from tests.helpers.token_factory import make_teacher_token

_GRADE = 9
_THRESHOLD = 14


def _hdr(teacher_id: str, school_id: str, role: str = "school_admin") -> dict:
    return {"Authorization": f"Bearer {make_teacher_token(teacher_id, school_id, role)}"}


def _pool(client: AsyncClient):
    return client._transport.app.state.pool


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Idle School{suffix}",
            "contact_email": f"idle{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_student(
    client: AsyncClient, school_id: str, name: str, *, enrolled_days_ago: int
) -> str:
    """A student enrolled `enrolled_days_ago` days ago, with no activity yet."""
    student_id = str(uuid.uuid4())
    email = f"idle-{student_id[:8]}@school.example.com"
    added_at = datetime.now(tz=timezone.utc) - timedelta(days=enrolled_days_ago)
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale,
                 account_status, school_id)
            VALUES ($1, $2, $3, $4, $5, 'en', 'active', $6)
            """,
            uuid.UUID(student_id),
            f"auth0|idle-{student_id.replace('-', '')}",
            name,
            email,
            _GRADE,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_email, student_id, status, grade, added_at)
            VALUES ($1, $2, $3, 'active', $4, $5)
            """,
            uuid.UUID(school_id),
            email,
            uuid.UUID(student_id),
            _GRADE,
            added_at,
        )
    return student_id


async def _seed_activity(client: AsyncClient, student_id: str, *, days_ago: int) -> None:
    when = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views (student_id, unit_id, curriculum_id, started_at)
            VALUES ($1, 'IDLE-UNIT-1', 'idle-curriculum', $2)
            """,
            uuid.UUID(student_id),
            when,
        )


async def _find(client: AsyncClient, school_id: str, days: int = _THRESHOLD) -> list:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await find_inactive_students(conn, school_id, days)


async def _raise(client: AsyncClient, school_id: str, student_id: str, days: int) -> None:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await raise_inactive_student_alert(conn, school_id, student_id, days)


async def _open_rows(client: AsyncClient, school_id: str) -> list:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetch(
            """
            SELECT alert_id, details, triggered_at FROM report_alerts
            WHERE school_id = $1 AND alert_type = 'inactive_students'
              AND resolved_at IS NULL AND NOT acknowledged
            ORDER BY triggered_at
            """,
            uuid.UUID(school_id),
        )


# ── Detection ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_student_silent_past_the_threshold_is_found(client, db_conn):
    school = await _register_school(client, "_hit")
    student = await _seed_student(client, school["school_id"], "Gone Quiet", enrolled_days_ago=60)
    await _seed_activity(client, student, days_ago=30)

    rows = await _find(client, school["school_id"])
    assert [r["student_id"] for r in rows] == [student]
    assert rows[0]["days_inactive"] >= 29


@pytest.mark.asyncio
async def test_recent_activity_keeps_a_student_out(client, db_conn):
    school = await _register_school(client, "_recent")
    student = await _seed_student(client, school["school_id"], "Still Here", enrolled_days_ago=60)
    await _seed_activity(client, student, days_ago=2)

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_a_quiz_counts_as_activity_not_only_a_lesson_view(client, db_conn):
    """Two independent histories. Reading only one of them alerts on a student
    who has been sitting quizzes all week."""
    school = await _register_school(client, "_quiz")
    student = await _seed_student(client, school["school_id"], "Quiz Only", enrolled_days_ago=60)
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at,
                 completed, attempt_number, passed)
            VALUES ($1, 'IDLE-UNIT-2', 'idle-curriculum', $2, 'Technology', NOW(),
                    TRUE, 1, TRUE)
            """,
            uuid.UUID(student),
            _GRADE,
        )

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_a_newly_enrolled_student_is_not_instantly_inactive(client, db_conn):
    """Silence is measured from `added_at`, not from epoch.

    Otherwise the first thing a school sees after uploading a roster is one
    alert per student, about students who have not had a chance to log in.
    """
    school = await _register_school(client, "_new")
    await _seed_student(client, school["school_id"], "Just Enrolled", enrolled_days_ago=1)

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_a_student_who_never_started_eventually_counts(client, db_conn):
    """Enrolled long ago and never opened anything IS the signal, not an exemption."""
    school = await _register_school(client, "_never")
    student = await _seed_student(client, school["school_id"], "Never Began", enrolled_days_ago=45)

    rows = await _find(client, school["school_id"])
    assert [r["student_id"] for r in rows] == [student]


@pytest.mark.asyncio
async def test_a_double_enrolment_yields_one_row_not_two(client, db_conn):
    """#623's fan-out. The unique index would collapse the duplicate alert, so
    the inbox would look right while the evaluator's count was wrong."""
    school = await _register_school(client, "_dup")
    student = await _seed_student(client, school["school_id"], "Twice", enrolled_days_ago=60)
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_email, student_id, status, grade, added_at)
            VALUES ($1, $2, $3, 'active', $4, NOW() - INTERVAL '60 days')
            """,
            uuid.UUID(school["school_id"]),
            f"dup-{uuid.uuid4().hex[:8]}@school.example.com",
            uuid.UUID(student),
            _GRADE,
        )

    rows = await _find(client, school["school_id"])
    assert len(rows) == 1, f"expected one row, got {len(rows)}"


# ── Dedup + withdrawal ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_repeat_refreshes_the_count_but_not_the_age(client, db_conn):
    school = await _register_school(client, "_repeat")
    student = await _seed_student(client, school["school_id"], "Repeat", enrolled_days_ago=60)

    await _raise(client, school["school_id"], student, 20)
    first = (await _open_rows(client, school["school_id"]))[0]
    await _raise(client, school["school_id"], student, 21)

    rows = await _open_rows(client, school["school_id"])
    assert len(rows) == 1, f"expected one open alert, got {len(rows)}"
    assert rows[0]["details"]["days_inactive"] == 21, "the count grows"
    assert rows[0]["triggered_at"] == first["triggered_at"], "the alert does not get younger"


@pytest.mark.asyncio
async def test_two_students_each_get_their_own_alert(client, db_conn):
    """This type carries NO unit_id -- migration 0066's exact trap. Through the
    old unit-keyed index every row would key on NULL, and NULLs are distinct."""
    school = await _register_school(client, "_two")
    a = await _seed_student(client, school["school_id"], "A", enrolled_days_ago=60)
    b = await _seed_student(client, school["school_id"], "B", enrolled_days_ago=60)

    await _raise(client, school["school_id"], a, 20)
    await _raise(client, school["school_id"], b, 20)

    rows = await _open_rows(client, school["school_id"])
    assert len(rows) == 2
    assert {r["details"]["student_id"] for r in rows} == {a, b}


@pytest.mark.asyncio
async def test_coming_back_resolves_the_alert(client, db_conn):
    school = await _register_school(client, "_back")
    student = await _seed_student(client, school["school_id"], "Returned", enrolled_days_ago=60)
    await _raise(client, school["school_id"], student, 20)

    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        n = await resolve_cleared_inactive_alerts(conn, school["school_id"], still_inactive=[])

    assert n == 1
    assert await _open_rows(client, school["school_id"]) == []


# ── The endpoint, and who can see it ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_alert_reaches_the_inbox_named(client, db_conn):
    school = await _register_school(client, "_inbox")
    student = await _seed_student(client, school["school_id"], "Priya Raman", enrolled_days_ago=60)
    await _raise(client, school["school_id"], student, 21)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    assert r.status_code == 200, r.text
    alert = next(a for a in r.json()["alerts"] if a["alert_type"] == "inactive_students")
    assert alert["student_name"] == "Priya Raman"
    assert alert["details"]["days_inactive"] == 21
    # No unit anywhere -- this alert is about a person, not a topic.
    assert alert["unit_title"] is None


@pytest.mark.asyncio
async def test_a_teacher_of_that_grade_can_see_it(client, db_conn):
    """The fallback under test. This alert carries no unit, and grade was
    resolved only through `details->>'unit_id'` -- so it would have been
    withheld from every grade-restricted teacher and shown to admins alone.
    """
    school = await _register_school(client, "_scope")
    student = await _seed_student(client, school["school_id"], "Scoped In", enrolled_days_ago=60)
    await _raise(client, school["school_id"], student, 21)

    teacher_id = str(uuid.uuid4())
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, name, email, role, account_status)
            VALUES ($1, $2, $3, 'Their Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school["school_id"]),
            f"auth0|t-{teacher_id.replace('-', '')}",
            f"t-{teacher_id[:8]}@school.example.com",
        )
        await conn.execute(
            "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
            " VALUES ($1, $2, $3)",
            uuid.UUID(teacher_id),
            uuid.UUID(school["school_id"]),
            _GRADE,
        )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(teacher_id, school["school_id"], role="teacher"),
    )
    assert r.status_code == 200, r.text
    types = [a["alert_type"] for a in r.json()["alerts"]]
    assert "inactive_students" in types, "grade fallback did not resolve"


@pytest.mark.asyncio
async def test_a_teacher_of_another_grade_cannot(client, db_conn):
    """...and the fallback must not become a way around scoping (#576, FERPA)."""
    school = await _register_school(client, "_otherscope")
    student = await _seed_student(client, school["school_id"], "Not Yours", enrolled_days_ago=60)
    await _raise(client, school["school_id"], student, 21)

    teacher_id = str(uuid.uuid4())
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, name, email, role, account_status)
            VALUES ($1, $2, $3, 'Other Grade', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school["school_id"]),
            f"auth0|o-{teacher_id.replace('-', '')}",
            f"o-{teacher_id[:8]}@school.example.com",
        )
        await conn.execute(
            "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
            " VALUES ($1, $2, $3)",
            uuid.UUID(teacher_id),
            uuid.UUID(school["school_id"]),
            _GRADE - 1,
        )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(teacher_id, school["school_id"], role="teacher"),
    )
    assert r.status_code == 200, r.text
    types = [a["alert_type"] for a in r.json()["alerts"]]
    assert "inactive_students" not in types


# ── Settings ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_dead_thresholds_are_no_longer_offered(client, db_conn):
    """#735. A control that persists and does nothing is worse than no control."""
    school = await _register_school(client, "_settings")
    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts/settings",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert "score_drop_threshold" not in body
    assert "feedback_count_threshold" not in body
    # The ones the evaluator actually reads stay.
    assert body["inactive_days_threshold"] == 14
    assert body["pass_rate_threshold"] == 50.0
    assert body["stuck_attempts_threshold"] == 3
