"""A student who never passes a unit produces a signal.

Reported by Venki 2026-09-02, against a student card reading
`Attempt #11 · Score 3/8`: "Why was this not shown in the Alerts section?"

It could not have been. Every alert type before this one is UNIT-grained — the
evaluator runs `GROUP BY ps.unit_id`, so `student_id` survives only inside
`COUNT(DISTINCT …)` and is consumed by the aggregate. Both sides of the pass-rate
ratio also filter `attempt_number = 1`, so attempts 2..N are invisible.

These tests call `find_stuck_students` / `raise_stuck_student_alert` /
`resolve_cleared_stuck_alerts` — the same functions the Celery task calls —
rather than re-typing their SQL, for the reason `test_report_alerts_dedupe.py`
gives: re-typed SQL only proves the copy agrees with itself, which is how a
dedupe that could never fire survived for months.

The NEGATIVE cases carry as much weight as the positive ones. A threshold that
fires on ordinary revision would be worse than the silence it replaces, and the
reported history is itself a negative case — see
`test_the_reported_history_does_not_fire`.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import (
    find_stuck_students,
    raise_pass_rate_alert,
    raise_stuck_student_alert,
    resolve_cleared_stuck_alerts,
)
from tests.helpers.token_factory import make_teacher_token

_GRADE = 10
_CURRICULUM = "stuck-test-curriculum"


def _hdr(teacher_id: str, school_id: str, role: str = "school_admin") -> dict:
    return {"Authorization": f"Bearer {make_teacher_token(teacher_id, school_id, role)}"}


def _pool(client: AsyncClient):
    return client._transport.app.state.pool


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Stuck School{suffix}",
            "contact_email": f"stuck{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_unit(client: AsyncClient, unit_id: str, title: str) -> None:
    """A platform curriculum holding `unit_id`, so grade and title resolve."""
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        curriculum_id = f"{_CURRICULUM}-{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Stuck Curriculum', $2, 2026, 'platform', FALSE)
            """,
            curriculum_id,
            _GRADE,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Technology', $3, $3, 1)
            """,
            unit_id,
            curriculum_id,
            title,
        )


async def _seed_student(client: AsyncClient, school_id: str, name: str) -> str:
    student_id = str(uuid.uuid4())
    email = f"stuck-{student_id[:8]}@school.example.com"
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
            f"auth0|stuck-{student_id.replace('-', '')}",
            name,
            email,
            _GRADE,
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
            _GRADE,
        )
    return student_id


async def _second_active_enrolment(client: AsyncClient, school_id: str, student_id: str) -> None:
    """A second ACTIVE enrolment row for the same student at the same school.

    Not hypothetical: this is the shape that let a unit's pass rate exceed 100%
    (#623) and weighted the health averages by lesson-view count (#625).
    """
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', $4)
            """,
            uuid.UUID(school_id),
            f"dup-{uuid.uuid4().hex[:8]}@school.example.com",
            uuid.UUID(student_id),
            _GRADE,
        )


async def _seed_sessions(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    history: list[tuple[int, bool | None, bool]],
) -> None:
    """`history` is a list of (attempt_number, passed, completed)."""
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for attempt, passed, completed in history:
            await conn.execute(
                """
                INSERT INTO progress_sessions
                    (student_id, unit_id, curriculum_id, grade, subject,
                     started_at, ended_at, score, total_questions,
                     completed, attempt_number, passed)
                VALUES ($1, $2, $3, $4, 'Technology',
                        NOW(), NOW(), $5, 8, $6, $7, $8)
                """,
                uuid.UUID(student_id),
                unit_id,
                _CURRICULUM,
                _GRADE,
                6 if passed else 3,
                completed,
                attempt,
                passed,
            )


async def _find(client: AsyncClient, school_id: str, threshold: int = 3) -> list:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await find_stuck_students(conn, school_id, threshold)


async def _raise(
    client: AsyncClient, school_id: str, student_id: str, unit_id: str, failed: int
) -> None:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await raise_stuck_student_alert(conn, school_id, student_id, unit_id, failed)


async def _open_stuck(client: AsyncClient, school_id: str) -> list:
    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetch(
            """
            SELECT alert_id, details, triggered_at
            FROM report_alerts
            WHERE school_id = $1 AND alert_type = 'student_stuck_on_unit'
              AND resolved_at IS NULL AND NOT acknowledged
            ORDER BY triggered_at
            """,
            uuid.UUID(school_id),
        )


# ── Detection ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_never_passed_after_threshold_is_stuck(client, db_conn):
    school = await _register_school(client, "_hit")
    await _seed_unit(client, "STUCK-HIT-1", "Software Development Lifecycle")
    student = await _seed_student(client, school["school_id"], "Priya Raman")
    await _seed_sessions(
        client,
        student,
        "STUCK-HIT-1",
        [(1, False, True), (2, False, True), (3, False, True)],
    )

    rows = await _find(client, school["school_id"])
    assert [(r["student_id"], r["unit_id"]) for r in rows] == [(student, "STUCK-HIT-1")]
    assert rows[0]["failed_attempts"] == 3


@pytest.mark.asyncio
async def test_below_threshold_is_silent(client, db_conn):
    school = await _register_school(client, "_below")
    await _seed_unit(client, "STUCK-BELOW-1", "Data Structures")
    student = await _seed_student(client, school["school_id"], "Below Threshold")
    await _seed_sessions(client, student, "STUCK-BELOW-1", [(1, False, True), (2, False, True)])

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_the_reported_history_does_not_fire(client, db_conn):
    """Pass, then fail, is revision — not stuck.

    The exact history behind the 2026-09-02 report: attempt 1 failed, attempts
    2-10 passed, attempt 11 failed. One slip after nine passes. A threshold low
    enough to fire here fires on everyone who revises, which is noise in an inbox
    migration 0066 just cut from 294 rows to 13.
    """
    school = await _register_school(client, "_venki")
    await _seed_unit(client, "STUCK-VENKI-1", "Software Development Lifecycle")
    student = await _seed_student(client, school["school_id"], "Reported Student")
    history = [(1, False, True)] + [(n, True, True) for n in range(2, 11)] + [(11, False, True)]
    await _seed_sessions(client, student, "STUCK-VENKI-1", history)

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_abandoned_sessions_are_not_failures(client, db_conn):
    """`passed IS NULL` with `completed = FALSE` is an abandoned attempt.

    Guards the `completed AND NOT passed` FILTER — that an unfinished attempt is
    not counted as a failure. Mutating it to `NOT COALESCE(passed, FALSE)` (a
    plausible reading of "didn't pass") fails this with `failed_attempts=3`.

    It does NOT guard the COALESCE around BOOL_OR, which an earlier draft of this
    docstring claimed. That branch is unreachable: `NULL AND FALSE` is FALSE, so
    BOOL_OR yields NULL only when every row is (completed, passed IS NULL), and
    those rows contribute 0 to `failed_attempts` and never reach the threshold.
    Removing the COALESCE fails nothing. Recorded here so the next person does not
    trust a guard that is not there.
    """
    school = await _register_school(client, "_abandoned")
    await _seed_unit(client, "STUCK-ABANDON-1", "Cloud Computing")
    student = await _seed_student(client, school["school_id"], "Abandoner")
    await _seed_sessions(
        client,
        student,
        "STUCK-ABANDON-1",
        [(1, None, False), (2, None, False), (3, None, False)],
    )

    assert await _find(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_double_enrolment_does_not_inflate_the_count(client, db_conn):
    """Two active enrolments must not double `failed_attempts` (#623, #625).

    Without `COUNT(DISTINCT ps.session_id)` this student's 2 attempts read as 4
    and cross a threshold of 3 — an alert about a student who is not stuck.
    """
    school = await _register_school(client, "_fanout")
    await _seed_unit(client, "STUCK-FANOUT-1", "Digital Citizenship")
    student = await _seed_student(client, school["school_id"], "Twice Enrolled")
    await _second_active_enrolment(client, school["school_id"], student)
    await _seed_sessions(client, student, "STUCK-FANOUT-1", [(1, False, True), (2, False, True)])

    assert await _find(client, school["school_id"]) == []


# ── Deduplication: the trap migration 0066 left ───────────────────────────────


@pytest.mark.asyncio
async def test_two_students_same_unit_both_get_an_alert(client, db_conn):
    """Keyed on unit alone, the second student silently DO UPDATEs the first.

    This is the failure mode `uq_report_alerts_open_stuck` exists to prevent, and
    it is suppression rather than duplication — strictly worse, because nothing
    on screen indicates a student is missing.
    """
    school = await _register_school(client, "_two")
    await _seed_unit(client, "STUCK-TWO-1", "Introduction to Computing")
    a = await _seed_student(client, school["school_id"], "Student A")
    b = await _seed_student(client, school["school_id"], "Student B")

    await _raise(client, school["school_id"], a, "STUCK-TWO-1", 3)
    await _raise(client, school["school_id"], b, "STUCK-TWO-1", 3)

    rows = await _open_stuck(client, school["school_id"])
    assert len(rows) == 2
    assert {r["details"]["student_id"] for r in rows} == {a, b}


@pytest.mark.asyncio
async def test_same_student_twice_refreshes_one_alert(client, db_conn):
    """...and the dedupe still has to work in the other direction."""
    school = await _register_school(client, "_same")
    await _seed_unit(client, "STUCK-SAME-1", "Trigonometric Functions")
    student = await _seed_student(client, school["school_id"], "Repeat Student")

    await _raise(client, school["school_id"], student, "STUCK-SAME-1", 3)
    first = (await _open_stuck(client, school["school_id"]))[0]
    await _raise(client, school["school_id"], student, "STUCK-SAME-1", 4)

    rows = await _open_stuck(client, school["school_id"])
    assert len(rows) == 1, f"expected one open alert, got {len(rows)}"
    assert rows[0]["details"]["failed_attempts"] == 4, "count should be refreshed"
    assert rows[0]["triggered_at"] == first["triggered_at"], "age must not reset"
    assert rows[0]["alert_id"] == first["alert_id"], "should update, not replace"


@pytest.mark.asyncio
async def test_pass_rate_breach_dedupe_is_unaffected(client, db_conn):
    """Regression guard on narrowing `uq_report_alerts_open_unit` to one type.

    Widening the shared index to include `student_id` would have been the obvious
    move, and it would have broken this: `pass_rate_breach` carries no student_id,
    NULLs are distinct in a unique index, and the 69-duplicates-per-unit bug of
    migration 0066 comes straight back.
    """
    school = await _register_school(client, "_unaffected")
    await _seed_unit(client, "STUCK-PR-1", "Exponential Functions")

    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for _ in range(5):
            await raise_pass_rate_alert(conn, school["school_id"], "STUCK-PR-1", 0.0)
        n = await conn.fetchval(
            """
            SELECT COUNT(*) FROM report_alerts
            WHERE school_id = $1 AND alert_type = 'pass_rate_breach'
              AND resolved_at IS NULL AND NOT acknowledged
            """,
            uuid.UUID(school["school_id"]),
        )
    assert n == 1


# ── Withdrawal ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_passing_the_unit_resolves_the_alert(client, db_conn):
    school = await _register_school(client, "_resolve")
    await _seed_unit(client, "STUCK-RESOLVE-1", "Engineering Ethics")
    student = await _seed_student(client, school["school_id"], "Now Passing")
    await _raise(client, school["school_id"], student, "STUCK-RESOLVE-1", 3)

    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        n = await resolve_cleared_stuck_alerts(conn, school["school_id"], still_stuck=[])

    assert n == 1
    assert await _open_stuck(client, school["school_id"]) == []


@pytest.mark.asyncio
async def test_a_student_still_stuck_keeps_their_alert(client, db_conn):
    """The over-withdrawal case. Resolving everything is not "working"."""
    school = await _register_school(client, "_partial")
    await _seed_unit(client, "STUCK-PARTIAL-1", "Cloud Computing")
    still = await _seed_student(client, school["school_id"], "Still Stuck")
    freed = await _seed_student(client, school["school_id"], "Freed")
    await _raise(client, school["school_id"], still, "STUCK-PARTIAL-1", 3)
    await _raise(client, school["school_id"], freed, "STUCK-PARTIAL-1", 3)

    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        n = await resolve_cleared_stuck_alerts(
            conn, school["school_id"], still_stuck=[(still, "STUCK-PARTIAL-1")]
        )

    assert n == 1
    rows = await _open_stuck(client, school["school_id"])
    assert [r["details"]["student_id"] for r in rows] == [still]


# ── The endpoint ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_alert_reaches_the_inbox_named(client, db_conn):
    """The name is resolved at READ time, never stored in `details`."""
    school = await _register_school(client, "_inbox")
    await _seed_unit(client, "STUCK-INBOX-1", "Software Development Lifecycle")
    student = await _seed_student(client, school["school_id"], "Priya Raman")
    await _raise(client, school["school_id"], student, "STUCK-INBOX-1", 3)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    assert r.status_code == 200, r.text
    alert = next(a for a in r.json()["alerts"] if a["alert_type"] == "student_stuck_on_unit")

    assert alert["student_name"] == "Priya Raman"
    assert alert["unit_title"] == "Software Development Lifecycle"
    assert alert["grade"] == _GRADE
    assert alert["details"]["failed_attempts"] == 3
    # The name must not be persisted: a copy in an operational row goes stale and
    # outlives the account it describes.
    assert "student_name" not in alert["details"]


@pytest.mark.asyncio
async def test_a_malformed_student_id_costs_only_its_own_name(client, db_conn):
    """One bad row must not take the whole inbox down with it.

    `details` is free-form JSONB and `(details->>'student_id')::uuid` is a
    statement-level cast: a value that is not a UUID does not yield NULL for that
    row, it aborts the query. Without the shape check in `get_alerts`, a single
    malformed row 500s every alert for that school — including the pass-rate ones
    that have nothing to do with it.
    """
    school = await _register_school(client, "_malformed")
    await _seed_unit(client, "STUCK-BAD-1", "Cloud Computing")
    await _seed_unit(client, "STUCK-BAD-2", "Web Development")

    async with _pool(client).acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO report_alerts (school_id, alert_type, details)
            VALUES ($1, 'student_stuck_on_unit',
                    jsonb_build_object('unit_id', 'STUCK-BAD-1',
                                       'student_id', 'not-a-uuid',
                                       'failed_attempts', 3))
            """,
            uuid.UUID(school["school_id"]),
        )
        await raise_pass_rate_alert(conn, school["school_id"], "STUCK-BAD-2", 0.0)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    assert r.status_code == 200, r.text
    alerts = {a["alert_type"]: a for a in r.json()["alerts"]}

    # The unrelated alert is unaffected -- that is the point.
    assert "pass_rate_breach" in alerts
    # The bad row still renders, just without a name it could not resolve.
    assert alerts["student_stuck_on_unit"]["student_name"] is None
    assert alerts["student_stuck_on_unit"]["unit_title"] == "Cloud Computing"


@pytest.mark.asyncio
async def test_a_teacher_outside_the_grade_cannot_see_it(client, db_conn):
    """This alert names a STUDENT, so #576 scoping is not cosmetic here."""
    school = await _register_school(client, "_scope")
    await _seed_unit(client, "STUCK-SCOPE-1", "Web Development")
    student = await _seed_student(client, school["school_id"], "Scoped Away")
    await _raise(client, school["school_id"], student, "STUCK-SCOPE-1", 3)

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
            f"auth0|other-{teacher_id.replace('-', '')}",
            f"other-{teacher_id[:8]}@school.example.com",
        )
        await conn.execute(
            """
            INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
            VALUES ($1, $2, $3)
            """,
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
    assert "student_stuck_on_unit" not in types


# ── Settings ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_threshold_round_trips(client, db_conn):
    """#526: the write existed but nothing read it back, so saves looked lost."""
    school = await _register_school(client, "_settings")
    hdr = _hdr(school["teacher_id"], school["school_id"])
    url = f"/api/v1/reports/school/{school['school_id']}/alerts/settings"

    r = await client.get(url, headers=hdr)
    assert r.status_code == 200, r.text
    assert r.json()["stuck_attempts_threshold"] == 3, "server default"

    body = r.json()
    body["stuck_attempts_threshold"] = 5
    body.pop("school_id", None)
    body.pop("updated_at", None)
    r = await client.put(url, json=body, headers=hdr)
    assert r.status_code == 200, r.text
    assert r.json()["stuck_attempts_threshold"] == 5

    r = await client.get(url, headers=hdr)
    assert r.json()["stuck_attempts_threshold"] == 5


@pytest.mark.asyncio
async def test_a_threshold_of_one_is_refused(client, db_conn):
    """One failed attempt is a bad day, not a pattern. `ge=2` is the guard."""
    school = await _register_school(client, "_ge2")
    hdr = _hdr(school["teacher_id"], school["school_id"])
    url = f"/api/v1/reports/school/{school['school_id']}/alerts/settings"

    r = await client.get(url, headers=hdr)
    body = r.json()
    body["stuck_attempts_threshold"] = 1
    body.pop("school_id", None)
    body.pop("updated_at", None)

    r = await client.put(url, json=body, headers=hdr)
    assert r.status_code == 422, r.text
