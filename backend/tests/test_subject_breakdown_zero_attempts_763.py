"""
tests/test_subject_breakdown_zero_attempts_763.py

Subjects with no quiz attempts are still subjects (Venki, 14 Sep — #763):

    "Subject Breakdown only shows subjects that have quiz attempts > 0.
     Business studies not showing because quiz attempts: 0."

The breakdown was built solely from `progress_sessions`, so a subject the
student had not attempted contributed no row and could not appear. The one case
a student most needs to see — "I have not started this yet" — was the one the
chart was structurally incapable of showing.

This is the third instance of the same shape:

  * #590  "units with no activity" measured activity against activity, so a unit
          nobody had opened could never be listed.
  * #755  a student who had never begun was described as one who had stopped,
          because the only figure available counted from enrolment.
  * #763  this.

In each, a list built from ACTIVITY is asked to report the ABSENCE of activity.

The catalog comes from `resolve_curriculum_ids`, the shared resolver (pitfall
#31), so the subjects offered are the ones the student is actually served: a
Commerce student sees Accountancy / Business Studies / Economics, not every
subject taught at their grade. Seeding the breakdown from a wider source would
fix the missing zero by inventing subjects the student does not take.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from jose import jwt as _jwt

from tests.helpers.token_factory import make_student_token

_JWT_SECRET = "test-secret-do-not-use-in-production-aaaa"


def _student_id(seed: str) -> str:
    payload = _jwt.decode(
        make_student_token(student_id=seed, grade=11), _JWT_SECRET, algorithms=["HS256"]
    )
    return payload["student_id"]


def _token_for(student_id: str, school_id: str) -> str:
    """A token carrying `school_id`, which the resolver REQUIRES.

    `resolve_curriculum_ids` gates its classroom-package step on
    `if not ids and school_id:` — without it, resolution skips straight to the
    `default-{year}-g{grade}` fallback. A token minted without a school is
    therefore not a weaker version of a real one; it resolves to a DIFFERENT
    curriculum, and a fixture that omitted it would test the fallback path
    while appearing to test the stream path.
    """
    return make_student_token(student_id=student_id, grade=11, school_id=school_id)


async def _curriculum(client: AsyncClient, grade: int, units: list[tuple[str, str, str]]) -> str:
    """`units` is [(unit_id, subject_code, subject_display_name)]."""
    cid = f"sb-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Breakdown Curriculum', $2, 2026, 'platform', FALSE)
            """,
            cid,
            grade,
        )
        for unit_id, code, name in units:
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, 0)
                """,
                unit_id,
                cid,
                code,
                f"Unit {unit_id}",
            )
            await conn.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, subject_name, version_number, status)
                VALUES ($1, $2, $3, 1, 'published')
                ON CONFLICT DO NOTHING
                """,
                cid,
                code,
                name,
            )
    return cid


async def _student_on(client: AsyncClient, student_id: str, grade: int, cid: str) -> str:
    """A student routed to `cid` through a classroom package — the real path."""
    school_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, status)
            VALUES ($1, 'Breakdown School', $2, 'IN', 'active')
            """,
            uuid.UUID(school_id),
            f"bd-{school_id.replace('-', '')[-12:]}@school.example.com",
        )
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Breakdown Student', $4, 'en', $5)
            ON CONFLICT (student_id) DO UPDATE SET school_id = EXCLUDED.school_id
            """,
            uuid.UUID(student_id),
            f"auth0|bd-{student_id.replace('-', '')}",
            f"bd-{student_id.replace('-', '')}@example.com",
            grade,
            uuid.UUID(school_id),
        )
        classroom_id = await conn.fetchval(
            "INSERT INTO classrooms (school_id, name, grade) VALUES ($1, $2, $3)"
            " RETURNING classroom_id",
            uuid.UUID(school_id),
            "Breakdown Room",
            grade,
        )
        await conn.execute(
            "INSERT INTO classroom_packages (classroom_id, curriculum_id) VALUES ($1, $2)",
            classroom_id,
            cid,
        )
        await conn.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) VALUES ($1, $2)",
            classroom_id,
            uuid.UUID(student_id),
        )
    return school_id


async def _attempt(client: AsyncClient, student_id: str, unit_id: str, cid: str, code: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 11, $4, 1, TRUE, TRUE, 7, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            code,
        )


def _by_subject(body: dict) -> dict[str, dict]:
    return {b["subject"]: b for b in body["subject_breakdown"]}


# ── The reported case ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_subject_with_zero_attempts_still_appears(client, db_conn):
    """Venki's exact case: Accountancy attempted, Business Studies not."""
    student_id = _student_id("b7630000-0000-0000-0000-000000000001")
    cid = await _curriculum(
        client,
        11,
        [
            ("BD-ACC-001", "G11-ACC", "Accountancy"),
            ("BD-BUS-001", "G11-BUS", "Business Studies"),
        ],
    )
    school_id = await _student_on(client, student_id, 11, cid)
    token = _token_for(student_id, school_id)
    await _attempt(client, student_id, "BD-ACC-001", cid, "G11-ACC")

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    by_subject = _by_subject(r.json())

    assert "Business Studies" in by_subject, r.json()
    assert by_subject["Business Studies"]["attempts"] == 0
    assert by_subject["Accountancy"]["attempts"] == 1


@pytest.mark.asyncio
async def test_a_zero_attempt_subject_reports_a_zero_pass_rate(client, db_conn):
    """Not a null and not a 100%. Dividing by zero attempts has no answer, and
    the chart plots this value."""
    student_id = _student_id("b7630000-0000-0000-0000-000000000002")
    cid = await _curriculum(
        client,
        11,
        [("BD-Z-ACC", "G11-ACC", "Accountancy"), ("BD-Z-BUS", "G11-BUS", "Business Studies")],
    )
    school_id = await _student_on(client, student_id, 11, cid)
    token = _token_for(student_id, school_id)
    await _attempt(client, student_id, "BD-Z-ACC", cid, "G11-ACC")

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    bus = _by_subject(r.json())["Business Studies"]

    assert bus["pass_rate"] == 0.0
    assert bus["attempts"] == 0


# ── The narrowing: only subjects the student is actually TAUGHT ───────────────


@pytest.mark.asyncio
async def test_only_the_students_own_subjects_are_listed(client, db_conn):
    """The fix must not swing to the opposite error. Seeding from every subject
    at the grade would show a Commerce student Physics — which is #758's
    complaint, and would be a worse bug than the missing zero."""
    student_id = _student_id("b7630000-0000-0000-0000-000000000003")
    mine = await _curriculum(
        client,
        11,
        [("BD-M-ACC", "G11-ACC", "Accountancy"), ("BD-M-BUS", "G11-BUS", "Business Studies")],
    )
    # A second Grade 11 curriculum this student is NOT routed to.
    await _curriculum(client, 11, [("BD-O-PHY", "G11-PHYS", "Physics")])
    school_id = await _student_on(client, student_id, 11, mine)
    token = _token_for(student_id, school_id)

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    subjects = set(_by_subject(r.json()))

    assert "Accountancy" in subjects
    assert "Business Studies" in subjects
    assert "Physics" not in subjects, "a subject this student does not take"


@pytest.mark.asyncio
async def test_attempted_totals_are_unchanged_by_the_seeding(client, db_conn):
    """Seeding at zero must ADD to the attempted figures, never define them —
    a `setdefault` that ran after the attempts were tallied would silently
    reset every count to zero."""
    student_id = _student_id("b7630000-0000-0000-0000-000000000004")
    cid = await _curriculum(client, 11, [("BD-T-ACC", "G11-ACC", "Accountancy")])
    school_id = await _student_on(client, student_id, 11, cid)
    token = _token_for(student_id, school_id)
    await _attempt(client, student_id, "BD-T-ACC", cid, "G11-ACC")
    await _attempt(client, student_id, "BD-T-ACC", cid, "G11-ACC")

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    acc = _by_subject(r.json())["Accountancy"]

    assert acc["attempts"] == 2
    assert acc["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_subject_names_are_resolved_not_codes(client, db_conn):
    """`curriculum_units.subject` holds a CODE for every stream curriculum
    (pitfall #32). The seeded rows go through the same `display_subject`
    resolution as the attempted ones, or this chart becomes the one place that
    prints "G11-BUS"."""
    student_id = _student_id("b7630000-0000-0000-0000-000000000005")
    cid = await _curriculum(client, 11, [("BD-L-BUS", "G11-BUS", "Business Studies")])
    school_id = await _student_on(client, student_id, 11, cid)
    token = _token_for(student_id, school_id)

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    subjects = set(_by_subject(r.json()))

    assert "Business Studies" in subjects
    assert "G11-BUS" not in subjects
