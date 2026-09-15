"""
tests/test_multi_school_enrolment_572.py

A student may be enrolled at more than one school (issue #572).

Reported by Venki 2026-08-10: adding `chnsuri@gmail.com` to ABC School failed
with "A student with that email already exists" because she was an active
student of another school. #616 made that message explain itself; this makes the
case actually work.

Product decision taken 2026-08-24, with the motivating example: a student
attends a school for their regular curriculum AND an external tutor who runs
additional classes on the same platform. Both are real, simultaneous
relationships. The rule stated alongside it: **the same student cannot appear
twice within one school.**

## The shape chosen, and why it is not the one first costed

The obvious reading — "scope `students.email` per school" — would create a
SECOND `students` row per person. That makes login ambiguous (which account does
this address sign into?), which is #578, and splits a student's record in two.

The schema already offers a better answer:

    school_enrolments  UNIQUE (school_id, student_email)   one ID per school
                       PK (enrolment_id), no unique on student_id

`school_enrolments` is ALREADY many-to-many. So: keep exactly ONE identity per
person (`students.email` stays globally unique — no login ambiguity, #578 is not
a blocker) and let that identity hold several enrolments. Provisioning an
address that already exists ATTACHES the person to the new school instead of
failing.

## What attaching must not do

It must not touch their credentials. The student has a password with their first
school; a second school adding them cannot reset it, cannot see it, and cannot
be handed one to email out. Tested explicitly below — this is the difference
between "enrol an existing person" and "create an account".

## FERPA boundary

Multi-school membership creates a disclosure risk that did not exist when a
student could only belong to one school: school B enrols a student and can then
read the work they did for school A.

Rule applied: a school sees a student's work on curricula it OWNS, plus work on
platform-default curricula, which both schools legitimately teach. Work on
another school's OWN curriculum is not visible. The tutor's bespoke classes stay
with the tutor; the school's forked content stays with the school.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


def _fresh_email(tag: str) -> str:
    """A unique address per test.

    Rows written through the app pool are COMMITTED and persist for the whole
    test session, so a shared constant accumulated enrolments across tests and
    turned every count assertion into nonsense.
    """
    return f"dual-{tag}-{uuid.uuid4().hex[:8]}@example.com"


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Multi School{suffix}",
            "contact_email": f"multi{suffix}@school.example.com",
            "country": "ZA",
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


async def _provision(
    client: AsyncClient,
    school: dict,
    email: str,
    grade: int = 8,
    name: str = "Dual Student",
    mailer: AsyncMock | None = None,
):
    """Add a student through the school-admin endpoint the UI uses.

    The welcome mail is patched at `src.email.service` because the router
    imports it inside the handler, so patching the router's namespace finds
    nothing. Pass `mailer` to assert on whether credentials were sent.
    """
    target = mailer if mailer is not None else AsyncMock(return_value=None)
    with patch("src.email.service.send_welcome_student_email", target):
        return await client.post(
            f"/api/v1/schools/{school['school_id']}/students",
            json={"name": name, "email": email, "grade": grade},
            headers=_headers(school),
        )


async def _enrolment_rows(client: AsyncClient, email: str) -> list:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetch(
            "SELECT school_id::text, student_id::text, status, grade"
            " FROM school_enrolments WHERE lower(student_email) = lower($1)",
            email,
        )


async def _student_rows(client: AsyncClient, email: str) -> list:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetch(
            "SELECT student_id::text, password_hash, school_id::text"
            " FROM students WHERE lower(email) = lower($1)",
            email,
        )


# ── The reported case ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_student_can_be_added_to_a_second_school(client, db_conn):
    """Venki's block: the address is registered elsewhere, so adding it failed."""
    email = _fresh_email("a_student_can_b")
    school_a = await _register_school(client, "_a1")
    school_b = await _register_school(client, "_b1")

    first = await _provision(client, school_a, email)
    assert first.status_code == 201, first.text

    second = await _provision(client, school_b, email)
    assert second.status_code == 201, second.text


@pytest.mark.asyncio
async def test_it_is_one_person_not_two_accounts(client, db_conn):
    """One identity, two enrolments — not two students who share an address."""
    email = _fresh_email("it_is_one_perso")
    school_a = await _register_school(client, "_a2")
    school_b = await _register_school(client, "_b2")
    await _provision(client, school_a, email)
    await _provision(client, school_b, email)

    students = await _student_rows(client, email)
    assert len(students) == 1, "a second students row was created"

    enrolments = await _enrolment_rows(client, email)
    assert len(enrolments) == 2, enrolments
    assert {e["school_id"] for e in enrolments} == {
        school_a["school_id"],
        school_b["school_id"],
    }
    # Both enrolments point at the same person.
    assert {e["student_id"] for e in enrolments} == {students[0]["student_id"]}


@pytest.mark.asyncio
async def test_the_same_student_cannot_be_added_twice_to_one_school(client, db_conn):
    """The stated rule: one ID per school.

    Already enforced by UNIQUE (school_id, student_email) — this pins that
    attaching did not accidentally open a second door around it.
    """
    email = _fresh_email("the_same_studen")
    school = await _register_school(client, "_dup")
    first = await _provision(client, school, email)
    assert first.status_code == 201, first.text

    again = await _provision(client, school, email)
    assert again.status_code == 409, again.text
    detail = str(again.json()["detail"])
    # It is on THIS roster, so the message may say so — that is not a leak.
    assert "roster" in detail.lower() or "already" in detail.lower(), detail

    assert len(await _enrolment_rows(client, email)) == 1


# ── Attaching is not account creation ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_second_school_cannot_reset_the_students_password(client, db_conn):
    """The credential belongs to the person, not to whoever adds them.

    If attaching re-provisioned the account, the second school would silently
    invalidate the student's existing login and be handed a password for a
    person they do not own.
    """
    email = _fresh_email("the_second_scho")
    school_a = await _register_school(client, "_pw_a")
    school_b = await _register_school(client, "_pw_b")

    await _provision(client, school_a, email)
    before = (await _student_rows(client, email))[0]["password_hash"]

    second = await _provision(client, school_b, email)
    assert second.status_code == 201, second.text

    after = (await _student_rows(client, email))[0]["password_hash"]
    assert after == before, "the second school reset an existing student's password"


@pytest.mark.asyncio
async def test_no_welcome_credentials_are_sent_when_attaching(client, db_conn):
    """Attaching must not email a "here is your password" to an existing user.

    There is no new password — the person already has one — so sending anything
    credential-shaped would either be a lie or a reset. The first provisioning
    DOES send one, which is what makes this assertion meaningful rather than a
    mailer that never fires.
    """
    email = _fresh_email("no_welcome_cred")
    school_a = await _register_school(client, "_nopw_a")
    school_b = await _register_school(client, "_nopw_b")

    first_mailer = AsyncMock(return_value=None)
    await _provision(client, school_a, email, mailer=first_mailer)
    assert first_mailer.await_count == 1, "a new account should get its credentials"

    second_mailer = AsyncMock(return_value=None)
    second = await _provision(client, school_b, email, mailer=second_mailer)
    assert second.status_code == 201, second.text
    assert second_mailer.await_count == 0, "credentials were emailed on attach"


# ── Visibility ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_student_appears_on_both_rosters(client, db_conn):
    """Both schools must see their own enrolment of this person."""
    email = _fresh_email("the_student_app")
    school_a = await _register_school(client, "_ros_a")
    school_b = await _register_school(client, "_ros_b")
    await _provision(client, school_a, email)
    await _provision(client, school_b, email)

    for school in (school_a, school_b):
        r = await client.get(
            f"/api/v1/schools/{school['school_id']}/enrolment", headers=_headers(school)
        )
        assert r.status_code == 200, r.text
        emails = [row["student_email"] for row in r.json()["roster"]]
        assert email in emails, (school["school_id"], emails)


@pytest.mark.asyncio
async def test_the_reports_roster_shows_a_student_enrolled_at_this_school(client, db_conn):
    """The reports roster keyed off students.school_id, which names ONE school.

    A student attached to a second school would be invisible in that school's
    reports — provisioned successfully, then absent from the screen the teacher
    actually uses.
    """
    email = _fresh_email("the_reports_ros")
    school_a = await _register_school(client, "_rep_a")
    school_b = await _register_school(client, "_rep_b")
    await _provision(client, school_a, email)
    await _provision(client, school_b, email)

    r = await client.get(
        f"/api/v1/reports/school/{school_b['school_id']}/roster", headers=_headers(school_b)
    )
    assert r.status_code == 200, r.text
    names = [s["student_name"] for s in r.json()["students"]]
    assert names, "school B's reports roster is empty"


@pytest.mark.asyncio
async def test_attaching_does_not_disclose_work_done_before_enrolment(client, db_conn):
    """The disclosure this feature would otherwise create.

    Multi-school membership means a school admin who knows an address can add
    that person and then read what they did elsewhere. Enrolling someone grants
    visibility of their work at THIS school from the point they joined — not a
    retrospective view of another school's records.

    Every current flow (provisioning, roster upload, enrol-by-code) writes the
    enrolment before any work happens, so this hides nothing a school owns.
    """
    email = _fresh_email("no_retro")
    school_a = await _register_school(client, "_retro_a")
    school_b = await _register_school(client, "_retro_b")

    created = await _provision(client, school_a, email)
    assert created.status_code == 201, created.text
    student_id = created.json()["student_id"]

    # Work done while enrolled only at school A.
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, 'G8-MATH-001', 'default-2026-g8', 8, 'Mathematics',
                    NOW(), NOW(), 7, 8, TRUE, 1, TRUE)
            """,
            uuid.UUID(student_id),
        )

    attached = await _provision(client, school_b, email)
    assert attached.status_code == 201, attached.text

    r = await client.get(
        f"/api/v1/reports/school/{school_b['school_id']}/roster", headers=_headers(school_b)
    )
    assert r.status_code == 200, r.text
    rows = [s for s in r.json()["students"] if s["student_id"] == student_id]
    assert rows, "the attached student should appear on school B's roster"
    assert rows[0]["units_completed"] == 0, (
        f"school B can see work done before the student joined: {rows[0]}"
    )


@pytest.mark.asyncio
async def test_the_first_school_still_sees_its_own_students_work(client, db_conn):
    """The guard must not blank the school that legitimately owns the record."""
    email = _fresh_email("owner_sees")
    school_a = await _register_school(client, "_own_a")

    created = await _provision(client, school_a, email)
    student_id = created.json()["student_id"]

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, 'G8-MATH-001', 'default-2026-g8', 8, 'Mathematics',
                    NOW(), NOW(), 7, 8, TRUE, 1, TRUE)
            """,
            uuid.UUID(student_id),
        )

    r = await client.get(
        f"/api/v1/reports/school/{school_a['school_id']}/roster", headers=_headers(school_a)
    )
    assert r.status_code == 200, r.text
    rows = [s for s in r.json()["students"] if s["student_id"] == student_id]
    assert rows and rows[0]["units_completed"] == 1, rows
