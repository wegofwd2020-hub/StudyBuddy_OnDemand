"""Venki's 1 Sep round — "Reports → Unit Performance → All Units: Inconsistency
in displaying the Subject Name."

His screenshot showed ONE column speaking two vocabularies:

    Environmental Engineering    G5-ENG      0%
    Fractions and Decimals       G5-MATH     0%
    Electrical Engineering Fund. Engineering 0%
    Energy: Work, Power, Effic.  Science     0%
    Advanced Robotics            G12-ENG     0%

The cause was not one bad value but a missing step. `get_curriculum_health` had
no subject resolution at all, so it printed whatever was stored — and it reads
from two different places that store different things:

  * touched units carry `MAX(progress_sessions.subject)`, a column holding a mix
    of real names and subject codes depending on what was resolvable when the
    session row was written;
  * untouched units carry `curriculum_units.subject`, which is a CODE for every
    stream curriculum (CLAUDE.md pitfall #32).

`get_student_report` has always resolved through `resolve_subject_labels` /
`display_subject`. This one did not, so the same unit could read "Engineering"
on the student's report card and "G5-ENG" on the unit report — which matters
more than either being individually defensible, because a teacher reads them
side by side.

Every fixture below stores a CODE. A fixture that stored a display name would
pass with the resolution step deleted.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import get_curriculum_health, get_student_report


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Subject School{suffix}",
            "contact_email": f"subj{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _curriculum(client: AsyncClient, grade: int, units: list[tuple[str, str]]) -> str:
    """Seed units whose `subject` column holds a CODE, plus a
    content_subject_versions row carrying the human name — the exact shape a
    stream curriculum has on the demo (pitfall #32)."""
    cid = f"subj-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Subject Curriculum', $2, 2026, 'platform', TRUE)
            """,
            cid,
            grade,
        )
        for i, (unit, code) in enumerate(units):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, $5)
                """,
                unit,
                cid,
                code,
                f"Unit {unit}",
                i,
            )
        for code, name in {"G10-ENG": "Engineering", "G10-MATH": "Mathematics"}.items():
            await conn.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, subject_name, version_number, status)
                VALUES ($1, $2, $3, 1, 'published')
                """,
                cid,
                code,
                name,
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
            VALUES ($1, $2, $3, 'Subject Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|subj-{student_id.replace('-', '')}",
            f"subj-{student_id[:8]}@example.com",
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
            f"subj-{student_id[:8]}@example.com",
            grade,
        )
    return student_id


async def _session(client, student_id, unit_id, cid, stored_subject: str) -> None:
    """`stored_subject` is deliberately a CODE — that is what the demo holds."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 10, $4, 1, TRUE, TRUE, 5, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            stored_subject,
        )


def _subject_of(report: dict, unit_id: str) -> str | None:
    for u in report["units"]:
        if u["unit_id"] == unit_id:
            return u["subject"]
    return None


# ── The report resolves what it shows ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_unit_performance_shows_names_not_codes(client, db_conn):
    """A unit whose session stored "G10-ENG" must report "Engineering"."""
    school = await _school(client, "_codes")
    cid = await _curriculum(client, 10, [("SUBJ-ENG-1", "G10-ENG")])
    student_id = await _enrol(client, school["school_id"], 10)
    await _session(client, student_id, "SUBJ-ENG-1", cid, "G10-ENG")

    report = await get_curriculum_health(db_conn, school["school_id"])
    assert _subject_of(report, "SUBJ-ENG-1") == "Engineering"


@pytest.mark.asyncio
async def test_one_column_does_not_mix_codes_and_names(client, db_conn):
    """The literal complaint: two units, one session storing a CODE and one
    storing a NAME, must not print in two different vocabularies."""
    school = await _school(client, "_mixed")
    cid = await _curriculum(
        client, 10, [("SUBJ-MIX-1", "G10-ENG"), ("SUBJ-MIX-2", "G10-MATH")]
    )
    student_id = await _enrol(client, school["school_id"], 10)
    # Exactly the demo's mix: one session wrote the code, the other the name.
    await _session(client, student_id, "SUBJ-MIX-1", cid, "G10-ENG")
    await _session(client, student_id, "SUBJ-MIX-2", cid, "Mathematics")

    report = await get_curriculum_health(db_conn, school["school_id"])
    subjects = [u["subject"] for u in report["units"] if u["unit_id"].startswith("SUBJ-MIX")]

    assert sorted(subjects) == ["Engineering", "Mathematics"]
    for s in subjects:
        assert "-" not in s, f"{s!r} is a code, not a subject name"


@pytest.mark.asyncio
async def test_unit_report_and_student_report_agree(client, db_conn):
    """The reason this matters. A teacher opens both screens for the same unit;
    they must not disagree about what subject it is."""
    school = await _school(client, "_agree")
    cid = await _curriculum(client, 10, [("SUBJ-AGREE-1", "G10-ENG")])
    student_id = await _enrol(client, school["school_id"], 10)
    await _session(client, student_id, "SUBJ-AGREE-1", cid, "G10-ENG")

    health = await get_curriculum_health(db_conn, school["school_id"])
    student = await get_student_report(db_conn, school["school_id"], student_id)

    from_student = next(
        u["subject"] for u in student["per_unit"] if u["unit_id"] == "SUBJ-AGREE-1"
    )
    assert _subject_of(health, "SUBJ-AGREE-1") == from_student == "Engineering"


@pytest.mark.asyncio
async def test_untouched_units_resolve_too(client, db_conn, monkeypatch):
    """Untouched units come from `curriculum_units.subject` — a SEPARATE code
    path that was equally unresolved, and the actual source of the `G5-ENG` /
    `G12-ENG` rows in the report: every one of them had zero activity.

    The catalog is discovered through the curriculum resolver, which is not what
    is under test here. Stubbing `cohort_unit_ids` puts the unit on the untouched
    path directly, so this asserts the thing that was broken — resolution — and
    not the resolver's ability to find a synthetic curriculum.

    Resolution runs after the touched and untouched lists are merged precisely so
    this path cannot drift from the other one again.
    """
    school = await _school(client, "_untouched")
    await _curriculum(client, 10, [("SUBJ-COLD-1", "G10-ENG")])
    await _enrol(client, school["school_id"], 10)

    import src.reports.service as svc

    async def _fake_cohort(conn, pool, redis, school_id, allowed_grades=None):
        return {"SUBJ-COLD-1"}

    monkeypatch.setattr(svc, "cohort_unit_ids", _fake_cohort)

    report = await get_curriculum_health(
        db_conn, school["school_id"], None, object(), object()
    )

    # It must actually be on the untouched path — otherwise this test would pass
    # by silently exercising the touched path it is meant to complement.
    row = next(u for u in report["units"] if u["unit_id"] == "SUBJ-COLD-1")
    assert row["health_tier"] == "no_activity"
    assert row["subject"] == "Engineering"

# ── The export must account for every feedback row the dashboard counts ───────


@pytest.mark.asyncio
async def test_feedback_on_an_untouched_unit_still_gets_a_row(client, db_conn):
    """Venki, 2 Sep: the dashboard tile read 22 and the Unit Performance export
    summed to 17.

    The missing 5 were feedback on units his students had commented on but never
    opened. The report builds from `progress_sessions` plus the cohort catalog,
    so a unit with feedback and no activity had nowhere to appear — while the
    tile counted it.

    Surfacing the unit is the right direction. Narrowing the tile to match would
    have made the numbers agree by hiding feedback nobody would then read.
    """
    school = await _school(client, "_fbgap")
    cid = await _curriculum(client, 10, [("SUBJ-FB-1", "G10-ENG")])
    student_id = await _enrol(client, school["school_id"], 10)

    # Feedback, but deliberately NO session and no lesson view on this unit.
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO feedback (student_id, unit_id, category, message, reviewed)
            VALUES ($1, 'SUBJ-FB-1', 'content', 'This question is unclear.', FALSE)
            """,
            uuid.UUID(student_id),
        )

    report = await get_curriculum_health(db_conn, school["school_id"])
    row = next((u for u in report["units"] if u["unit_id"] == "SUBJ-FB-1"), None)
    assert row is not None, "a unit with feedback must appear even with no activity"
    assert row["feedback_count"] == 1
    assert row["health_tier"] == "no_activity"
    assert cid


@pytest.mark.asyncio
async def test_unit_less_feedback_is_reported_separately(client, db_conn):
    """Feedback naming no unit cannot appear in a per-unit report, so it is
    reported alongside — otherwise the two figures differ with no way to see why,
    which is the whole complaint. Reconciliation beats coincidence."""
    school = await _school(client, "_fbgeneral")
    student_id = await _enrol(client, school["school_id"], 10)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO feedback (student_id, unit_id, category, message, reviewed)
            VALUES ($1, NULL, 'general', 'The app is slow on my tablet.', FALSE)
            """,
            uuid.UUID(student_id),
        )

    report = await get_curriculum_health(db_conn, school["school_id"])
    assert report["general_feedback_count"] == 1
    assert all(u["unit_id"] != "" for u in report["units"])


# ── Attempts-to-pass counts attempts NEEDED, not passes observed ──────────────


async def _view(client, student_id, unit_id, cid):
    """The tier treats `has_lesson_view` as "has activity", so a unit with quiz
    sessions but no view is tiered `no_activity` regardless of its scores. Seed
    one so these fixtures exercise the tier they are actually about."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            "INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)"
            " VALUES ($1, $2, $3, 120)",
            uuid.UUID(student_id), unit_id, cid,
        )


async def _session_at(client, student_id, unit_id, cid, attempt, *, passed, completed=True):
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 10, 'G10-ENG', $4, $5, $6, 8, 8)
            """,
            uuid.UUID(student_id), unit_id, cid, attempt, completed, passed,
        )


@pytest.mark.asyncio
async def test_retaking_a_passed_unit_does_not_inflate_attempts_to_pass(client, db_conn):
    """Venki, 2 Sep: "Web Development is 100% — should it not be Green?"

    It was Orange. The tier rules were right; their INPUT was not. Exactly this
    session history, taken from the demo:

        attempt 1  completed, PASSED
        attempt 2  completed, failed
        attempt 3  completed, PASSED

    The student passed FIRST TIME. `AVG(attempt_number) FILTER (WHERE passed)`
    read AVG(1, 3) = 2.0, which fails the healthy threshold of <= 1.5 and drops
    the unit to "watch" — a unit at 100% first-attempt pass rate coloured as
    needing attention.

    100% first-attempt pass rate and 2.0 attempts-to-pass cannot both be true.
    """
    school = await _school(client, "_attempts")
    cid = await _curriculum(client, 10, [("SUBJ-ATT-1", "G10-ENG")])
    student_id = await _enrol(client, school["school_id"], 10)

    await _view(client, student_id, "SUBJ-ATT-1", cid)
    await _session_at(client, student_id, "SUBJ-ATT-1", cid, 1, passed=True)
    await _session_at(client, student_id, "SUBJ-ATT-1", cid, 2, passed=False)
    await _session_at(client, student_id, "SUBJ-ATT-1", cid, 3, passed=True)

    report = await get_curriculum_health(db_conn, school["school_id"])
    row = next(u for u in report["units"] if u["unit_id"] == "SUBJ-ATT-1")

    assert row["first_attempt_pass_rate_pct"] == 100.0
    assert row["avg_attempts_to_pass"] == 1.0, "they passed on attempt 1; later passes are revision"
    assert row["health_tier"] == "healthy", "100% first-attempt pass must not read as 'watch'"


@pytest.mark.asyncio
async def test_a_unit_that_genuinely_takes_several_attempts_still_shows_it(client, db_conn):
    """The negative direction. Hard-coding attempts to 1, or ignoring the field,
    would satisfy the test above and hide the units this metric exists to find."""
    school = await _school(client, "_attempts_real")
    cid = await _curriculum(client, 10, [("SUBJ-ATT-2", "G10-ENG")])
    student_id = await _enrol(client, school["school_id"], 10)

    # Failed twice, passed on the third — genuinely three attempts to pass.
    await _view(client, student_id, "SUBJ-ATT-2", cid)
    await _session_at(client, student_id, "SUBJ-ATT-2", cid, 1, passed=False)
    await _session_at(client, student_id, "SUBJ-ATT-2", cid, 2, passed=False)
    await _session_at(client, student_id, "SUBJ-ATT-2", cid, 3, passed=True)

    report = await get_curriculum_health(db_conn, school["school_id"])
    row = next(u for u in report["units"] if u["unit_id"] == "SUBJ-ATT-2")

    assert row["first_attempt_pass_rate_pct"] == 0.0
    assert row["avg_attempts_to_pass"] == 3.0
    assert row["health_tier"] == "struggling"
