"""
tests/test_progress_status_lessons_675.py

A unit's status counts the lesson, not only the quiz (issue #675).

Venki 2026-08-28 worked the legend out himself and found one state unreachable:

    "Point No 1, 2 & 4 icons seem to be displaying correctly but that In
     Progress icon is not being shown when I complete the lesson and not taken
     the quiz."

`mv_student_curriculum_progress` was built FROM progress_sessions alone, so
`in_progress` really meant "has an ABANDONED QUIZ ATTEMPT" and `not_started`
covered units whose lesson had been read end to end.

It narrowed further after #579/#646: the lesson page used to create a phantom
session, which accidentally made the icon nearly mean what the label said.
Removing those sessions was right, and it quietly emptied a state that was
already mislabelled — a display reading a proxy nobody had re-checked.

## What these tests pin

  - a lesson view alone puts a unit in `in_progress`;
  - the quiz states still win over it, in the right order;
  - quiz figures (`attempts`, `best_score`) are NOT inflated by lesson views;
  - `not_started` still means genuinely untouched;
  - re-reading a lesson does not fan the row out (the view is keyed unique on
    (student, unit, curriculum), so a fan-out would break the refresh outright).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token

_GRADE = 8
_CURRICULUM = "default-2026-g8"


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
            VALUES ($1, $2, 'Status Student', $3, $4, 'en', 'active')
            """,
            uuid.UUID(student_id),
            f"auth0|status-{student_id.replace('-', '')}",
            f"status-{student_id[:8]}@example.com",
            _GRADE,
        )
    return student_id


async def _unit(client: AsyncClient, unit_id: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Status Curriculum', $2, 2026, 'platform', TRUE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            _CURRICULUM,
            _GRADE,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Status', $1, $1, 1)
            ON CONFLICT DO NOTHING
            """,
            unit_id,
            _CURRICULUM,
        )


async def _view_lesson(client: AsyncClient, student_id: str, unit_id: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, started_at, ended_at, duration_s, audio_played)
            VALUES ($1, $2, $3, NOW(), NOW(), 90, FALSE)
            """,
            uuid.UUID(student_id),
            unit_id,
            _CURRICULUM,
        )


async def _quiz(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    *,
    completed: bool,
    passed: bool = False,
    score: int | None = None,
) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, $4, 'Status', NOW(), NOW(), $5, 10, $6, 1, $7)
            """,
            uuid.UUID(student_id),
            unit_id,
            _CURRICULUM,
            _GRADE,
            score,
            completed,
            passed,
        )


async def _status(client: AsyncClient, student_id: str, unit_id: str) -> dict:
    """Refresh the view, then read the row the progress map would read."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("REFRESH MATERIALIZED VIEW mv_student_curriculum_progress")
        row = await conn.fetchrow(
            """
            SELECT status, attempts, best_score
            FROM mv_student_curriculum_progress
            WHERE student_id = $1 AND unit_id = $2 AND curriculum_id = $3
            """,
            uuid.UUID(student_id),
            unit_id,
            _CURRICULUM,
        )
    return dict(row) if row else {"status": "not_started", "attempts": 0, "best_score": None}


@pytest.mark.asyncio
async def test_reading_the_lesson_puts_the_unit_in_progress(client, db_conn):
    """The reported case: the state that could never appear."""
    student = await _student(client)
    await _unit(client, "ST-LESSON-1")
    await _view_lesson(client, student, "ST-LESSON-1")

    assert (await _status(client, student, "ST-LESSON-1"))["status"] == "in_progress"


@pytest.mark.asyncio
async def test_an_untouched_unit_is_still_not_started(client, db_conn):
    """Guard against the opposite error — marking everything in progress."""
    student = await _student(client)
    await _unit(client, "ST-UNTOUCHED-1")

    assert (await _status(client, student, "ST-UNTOUCHED-1"))["status"] == "not_started"


@pytest.mark.asyncio
async def test_passing_the_quiz_beats_the_lesson_view(client, db_conn):
    student = await _student(client)
    await _unit(client, "ST-PASS-1")
    await _view_lesson(client, student, "ST-PASS-1")
    await _quiz(client, student, "ST-PASS-1", completed=True, passed=True, score=9)

    assert (await _status(client, student, "ST-PASS-1"))["status"] == "completed"


@pytest.mark.asyncio
async def test_a_failed_quiz_beats_the_lesson_view(client, db_conn):
    """needs_retry must not be masked back to in_progress by the lesson."""
    student = await _student(client)
    await _unit(client, "ST-FAIL-1")
    await _view_lesson(client, student, "ST-FAIL-1")
    await _quiz(client, student, "ST-FAIL-1", completed=True, passed=False, score=3)

    assert (await _status(client, student, "ST-FAIL-1"))["status"] == "needs_retry"


@pytest.mark.asyncio
async def test_a_lesson_view_is_not_a_quiz_attempt(client, db_conn):
    """Reading is not attempting — the quiz figures must stay quiz figures."""
    student = await _student(client)
    await _unit(client, "ST-COUNT-1")
    await _view_lesson(client, student, "ST-COUNT-1")
    await _view_lesson(client, student, "ST-COUNT-1")

    row = await _status(client, student, "ST-COUNT-1")
    assert row["status"] == "in_progress", row
    assert row["attempts"] == 0, row
    assert row["best_score"] is None, row


@pytest.mark.asyncio
async def test_re_reading_a_lesson_does_not_duplicate_the_row(client, db_conn):
    """The view is UNIQUE on (student, unit, curriculum).

    A fan-out here would not merely double-count — it would break REFRESH
    MATERIALIZED VIEW CONCURRENTLY outright, since that requires the unique
    index.
    """
    student = await _student(client)
    await _unit(client, "ST-DUP-1")
    for _ in range(3):
        await _view_lesson(client, student, "ST-DUP-1")
    await _quiz(client, student, "ST-DUP-1", completed=False)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("REFRESH MATERIALIZED VIEW mv_student_curriculum_progress")
        count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM mv_student_curriculum_progress
            WHERE student_id = $1 AND unit_id = $2 AND curriculum_id = $3
            """,
            uuid.UUID(student),
            "ST-DUP-1",
            _CURRICULUM,
        )
    assert count == 1, count


@pytest.mark.asyncio
async def test_the_progress_map_surfaces_the_new_status(client, db_conn):
    """End to end through the endpoint the student actually looks at."""
    student = await _student(client)
    await _unit(client, "ST-MAP-1")
    await _view_lesson(client, student, "ST-MAP-1")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("REFRESH MATERIALIZED VIEW mv_student_curriculum_progress")

    token = make_student_token(student_id=student, grade=_GRADE)
    r = await client.get("/api/v1/student/progress", headers=_auth(token))
    assert r.status_code == 200, r.text

    units = [u for s in r.json()["subjects"] for u in s["units"]]
    mine = next((u for u in units if u["unit_id"] == "ST-MAP-1"), None)
    assert mine is not None, r.json()
    assert mine["status"] == "in_progress", mine
