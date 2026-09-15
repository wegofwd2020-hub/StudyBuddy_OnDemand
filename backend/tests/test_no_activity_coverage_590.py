"""
tests/test_no_activity_coverage_590.py

"No activity" must mean units nobody has touched (issue #590).

Reported by Venki 2026-08-17 as "Units with Activity shows no data". Two
differently-wrong metrics share the name, and neither is grounded in the
curriculum:

**Overview.** `units_no_activity` was

    (units with a lesson_view BEFORE the period start)
      MINUS
    (units with a progress_session DURING the period)

That is "went quiet this period", not "untouched" — and a unit never viewed
before the window can never appear however untouched it is. With `period=term`
resolving to a date before any lesson_views exist, the set is structurally
guaranteed to be empty regardless of real coverage.

**Curriculum health.** Its rows come `FROM progress_sessions ... GROUP BY
unit_id`, so a unit with **zero sessions never enters the result at all** — it is
silently missing from `total_units` and from every tier count, rather than being
reported as untouched. The `no_activity` tier actually meant "has sessions but no
lesson view".

So the report designed to surface coverage gaps was blind to exactly the units
that represent them: the ones nobody has opened.

Both are now grounded in the cohort's real curriculum catalog, resolved the same
way content is served and with the fork -> source rule from #650.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_YEAR = 2026


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Coverage School{suffix}",
            "contact_email": f"coverage{suffix}@school.example.com",
            "country": "IN",
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


async def _seed_curriculum(client: AsyncClient, curriculum_id: str, grade: int, units: list[str]):
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, $2, $3, $4, 'platform', TRUE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id,
            f"Seeded {curriculum_id}",
            grade,
            _YEAR,
        )
        for i, unit_id in enumerate(units, start=1):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, 'Coverage', $3, $3, $4)
                ON CONFLICT DO NOTHING
                """,
                unit_id,
                curriculum_id,
                f"Unit {i}",
                i,
            )


async def _enrol(client: AsyncClient, school_id: str, grade: int) -> str:
    student_id = str(uuid.uuid4())
    email = f"cov-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Coverage Student', $3, $4, 'en', 'active', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|cov-{student_id.replace('-', '')}",
            email,
            grade,
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
            grade,
        )
    return student_id


async def _touch(client: AsyncClient, student_id: str, unit_id: str, curriculum_id: str, grade: int):
    """One completed quiz session plus a lesson view on this unit."""
    pool = client._transport.app.state.pool
    when = datetime.now(UTC) - timedelta(hours=1)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, $4, 'Coverage', $5, $5, 7, 8, TRUE, 1, TRUE)
            """,
            uuid.UUID(student_id),
            unit_id,
            curriculum_id,
            grade,
            when,
        )
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, started_at, ended_at, duration_s, audio_played)
            VALUES ($1, $2, $3, $4, $4, 120, FALSE)
            """,
            uuid.UUID(student_id),
            unit_id,
            curriculum_id,
            when,
        )


# ── Overview ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_an_untouched_unit_is_reported_as_no_activity(client, db_conn):
    """The reported symptom: the card was structurally always empty."""
    cid = f"default-{_YEAR}-g6"
    await _seed_curriculum(client, cid, 6, ["COV-A", "COV-B", "COV-C"])
    school = await _register_school(client, "_ov")
    student = await _enrol(client, school["school_id"], 6)
    await _touch(client, student, "COV-A", cid, 6)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/overview?period=30d",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text
    no_activity = set(r.json()["units_no_activity"])
    assert {"COV-B", "COV-C"} <= no_activity, r.json()


@pytest.mark.asyncio
async def test_a_touched_unit_is_not_reported_as_no_activity(client, db_conn):
    """Guard against the opposite error — listing everything."""
    cid = f"default-{_YEAR}-g6"
    await _seed_curriculum(client, cid, 6, ["COV-A", "COV-B", "COV-C"])
    school = await _register_school(client, "_ov2")
    student = await _enrol(client, school["school_id"], 6)
    await _touch(client, student, "COV-A", cid, 6)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/overview?period=30d",
        headers=_headers(school),
    )
    assert "COV-A" not in r.json()["units_no_activity"], r.json()


# ── Curriculum health ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_curriculum_health_includes_units_with_no_sessions(client, db_conn):
    """Units with zero sessions were silently absent from the whole report.

    They are the coverage gaps the report exists to surface, so excluding them
    made it blind in exactly the case that matters.
    """
    cid = f"default-{_YEAR}-g6"
    await _seed_curriculum(client, cid, 6, ["COV-A", "COV-B", "COV-C"])
    school = await _register_school(client, "_ch")
    student = await _enrol(client, school["school_id"], 6)
    await _touch(client, student, "COV-A", cid, 6)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    listed = {u["unit_id"] for u in body["units"]}
    assert {"COV-A", "COV-B", "COV-C"} <= listed, body


@pytest.mark.asyncio
async def test_total_units_is_the_catalog_not_the_units_with_sessions(client, db_conn):
    """`total_units` counted only units that happened to have a session."""
    cid = f"default-{_YEAR}-g6"
    await _seed_curriculum(client, cid, 6, ["COV-A", "COV-B", "COV-C"])
    school = await _register_school(client, "_tot")
    student = await _enrol(client, school["school_id"], 6)
    await _touch(client, student, "COV-A", cid, 6)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.json()["total_units"] == 3, r.json()


@pytest.mark.asyncio
async def test_untouched_units_are_tiered_no_activity(client, db_conn):
    """And they must be counted in the tier, not merely present."""
    cid = f"default-{_YEAR}-g6"
    await _seed_curriculum(client, cid, 6, ["COV-A", "COV-B", "COV-C"])
    school = await _register_school(client, "_tier")
    student = await _enrol(client, school["school_id"], 6)
    await _touch(client, student, "COV-A", cid, 6)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    body = r.json()
    tiers = {u["unit_id"]: u["health_tier"] for u in body["units"]}
    assert tiers.get("COV-B") == "no_activity", body
    assert tiers.get("COV-C") == "no_activity", body
    assert body["no_activity_count"] >= 2, body
