"""
mobile/tests/test_event_queue.py

Tests for mobile/src/logic/EventQueue.py

All tests use a temporary SQLite path isolated per test.
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mobile.src.logic.EventQueue import EventQueue  # noqa: E402


@pytest.fixture
def queue(tmp_path):
    db_path = str(tmp_path / "test_queue.db")
    q = EventQueue(db_path=db_path)
    yield q


# ── Enqueue ───────────────────────────────────────────────────────────────────

def test_enqueue_returns_uuid(queue):
    event_id = queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 30})
    assert len(event_id) == 36  # UUID format
    assert event_id.count("-") == 4


def test_enqueue_returns_unique_ids(queue):
    id1 = queue.enqueue("lesson_end", {"view_id": "v1"})
    id2 = queue.enqueue("lesson_end", {"view_id": "v2"})
    assert id1 != id2


# ── Pending ───────────────────────────────────────────────────────────────────

def test_pending_returns_empty_on_new_queue(queue):
    assert queue.pending() == []


def test_pending_returns_enqueued_events(queue):
    queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 45})
    events = queue.pending()
    assert len(events) == 1
    assert events[0]["event_type"] == "lesson_end"
    assert events[0]["payload"]["view_id"] == "v1"


def test_pending_orders_by_created_at_asc(queue):
    queue.enqueue("lesson_end", {"view_id": "first"})
    time.sleep(0.01)
    queue.enqueue("progress_answer", {"session_id": "second"})
    events = queue.pending()
    assert events[0]["payload"]["view_id"] == "first"
    assert events[1]["event_type"] == "progress_answer"


def test_pending_excludes_sent_events(queue):
    id1 = queue.enqueue("lesson_end", {"view_id": "v1"})
    queue.enqueue("lesson_end", {"view_id": "v2"})
    queue.mark_sent(id1)
    events = queue.pending()
    assert len(events) == 1
    assert events[0]["payload"]["view_id"] == "v2"


# ── Mark sent ─────────────────────────────────────────────────────────────────

def test_mark_sent_removes_from_pending(queue):
    event_id = queue.enqueue("lesson_end", {"view_id": "v1"})
    assert len(queue.pending()) == 1
    queue.mark_sent(event_id)
    assert queue.pending() == []


def test_mark_sent_is_idempotent(queue):
    event_id = queue.enqueue("lesson_end", {"view_id": "v1"})
    queue.mark_sent(event_id)
    queue.mark_sent(event_id)  # should not raise
    assert queue.pending() == []


# ── Purge sent ────────────────────────────────────────────────────────────────

def test_purge_sent_deletes_old_sent_events(queue):
    event_id = queue.enqueue("lesson_end", {"view_id": "v1"})
    queue.mark_sent(event_id)
    # Purge with keep_days=0 to delete immediately
    deleted = queue.purge_sent(keep_days=0)
    assert deleted == 1


def test_purge_sent_does_not_delete_unsent_events(queue):
    queue.enqueue("lesson_end", {"view_id": "v1"})
    deleted = queue.purge_sent(keep_days=0)
    assert deleted == 0
    assert len(queue.pending()) == 1


# ── Clear ─────────────────────────────────────────────────────────────────────

def test_clear_removes_all_events(queue):
    queue.enqueue("lesson_end", {"view_id": "v1"})
    queue.enqueue("progress_answer", {"session_id": "s1"})
    queue.clear()
    assert queue.pending() == []
