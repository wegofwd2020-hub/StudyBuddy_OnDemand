"""
tests/test_auth_tasks_progress.py

Progress-cluster Celery tasks from src/auth/tasks.py. PR #3 of Issue #261.

Covers four zero-coverage tasks on the student progress write path:
  - write_progress_answer_task  — fire-and-forget answer record
  - update_streak_task          — Redis streak counter logic (all branches)
  - refresh_progress_view_task  — REFRESH MATERIALIZED VIEW CONCURRENTLY
  - write_lesson_end_task       — fire-and-forget lesson-view end record

Same testing pattern as test_auth_tasks_identity.py (PR #2): invoke the
task via .run() with async dependencies mocked at module seams.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_pool_mock() -> tuple[MagicMock, AsyncMock]:
    """Async asyncpg pool where `async with pool.acquire() as conn:` yields conn."""
    pool = MagicMock()
    pool.close = AsyncMock()
    conn = AsyncMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=acquire_cm)
    return pool, conn


# ── write_progress_answer_task ────────────────────────────────────────────────


def test_write_progress_answer_task_records_answer_via_service():
    from src.auth.tasks import write_progress_answer_task

    pool, conn = _make_pool_mock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch(
            "src.progress.service.record_answer_sync", new_callable=AsyncMock
        ) as mock_record,
    ):
        write_progress_answer_task.run(
            session_id="sess-1",
            question_id="q-1",
            student_answer=2,
            correct_answer=3,
            correct=False,
            ms_taken=4500,
            event_id="evt-abc",
        )

    mock_record.assert_awaited_once_with(
        conn,
        session_id="sess-1",
        question_id="q-1",
        student_answer=2,
        correct_answer=3,
        correct=False,
        ms_taken=4500,
        event_id="evt-abc",
    )
    pool.close.assert_awaited_once()


def test_write_progress_answer_task_retries_on_db_error():
    from src.auth.tasks import write_progress_answer_task

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("pool timeout")),
    ):
        with pytest.raises(Exception):
            write_progress_answer_task.run(
                session_id="s", question_id="q", student_answer=1,
                correct_answer=1, correct=True, ms_taken=100, event_id=None,
            )


# ── update_streak_task (all branches) ─────────────────────────────────────────


def _streak_redis_mock(get_return: bytes | None = None) -> MagicMock:
    r = MagicMock()
    r.get = MagicMock(return_value=get_return)
    r.setex = MagicMock()
    r.close = MagicMock()
    return r


def test_update_streak_task_noop_when_activity_date_matches_last_active():
    from src.auth.tasks import update_streak_task

    existing = json.dumps(
        {"current": 5, "longest": 10, "last_active_date": "2026-04-20"}
    ).encode()
    r = _streak_redis_mock(get_return=existing)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-1", activity_date="2026-04-20")

    r.setex.assert_not_called()
    r.close.assert_called_once()


def test_update_streak_task_increments_on_consecutive_day():
    from src.auth.tasks import update_streak_task

    existing = json.dumps(
        {"current": 5, "longest": 7, "last_active_date": "2026-04-20"}
    ).encode()
    r = _streak_redis_mock(get_return=existing)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-1", activity_date="2026-04-21")

    r.setex.assert_called_once()
    _, _, payload = r.setex.call_args.args
    parsed = json.loads(payload)
    assert parsed["current"] == 6
    assert parsed["longest"] == 7  # current hasn't overtaken longest yet
    assert parsed["last_active_date"] == "2026-04-21"


def test_update_streak_task_resets_on_gap():
    from src.auth.tasks import update_streak_task

    existing = json.dumps(
        {"current": 5, "longest": 7, "last_active_date": "2026-04-18"}
    ).encode()
    r = _streak_redis_mock(get_return=existing)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-1", activity_date="2026-04-21")

    payload = r.setex.call_args.args[2]
    parsed = json.loads(payload)
    assert parsed["current"] == 1  # gap broke the streak
    assert parsed["longest"] == 7  # longest preserved


def test_update_streak_task_promotes_longest_when_current_exceeds_it():
    from src.auth.tasks import update_streak_task

    existing = json.dumps(
        {"current": 7, "longest": 7, "last_active_date": "2026-04-20"}
    ).encode()
    r = _streak_redis_mock(get_return=existing)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-1", activity_date="2026-04-21")

    parsed = json.loads(r.setex.call_args.args[2])
    assert parsed["current"] == 8
    assert parsed["longest"] == 8  # current > prior longest → promoted


def test_update_streak_task_handles_no_prior_streak():
    from src.auth.tasks import update_streak_task

    r = _streak_redis_mock(get_return=None)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-new", activity_date="2026-04-21")

    parsed = json.loads(r.setex.call_args.args[2])
    assert parsed == {"current": 1, "longest": 1, "last_active_date": "2026-04-21"}


def test_update_streak_task_handles_invalid_last_date_format():
    """Corrupt / migrated streak row with non-ISO last_active_date falls back to current=1."""
    from src.auth.tasks import update_streak_task

    existing = json.dumps(
        {"current": 5, "longest": 7, "last_active_date": "not-a-date"}
    ).encode()
    r = _streak_redis_mock(get_return=existing)

    with patch("redis.from_url", return_value=r):
        update_streak_task.run(student_id="stu-1", activity_date="2026-04-21")

    parsed = json.loads(r.setex.call_args.args[2])
    assert parsed["current"] == 1


def test_update_streak_task_retries_on_redis_error():
    from src.auth.tasks import update_streak_task

    with patch("redis.from_url", side_effect=RuntimeError("redis down")):
        with pytest.raises(Exception):
            update_streak_task.run(student_id="stu-1", activity_date="2026-04-21")


# ── refresh_progress_view_task ────────────────────────────────────────────────


def test_refresh_progress_view_task_refreshes_mv_and_invalidates_cache():
    from src.auth.tasks import refresh_progress_view_task

    pool, conn = _make_pool_mock()
    r = MagicMock()
    r.delete = MagicMock()
    r.close = MagicMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.from_url", return_value=r),
    ):
        refresh_progress_view_task.run(student_id="stu-1")

    conn.execute.assert_awaited_once_with(
        "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_student_curriculum_progress"
    )
    r.delete.assert_called_once_with("dashboard:stu-1")
    pool.close.assert_awaited_once()
    r.close.assert_called_once()


def test_refresh_progress_view_task_retries_on_db_error():
    from src.auth.tasks import refresh_progress_view_task

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("mv lock")),
    ):
        with pytest.raises(Exception):
            refresh_progress_view_task.run(student_id="stu-1")


# ── write_lesson_end_task ─────────────────────────────────────────────────────


def test_write_lesson_end_task_invokes_end_lesson_view():
    from src.auth.tasks import write_lesson_end_task

    pool, conn = _make_pool_mock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch(
            "src.analytics.service.end_lesson_view", new_callable=AsyncMock
        ) as mock_end,
    ):
        write_lesson_end_task.run(
            view_id="view-1",
            duration_s=240,
            audio_played=True,
            experiment_viewed=False,
        )

    mock_end.assert_awaited_once_with(
        conn,
        view_id="view-1",
        duration_s=240,
        audio_played=True,
        experiment_viewed=False,
    )
    pool.close.assert_awaited_once()


def test_write_lesson_end_task_retries_on_db_error():
    from src.auth.tasks import write_lesson_end_task

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("pool timeout")),
    ):
        with pytest.raises(Exception):
            write_lesson_end_task.run(
                view_id="view-x",
                duration_s=10,
                audio_played=False,
                experiment_viewed=False,
            )
