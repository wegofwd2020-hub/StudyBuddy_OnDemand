"""
tests/test_auth_tasks_notifications.py

Notification-cluster Celery tasks from src/auth/tasks.py. PR #4 of Issue #261.

Covers four zero-coverage tasks on the push-notification pipeline:
  - send_push_notification_task  — FCM wrapper (happy / retry)
  - check_streak_reminders       — daily 20:00 UTC; fan out to at-risk streaks
  - check_quiz_nudges            — daily 18:00 UTC; 3+ day inactivity
  - send_weekly_summary          — Sunday 09:00 UTC; past-week totals

Same .run() + mocked-seams pattern as PRs #267 (identity/audit) and
#268 (progress cluster). The three Beat tasks swallow exceptions with
a logged warning rather than retrying — tests assert error paths do
NOT raise, and happy paths dispatch the expected push fan-out.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── send_push_notification_task ───────────────────────────────────────────────


def test_send_push_notification_task_invokes_service():
    from src.auth.tasks import send_push_notification_task

    with patch(
        "src.notifications.service.send_push_notification", new_callable=AsyncMock
    ) as mock_send:
        send_push_notification_task.run(
            device_token="tok-123",
            title="Keep your streak alive! 🔥",
            body="You have a 5-day streak.",
            data={"deep_link": "/quiz"},
        )

    mock_send.assert_awaited_once_with(
        "tok-123", "Keep your streak alive! 🔥", "You have a 5-day streak.", {"deep_link": "/quiz"}
    )


def test_send_push_notification_task_retries_on_fcm_error():
    from src.auth.tasks import send_push_notification_task

    with patch(
        "src.notifications.service.send_push_notification",
        new_callable=AsyncMock,
        side_effect=RuntimeError("fcm 503"),
    ):
        with pytest.raises(Exception):
            send_push_notification_task.run(
                device_token="tok-x",
                title="t",
                body="b",
                data=None,
            )


# ── check_streak_reminders ────────────────────────────────────────────────────


def _streak_reminder_pool(rows: list[dict]) -> MagicMock:
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.close = AsyncMock()
    return pool


def test_check_streak_reminders_dispatches_for_at_risk_streaks():
    """Last active = yesterday → streak is at risk → push fired."""
    from datetime import date, timedelta

    from src.auth.tasks import check_streak_reminders

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    rows = [{"device_token": "tok-a", "student_id": "stu-1"}]

    pool = _streak_reminder_pool(rows)
    r = MagicMock()
    r.get = MagicMock(
        return_value=json.dumps(
            {"current": 5, "longest": 7, "last_active_date": yesterday}
        ).encode()
    )
    r.close = MagicMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.from_url", return_value=r),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        check_streak_reminders()

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["queue"] == "io"
    assert call_kwargs["kwargs"]["device_token"] == "tok-a"
    assert "5-day streak" in call_kwargs["kwargs"]["body"]


def test_check_streak_reminders_skips_when_last_active_is_today():
    """last_active_date != yesterday → no push (student already practised today or earlier)."""
    from src.auth.tasks import check_streak_reminders

    rows = [{"device_token": "tok-b", "student_id": "stu-2"}]
    pool = _streak_reminder_pool(rows)
    r = MagicMock()
    r.get = MagicMock(
        return_value=json.dumps(
            {"current": 5, "longest": 7, "last_active_date": "2020-01-01"}
        ).encode()
    )
    r.close = MagicMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.from_url", return_value=r),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        check_streak_reminders()

    mock_send.assert_not_called()


def test_check_streak_reminders_skips_students_without_streak_data():
    """raw=None → continue (student opted in but has no streak row yet)."""
    from src.auth.tasks import check_streak_reminders

    rows = [{"device_token": "tok-c", "student_id": "stu-3"}]
    pool = _streak_reminder_pool(rows)
    r = MagicMock()
    r.get = MagicMock(return_value=None)
    r.close = MagicMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.from_url", return_value=r),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        check_streak_reminders()

    mock_send.assert_not_called()


def test_check_streak_reminders_swallows_errors():
    """Exceptions are logged, not raised — the Beat schedule must not crash."""
    from src.auth.tasks import check_streak_reminders

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        # Must not raise.
        check_streak_reminders()


# ── check_quiz_nudges ─────────────────────────────────────────────────────────


def test_check_quiz_nudges_dispatches_one_push_per_row():
    from src.auth.tasks import check_quiz_nudges

    rows = [
        {"device_token": "tok-a"},
        {"device_token": "tok-b"},
        {"device_token": "tok-c"},
    ]
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.close = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        check_quiz_nudges()

    assert mock_send.call_count == 3
    for i, row in enumerate(rows):
        assert mock_send.call_args_list[i].kwargs["kwargs"]["device_token"] == row["device_token"]
        assert mock_send.call_args_list[i].kwargs["queue"] == "io"


def test_check_quiz_nudges_noop_when_no_rows():
    from src.auth.tasks import check_quiz_nudges

    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.close = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        check_quiz_nudges()

    mock_send.assert_not_called()


def test_check_quiz_nudges_swallows_errors():
    from src.auth.tasks import check_quiz_nudges

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        check_quiz_nudges()  # must not raise


# ── send_weekly_summary ───────────────────────────────────────────────────────


def test_send_weekly_summary_pluralises_for_multiple_quizzes():
    from src.auth.tasks import send_weekly_summary

    rows = [{"device_token": "tok-a", "quizzes_done": 5, "quizzes_passed": 4}]
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.close = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        send_weekly_summary()

    mock_send.assert_called_once()
    body = mock_send.call_args.kwargs["kwargs"]["body"]
    assert "5 quizzes" in body
    assert "4 passed" in body


def test_send_weekly_summary_uses_singular_for_one_quiz():
    """quizzes == 1 → 'quiz', not 'quizzes'."""
    from src.auth.tasks import send_weekly_summary

    rows = [{"device_token": "tok-a", "quizzes_done": 1, "quizzes_passed": 1}]
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.close = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        send_weekly_summary()

    body = mock_send.call_args.kwargs["kwargs"]["body"]
    assert "1 quiz," in body
    assert "quizzes" not in body


def test_send_weekly_summary_treats_null_counts_as_zero():
    """LEFT JOIN with no sessions yields None counts → fall back to 0."""
    from src.auth.tasks import send_weekly_summary

    rows = [{"device_token": "tok-a", "quizzes_done": None, "quizzes_passed": None}]
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.close = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.core.celery_app.celery_app.send_task") as mock_send,
    ):
        send_weekly_summary()

    body = mock_send.call_args.kwargs["kwargs"]["body"]
    assert "0 quizzes" in body
    assert "0 passed" in body


def test_send_weekly_summary_swallows_errors():
    from src.auth.tasks import send_weekly_summary

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        send_weekly_summary()  # must not raise
