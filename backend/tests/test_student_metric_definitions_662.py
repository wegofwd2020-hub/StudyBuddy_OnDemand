"""
tests/test_student_metric_definitions_662.py

One definition per student metric (issues #662, #668, #669).

Venki 2026-08-27 reported three symptoms that turned out to be one habit: a
metric named for a THING, computed over EVENTS — and, for the average, three
different formulas across two screens.

    "Quizzes completed count not getting refreshed in My Stats Page."
    "If I see the same lesson more than 1 time it is count as new lesson."
    "Average score in Dash board shows 61.8% whereas in My Stats page it
     shows 62%."

## What each was

**#662 — quizzes completed.** `/analytics/student/stats` summed every row in
`progress_sessions` with no `completed` filter. On the reporting student's
account that is 85 rows against 24 completed sessions; the tile read 82. Not
merely the wrong period (#649) — the wrong rows.

**#668 — lessons viewed.** `COUNT(*)` over `lesson_views`, so re-opening one
lesson incremented it. The same shape as #655, where "units done" counted
passed sessions rather than distinct units. Settled as DISTINCT lessons: the
tile sits beside "Units done" and "Quizzes completed", both thing-counts, and
re-reading a lesson is not more curriculum covered.

**#669 — average score.** Three formulas:

    dashboard summary   unweighted mean of per-SESSION percentages
    My Stats            mean of per-DAY averages
    dashboard subjects  questions right / questions answered

All three are now the weighted form. The per-day mean was the worst: a day with
one quiz weighed the same as a day with ten.

The visible 61.8-vs-62 gap also had a second, duller cause — one screen rounded
to a whole percent and the other to one decimal — so the numbers are now
rounded the same way and each tile states its window, since the dashboard is
all-time and My Stats is period-scoped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token

_GRADE = 8


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _student(client: AsyncClient) -> str:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status)
            VALUES ($1, $2, 'Metric Student', $3, $4, 'en', 'active')
            """,
            uuid.UUID(student_id),
            f"auth0|metric-{student_id.replace('-', '')}",
            f"metric-{student_id[:8]}@example.com",
            _GRADE,
        )
    return student_id


async def _session(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    *,
    completed: bool,
    score: int | None = None,
    total: int | None = None,
    passed: bool = False,
    attempt: int = 1,
    days_ago: int = 0,
):
    pool = client._transport.app.state.pool
    when = datetime.now(UTC) - timedelta(days=days_ago)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, 'metric-cur', $3, 'Metric', $9, $9, $4, $5, $6, $7, $8)
            """,
            uuid.UUID(student_id),
            unit_id,
            _GRADE,
            score,
            total,
            completed,
            attempt,
            passed,
            when,
        )


async def _view(client: AsyncClient, student_id: str, unit_id: str, *, days_ago: int = 0):
    pool = client._transport.app.state.pool
    when = datetime.now(UTC) - timedelta(days=days_ago)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, started_at, ended_at, duration_s, audio_played)
            VALUES ($1, $2, 'metric-cur', $3, $3, 60, FALSE)
            """,
            uuid.UUID(student_id),
            unit_id,
            when,
        )


async def _stats(client: AsyncClient, student_id: str, period: str = "30d") -> dict:
    token = make_student_token(student_id=student_id, grade=_GRADE)
    r = await client.get(
        f"/api/v1/analytics/student/stats?period={period}", headers=_auth(token)
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── #662: quizzes completed ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quizzes_completed_excludes_unfinished_sessions(client, db_conn):
    """The reported case, at the ratio he actually saw.

    Three finished, five abandoned. The tile must read 3, not 8.
    """
    student = await _student(client)
    for i in range(3):
        await _session(
            client, student, f"MET-{i}", completed=True, score=5, total=8, passed=False
        )
    for i in range(5):
        await _session(client, student, f"MET-AB-{i}", completed=False)

    body = await _stats(client, student)
    assert body["quizzes_completed"] == 3, body


@pytest.mark.asyncio
async def test_an_abandoned_only_day_is_not_plotted_as_activity(client, db_conn):
    """`session_dates` drives the streak chart, so it follows the same rule."""
    student = await _student(client)
    await _session(client, student, "MET-X", completed=False)

    body = await _stats(client, student)
    assert body["session_dates"] == [], body


# ── #668: lessons viewed ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reopening_a_lesson_does_not_count_as_another_lesson(client, db_conn):
    student = await _student(client)
    await _view(client, student, "MET-L1")
    await _view(client, student, "MET-L1")
    await _view(client, student, "MET-L2")

    body = await _stats(client, student)
    assert body["lessons_viewed"] == 2, body


# ── #669: one average, weighted ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_average_is_weighted_by_questions_answered(client, db_conn):
    """A 1-question quiz must not weigh the same as a 20-question one.

    1/1 (100%) and 5/20 (25%):
        mean of per-session percentages -> 62.5   (the old dashboard formula)
        questions right / asked         -> 6/21 = 28.6
    """
    student = await _student(client)
    await _session(client, student, "MET-W1", completed=True, score=1, total=1, passed=True)
    await _session(
        client, student, "MET-W2", completed=True, score=5, total=20, passed=False
    )

    body = await _stats(client, student)
    # The endpoint returns a fraction.
    assert body["avg_score"] == pytest.approx(0.286, abs=0.002), body


@pytest.mark.asyncio
async def test_the_dashboard_and_stats_report_the_same_average(client, db_conn):
    """The reported symptom: two screens, one number, two answers.

    Guards the reconciliation itself rather than either formula — if a future
    change moves one surface, this fails even if that surface is internally
    consistent.
    """
    # Chosen so the three old formulas all disagree — otherwise the test
    # passes even against the bug, which an earlier draft of it did:
    #
    #   day 1:  1/1                       (100%)
    #   day 2:  5/20 and 5/20             (25% each)
    #
    #   mean of per-DAY averages   (100 + 25) / 2       = 62.5   <- old My Stats
    #   mean of per-SESSION pcts   (100 + 25 + 25) / 3  = 50.0   <- old dashboard
    #   questions right / asked    11 / 41              = 26.8   <- both, now
    student = await _student(client)
    await _session(
        client, student, "MET-A1", completed=True, score=1, total=1, passed=True, days_ago=1
    )
    await _session(
        client, student, "MET-A2", completed=True, score=5, total=20, passed=False
    )
    await _session(
        client, student, "MET-A3", completed=True, score=5, total=20, passed=False
    )

    stats = await _stats(client, student, period="all")

    token = make_student_token(student_id=student, grade=_GRADE)
    r = await client.get("/api/v1/student/dashboard", headers=_auth(token))
    assert r.status_code == 200, r.text
    dashboard = r.json()

    # stats returns a fraction, the dashboard a percentage.
    assert stats["avg_score"] * 100 == pytest.approx(
        dashboard["summary"]["avg_quiz_score"], abs=0.15
    ), (stats["avg_score"], dashboard["summary"]["avg_quiz_score"])
    # And that the agreed value is the weighted one, not a shared wrong answer.
    assert stats["avg_score"] == pytest.approx(11 / 41, abs=0.002), stats["avg_score"]


@pytest.mark.asyncio
async def test_an_unfinished_session_does_not_drag_the_average(client, db_conn):
    """An abandoned attempt has no score and must not count as zero."""
    student = await _student(client)
    await _session(client, student, "MET-S1", completed=True, score=8, total=10, passed=True)
    await _session(client, student, "MET-S2", completed=False)

    body = await _stats(client, student)
    assert body["avg_score"] == pytest.approx(0.8, abs=0.001), body
