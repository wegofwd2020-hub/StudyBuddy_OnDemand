"""
tests/test_feedback_463.py

Regression test for feedback #463 — Unit Progress "Best score" must be a real
percentage, not the raw question count rendered with a "%" sign (e.g. score 6
shown as "6%"). best_score_pct = MAX(score / total_questions * 100), clamped to
100 to defend against legacy score > total rows (see #460).

Exercises analytics.get_student_metrics directly; reports.get_student_report
uses the identical SQL/clamp.
"""

from __future__ import annotations

import uuid

import pytest

from src.analytics.service import get_student_metrics


async def _student(db_conn, sid: uuid.UUID) -> None:
    await db_conn.execute(
        "INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status) "
        "VALUES ($1, $2, $3, $4, 8, 'en', 'active')",
        sid,
        f"auth0|test-{sid.hex[:18]}",
        "Best Score Tester",
        f"bs-{sid.hex[:8]}@test.invalid",
    )


async def _session(
    db_conn,
    sid: uuid.UUID,
    unit_id: str,
    score: int,
    total: int,
    *,
    attempt: int = 1,
    passed: bool = True,
) -> None:
    await db_conn.execute(
        """
        INSERT INTO progress_sessions
            (student_id, unit_id, curriculum_id, grade, subject,
             attempt_number, score, total_questions, completed, passed)
        VALUES ($1, $2, 'default-2026-g8', 8, 'G8-MATH', $3, $4, $5, TRUE, $6)
        """,
        sid,
        unit_id,
        attempt,
        score,
        total,
        passed,
    )


@pytest.mark.asyncio
async def test_best_score_is_percentage(db_conn):
    """score 6 of 8 → 75%, not 6."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _session(db_conn, sid, "G8-MATH-001", score=6, total=8)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-001")
    assert unit["best_score_pct"] == 75.0


@pytest.mark.asyncio
async def test_best_score_clamped_to_100(db_conn):
    """Legacy score > total (9 of 5 = 180%) is clamped to 100, not shown as 180%."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _session(db_conn, sid, "G8-MATH-002", score=9, total=5)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-002")
    assert unit["best_score_pct"] == 100.0


@pytest.mark.asyncio
async def test_best_score_takes_max_across_attempts(db_conn):
    """Best = highest percentage across attempts (25% then 87.5% → 87.5)."""
    sid = uuid.uuid4()
    await _student(db_conn, sid)
    await _session(db_conn, sid, "G8-MATH-003", score=2, total=8, attempt=1, passed=False)
    await _session(db_conn, sid, "G8-MATH-003", score=7, total=8, attempt=2, passed=True)

    result = await get_student_metrics(db_conn, str(sid))
    unit = next(u for u in result["per_unit"] if u["unit_id"] == "G8-MATH-003")
    assert unit["best_score_pct"] == 87.5
