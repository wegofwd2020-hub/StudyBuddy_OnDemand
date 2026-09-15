"""
tests/test_curriculum_health_join_fanout.py

`get_curriculum_health` must not weight a unit's statistics by how many times
students opened the lesson (issue #625).

The query joins `lesson_views` directly:

    FROM progress_sessions ps
    LEFT JOIN lesson_views lv ON lv.student_id = ps.student_id
                             AND lv.unit_id = ps.unit_id

so a student with N lesson views on a unit contributes N copies of every quiz
session row for that unit. Row-counting aggregates then multiply:

  - `COUNT(*)` in the pass-rate numerator produced the 200% / 300% / 800% rates
    reported in #623. That side was fixed by counting distinct students, which
    is immune to fan-out — but the fix landed with the wrong cause recorded
    (repeat sessions, #579), so the rest of the query was never examined.
  - `AVG(score)` and `AVG(attempt_number)` sit in the SAME query and are NOT
    immune. They still weight each student by their lesson-view count.

This is the same defect #464 already fixed in `analytics/service.py`, where
lesson views are aggregated in a subquery *before* the join. The precedent is
the fix: aggregate the child table first, then join one row per unit.

Averages only skew when the weights DIFFER between students, so both tests use
two students with different view counts. A single student re-viewing a lesson
duplicates identical rows and leaves the mean unchanged — which is why this
went unnoticed.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_UNIT = "G8-MATH-001"


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Fanout School{suffix}",
            "contact_email": f"fanout{suffix}@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _headers(reg: dict) -> dict:
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
    )
    return {"Authorization": f"Bearer {token}"}


async def _student_with_views(
    client: AsyncClient,
    school_id: str,
    *,
    score: int,
    attempt: int,
    passed: bool,
    lesson_views: int,
) -> str:
    """One student: one completed quiz session on _UNIT, plus N lesson views.

    The lesson views are what fan the session row out.
    """
    student_id = str(uuid.uuid4())
    email = f"fanout-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Fanout Student', $3, 8, 'en', 'active', $4)
            """,
            uuid.UUID(student_id),
            f"auth0|fo-{student_id.replace('-', '')}",
            email,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', 8)
            """,
            uuid.UUID(school_id),
            email,
            uuid.UUID(student_id),
        )
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 started_at, ended_at, score, total_questions, completed,
                 attempt_number, passed)
            VALUES ($1, $2, 'default-2026-g8', 8, 'Mathematics',
                    NOW(), NOW(), $3, 10, TRUE, $4, $5)
            """,
            uuid.UUID(student_id),
            _UNIT,
            score,
            attempt,
            passed,
        )
        for _ in range(lesson_views):
            await conn.execute(
                """
                INSERT INTO lesson_views
                    (student_id, unit_id, curriculum_id, started_at, ended_at,
                     duration_s, audio_played)
                VALUES ($1, $2, 'default-2026-g8', NOW(), NOW(), 60, FALSE)
                """,
                uuid.UUID(student_id),
                _UNIT,
            )
    return student_id


@pytest.mark.asyncio
async def test_avg_score_is_not_weighted_by_lesson_views(client, db_conn):
    """Two students, different view counts. The mean must not follow the views.

    Student A scores 10 and viewed the lesson 3 times; student B scores 4 and
    viewed it once. The honest mean is (10 + 4) / 2 = 7.0. Fanned out it is
    (10*3 + 4*1) / 4 = 8.5 — the weaker student is nearly erased because they
    opened the lesson fewer times.
    """
    school = await _register_school(client, "_avg")
    await _student_with_views(
        client, school["school_id"], score=10, attempt=1, passed=True, lesson_views=3
    )
    await _student_with_views(
        client, school["school_id"], score=4, attempt=1, passed=True, lesson_views=1
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["avg_score_pct"] == 7.0, (
        f"avg_score_pct {unit['avg_score_pct']} is weighted by lesson views (8.5 = fanned out)"
    )


@pytest.mark.asyncio
async def test_avg_attempts_is_not_weighted_by_lesson_views(client, db_conn):
    """The same fan-out skews average attempts, which drives the health tier.

    Student A passed on attempt 1 and viewed the lesson 4 times; student B
    needed 3 attempts and viewed it once. True mean attempts = 2.0. Fanned out
    it is (1*4 + 3*1) / 5 = 1.4 — the unit looks easier than it is, because the
    struggling student read the lesson less.
    """
    school = await _register_school(client, "_att")
    await _student_with_views(
        client, school["school_id"], score=9, attempt=1, passed=True, lesson_views=4
    )
    await _student_with_views(
        client, school["school_id"], score=6, attempt=3, passed=True, lesson_views=1
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["avg_attempts_to_pass"] == 2.0, (
        f"avg_attempts_to_pass {unit['avg_attempts_to_pass']} is weighted by lesson views (1.4 = fanned out)"
    )


@pytest.mark.asyncio
async def test_pass_rate_still_bounded_with_many_views(client, db_conn):
    """The #623 symptom, reproduced through its ACTUAL cause.

    One student, one passing session, eight lesson views: the old numerator
    counted eight joined rows against one distinct student and reported 800% —
    the exact figure the live demo produced. Kept as a regression guard now
    that the real mechanism is understood.
    """
    school = await _register_school(client, "_rate")
    await _student_with_views(
        client, school["school_id"], score=10, attempt=1, passed=True, lesson_views=8
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["first_attempt_pass_rate_pct"] == 100.0, unit


@pytest.mark.asyncio
async def test_lesson_view_detection_survives_the_rewrite(client, db_conn):
    """The join exists to answer "has anyone viewed this lesson?" — keep that.

    `has_lesson_view` is not returned to the client; it feeds `_health_tier`,
    which reports `no_activity` when nobody has opened the lesson. So the tier
    is the observable proof the signal survived replacing the join.

    Without this, a rewrite that drops lesson views entirely would still pass
    the three tests above — they only check that numbers got smaller.
    """
    school = await _register_school(client, "_flag")
    await _student_with_views(
        client, school["school_id"], score=3, attempt=2, passed=False, lesson_views=0
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["health_tier"] == "no_activity", unit


@pytest.mark.asyncio
async def test_a_viewed_unit_is_not_reported_as_no_activity(client, db_conn):
    """The other half of the same guard: views present must be detected.

    Paired with the test above, this pins both directions — a rewrite that
    hard-codes either answer fails one of them.
    """
    school = await _register_school(client, "_seen")
    await _student_with_views(
        client, school["school_id"], score=9, attempt=1, passed=True, lesson_views=2
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["health_tier"] != "no_activity", unit
