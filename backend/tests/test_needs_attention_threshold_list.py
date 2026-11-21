"""
tests/test_needs_attention_threshold_list.py

"Needs attention" lists every current subject whose average is under the school's
saved pass-rate threshold, weakest first. It used to name only the single lowest
subject, which hid a second weak subject (Venki, 11 Nov).
"""

from __future__ import annotations

import uuid

import pytest

from src.reports.service import get_student_report
from tests.test_earlier_curriculum_activity_758 import _enrol
from tests.test_subject_breakdown_zero_attempts_763 import (
    _curriculum,
    _student_id,
    _student_on,
)


async def _score(client, student_id: str, unit_id: str, cid: str, code: str, score: int) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 11, $4, 1, TRUE, $5, $6, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            code,
            score >= 6,
            score,
        )


async def _save_threshold(client, school_id: str, threshold: float) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO report_alert_settings
                (school_id, pass_rate_threshold, inactive_days_threshold,
                 stuck_attempts_threshold, new_feedback_immediate, updated_at)
            VALUES ($1, $2, 14, 3, TRUE, NOW())
            """,
            uuid.UUID(school_id),
            threshold,
        )


@pytest.mark.asyncio
async def test_every_current_subject_under_the_saved_threshold_is_listed_weakest_first(
    client, db_conn
):
    student_id = _student_id("b7580000-0000-0000-0000-000000000011")
    cid = await _curriculum(
        client,
        11,
        [
            ("E-ENG-0011", "G11-ENG", "English"),
            ("E-MAT-0011", "G11-MATH", "Mathematics"),
            ("E-ACC-0011", "G11-ACC", "Accountancy"),
        ],
    )
    school_id = await _student_on(client, student_id, 11, cid)
    await _enrol(client, school_id, student_id, 11)
    await _save_threshold(client, school_id, 70.0)
    await _score(client, student_id, "E-MAT-0011", cid, "G11-MATH", score=4)
    await _score(client, student_id, "E-ENG-0011", cid, "G11-ENG", score=3)
    await _score(client, student_id, "E-ACC-0011", cid, "G11-ACC", score=7)

    pool = client._transport.app.state.pool
    redis = client._transport.app.state.redis
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        report = await get_student_report(conn, school_id, student_id, pool, redis)

    assert report["needs_attention_subjects"] == ["English", "Mathematics"], report
    assert report["strongest_subject"] == "Accountancy"
