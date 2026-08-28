"""
tests/test_analytics_missing_view.py

`end_lesson_view` must not explode when the view row is absent.

Found while draining the Celery backlog after the worker had been down: 29 stale
`write_lesson_end_task` messages referenced `lesson_views` rows that never
existed (the lesson had 404'd, so `startLessonView` never inserted one). The
UPDATE matched zero rows, `fetchrow` returned None, and `row["view_id"]` raised
TypeError. The task's blanket `except Exception: raise self.retry(...)` then
retried a write that can never succeed — a poison message burning worker slots.

A missing view is a permanent condition, not a transient fault: report it and
move on.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.analytics.service import end_lesson_view

_MISSING_VIEW_ID = "c9000000-0000-0000-0000-0000000000ff"


@pytest.mark.asyncio
async def test_end_lesson_view_on_missing_row_does_not_raise():
    """A view_id with no matching row returns cleanly instead of raising TypeError."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)  # UPDATE matched nothing

    result = await end_lesson_view(
        conn,
        view_id=_MISSING_VIEW_ID,
        duration_s=42,
        audio_played=False,
        experiment_viewed=False,
    )

    # Caller gets a well-formed answer it can log; nothing to retry.
    assert result["view_id"] == _MISSING_VIEW_ID
    assert result["updated"] is False


@pytest.mark.asyncio
async def test_end_lesson_view_on_existing_row_still_reports_success():
    """The happy path is unchanged."""
    conn = MagicMock()
    # Mirrors the real RETURNING clause, which since #675 also yields
    # student_id so the caller can refresh that student's progress status
    # without a second query.
    conn.fetchrow = AsyncMock(
        return_value={"view_id": "abc", "duration_s": 42, "student_id": "s-1"}
    )

    result = await end_lesson_view(
        conn,
        view_id="abc",
        duration_s=42,
        audio_played=True,
        experiment_viewed=False,
    )

    assert result["view_id"] == "abc"
    assert result["duration_s"] == 42
    assert result["updated"] is True
