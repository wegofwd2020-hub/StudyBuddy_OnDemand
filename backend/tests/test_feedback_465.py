"""
tests/test_feedback_465.py

Regression test for feedback #465 — Progress History showed duplicate
"Attempt #2" cards.

attempt_number was assigned at session start ("completed sessions + 1"), but
sessions are opened eagerly (one per quiz-page load, and the lesson page used
to open one too), so several never-completed sessions for a unit all received
the same number. end_session now numbers sessions in COMPLETION order, so each
finished attempt is uniquely sequential regardless of how many incomplete
sessions exist.
"""

from __future__ import annotations

import uuid

import pytest

from src.progress.service import create_session, end_session

_CID = "default-2026-g8"


async def _student(db_conn, sid: uuid.UUID) -> None:
    await db_conn.execute(
        "INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status) "
        "VALUES ($1, $2, $3, $4, 8, 'en', 'active')",
        sid,
        f"auth0|test-{sid.hex[:18]}",
        "Attempt Tester",
        f"att-{sid.hex[:8]}@test.invalid",
    )


@pytest.mark.asyncio
async def test_completed_attempts_numbered_sequentially(db_conn):
    """Two completed attempts on the same unit get attempt 1 then 2 (no dupes)."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)

    s1 = await create_session(db_conn, str(sid), "G8-MATH-001", _CID)
    e1 = await end_session(db_conn, s1["session_id"], 6, 8)
    assert e1["attempt_number"] == 1

    s2 = await create_session(db_conn, str(sid), "G8-MATH-001", _CID)
    e2 = await end_session(db_conn, s2["session_id"], 7, 8)
    assert e2["attempt_number"] == 2


@pytest.mark.asyncio
async def test_incomplete_sessions_do_not_inflate_attempt_number(db_conn):
    """Abandoned (never-completed) sessions don't bump the next attempt number."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)

    # Two sessions opened but never completed (e.g. quiz page loaded + left).
    await create_session(db_conn, str(sid), "G8-MATH-002", _CID)
    await create_session(db_conn, str(sid), "G8-MATH-002", _CID)

    # The first genuinely completed attempt is still #1.
    s = await create_session(db_conn, str(sid), "G8-MATH-002", _CID)
    e = await end_session(db_conn, s["session_id"], 5, 8)
    assert e["attempt_number"] == 1


@pytest.mark.asyncio
async def test_attempt_number_is_per_unit(db_conn):
    """Completing an attempt on one unit doesn't affect another unit's count."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)

    s1 = await create_session(db_conn, str(sid), "G8-MATH-003", _CID)
    await end_session(db_conn, s1["session_id"], 6, 8)

    s2 = await create_session(db_conn, str(sid), "G8-SCI-003", _CID)
    e2 = await end_session(db_conn, s2["session_id"], 6, 8)
    assert e2["attempt_number"] == 1
