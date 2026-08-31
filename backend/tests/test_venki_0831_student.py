"""Venki's 31 Aug round — the student-facing half.

Three reports, three different shapes:

  * "Answers are retained even after I log out and log in again — is this OK?"
    Resuming is right for an interruption and wrong for an abandonment, and there
    was no line between them: any not-completed session resumed however old, and
    since `started_at` is refreshed on every resume it could be revived forever.

  * "Can you include the Unit name also in this screen" — the quiz result screen
    showed only the subject ("MATHEMATICS"), which does not say which of that
    subject's units the score belongs to.

  * "Check the calculations used for Lessons Viewed in My Stats" — the WEB
    endpoint was already right (#668). The endpoint the MOBILE app calls was not:
    it still counted view events, and still averaged per-session percentages
    instead of weighting by questions (#669).

The metric tests assert the definitions against data where the right and wrong
formulas DISAGREE. A fixture where they coincide passes either way and proves
nothing — that is how one of these survived the first fix.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.progress.service import RESUME_WINDOW_HOURS, create_session
from src.student.service import get_stats


async def _student(client: AsyncClient) -> str:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students (student_id, external_auth_id, email, name, grade, locale)
            VALUES ($1, $2, $3, 'Stats Student', 10, 'en')
            """,
            uuid.UUID(student_id),
            f"auth0|stats-{student_id.replace('-', '')}",
            f"stats-{student_id[:8]}@example.com",
        )
    return student_id


async def _unit(client: AsyncClient, unit_id: str, title: str) -> str:
    pool = client._transport.app.state.pool
    curriculum_id = f"vstat-{uuid.uuid4().hex[:8]}"
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Stats Curriculum', 10, 2026, 'platform', FALSE)
            """,
            curriculum_id,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Mathematics', $3, $3, 1)
            """,
            unit_id,
            curriculum_id,
            title,
        )
    return curriculum_id


# ── Resume window ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_recent_unfinished_session_resumes(client, db_conn):
    """The behaviour that must survive: a refresh or a re-login is not a new attempt."""
    student_id = await _student(client)
    cid = await _unit(client, "VSTAT-RESUME-1", "Resumable Unit")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        first = await create_session(conn, student_id, "VSTAT-RESUME-1", cid)
        second = await create_session(conn, student_id, "VSTAT-RESUME-1", cid)

    assert second["session_id"] == first["session_id"], "a re-open must resume, not restart"
    assert second["attempt_number"] == first["attempt_number"]


@pytest.mark.asyncio
async def test_a_stale_unfinished_session_does_not_resume(client, db_conn):
    """The reported case, taken to its limit: an abandoned quiz must not reopen.

    Without the window this returns the SAME session id -- the months-old attempt
    comes back with its stale answers, graded against a set pinned at the time.
    """
    student_id = await _student(client)
    cid = await _unit(client, "VSTAT-STALE-1", "Abandoned Unit")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        first = await create_session(conn, student_id, "VSTAT-STALE-1", cid)
        # Age it past the window, as an abandoned session would age on its own.
        await conn.execute(
            "UPDATE progress_sessions SET started_at = $2 WHERE session_id = $1",
            uuid.UUID(first["session_id"]),
            datetime.now(UTC) - timedelta(hours=RESUME_WINDOW_HOURS + 1),
        )
        second = await create_session(conn, student_id, "VSTAT-STALE-1", cid)

    assert second["session_id"] != first["session_id"], "a stale session must not resume"


@pytest.mark.asyncio
async def test_a_stale_session_is_kept_not_destroyed(client, db_conn):
    """Ageing out must not delete or complete anything the student did."""
    student_id = await _student(client)
    cid = await _unit(client, "VSTAT-KEEP-1", "Old Attempt")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        first = await create_session(conn, student_id, "VSTAT-KEEP-1", cid)
        await conn.execute(
            "UPDATE progress_sessions SET started_at = $2 WHERE session_id = $1",
            uuid.UUID(first["session_id"]),
            datetime.now(UTC) - timedelta(hours=RESUME_WINDOW_HOURS + 1),
        )
        await create_session(conn, student_id, "VSTAT-KEEP-1", cid)
        row = await conn.fetchrow(
            "SELECT completed FROM progress_sessions WHERE session_id = $1",
            uuid.UUID(first["session_id"]),
        )

    assert row is not None, "the old session must still exist"
    assert row["completed"] is False, "ageing out is not completing"


# ── Mobile stats parity (#668 / #669) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_mobile_stats_counts_distinct_lessons_not_views(client, db_conn):
    """Chosen so the two formulas DISAGREE: 3 views over 2 units."""
    student_id = await _student(client)
    cid = await _unit(client, "VSTAT-LV-1", "Lesson One")
    await _unit(client, "VSTAT-LV-2", "Lesson Two")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for unit in ("VSTAT-LV-1", "VSTAT-LV-1", "VSTAT-LV-2"):
            await conn.execute(
                """
                INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)
                VALUES ($1, $2, $3, 60)
                """,
                uuid.UUID(student_id),
                unit,
                cid,
            )
        stats = await get_stats(conn, client._transport.app.state.redis, student_id, "30d")

    assert stats["lessons_viewed"] == 2, (
        f"expected 2 distinct lessons from 3 views, got {stats['lessons_viewed']}"
    )


@pytest.mark.asyncio
async def test_mobile_stats_average_is_weighted_by_questions(client, db_conn):
    """A 4-question quiz must not weigh the same as a 20-question one.

    2/4 (50%) and 18/20 (90%). Unweighted mean = 70.0; weighted = 20/24 = 83.3.
    The fixture exists to make those two numbers differ.
    """
    student_id = await _student(client)
    cid = await _unit(client, "VSTAT-AVG-1", "Weighted Unit")

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        for score, total in ((2, 4), (18, 20)):
            await conn.execute(
                """
                INSERT INTO progress_sessions
                    (student_id, unit_id, curriculum_id, grade, subject,
                     attempt_number, completed, passed, score, total_questions)
                VALUES ($1, $2, $3, 10, 'Mathematics', 1, TRUE, TRUE, $4, $5)
                """,
                uuid.UUID(student_id),
                "VSTAT-AVG-1",
                cid,
                score,
                total,
            )
        stats = await get_stats(conn, client._transport.app.state.redis, student_id, "30d")

    avg = round(float(stats["avg_quiz_score"]), 1)
    assert avg == 83.3, f"expected the weighted 83.3, got {avg} (70.0 means unweighted)"
