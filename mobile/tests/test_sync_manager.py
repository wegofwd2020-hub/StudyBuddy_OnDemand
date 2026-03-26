"""
mobile/tests/test_sync_manager.py

Tests for mobile/src/logic/SyncManager.py

Uses a fake api_client and a real EventQueue (in-memory SQLite path).
All tests run synchronously via flush(blocking=True).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mobile.src.logic.EventQueue import EventQueue  # noqa: E402
from mobile.src.logic.SyncManager import SyncManager  # noqa: E402


# ── Fake API client ────────────────────────────────────────────────────────────

class FakeApiClient:
    """Records calls made by SyncManager._dispatch."""

    def __init__(self, fail_on: set = None):
        self.calls = []
        self._fail_on = fail_on or set()

    def record_answer(self, session_id, question_id, student_answer,
                      correct_answer, correct, ms_taken, event_id):
        if "record_answer" in self._fail_on:
            raise RuntimeError("simulated record_answer failure")
        self.calls.append(("record_answer", {
            "session_id": session_id,
            "question_id": question_id,
            "event_id": event_id,
        }))

    def end_lesson_view(self, view_id, duration_s, audio_played, experiment_viewed):
        if "end_lesson_view" in self._fail_on:
            raise RuntimeError("simulated end_lesson_view failure")
        self.calls.append(("end_lesson_view", {
            "view_id": view_id,
            "duration_s": duration_s,
            "audio_played": audio_played,
            "experiment_viewed": experiment_viewed,
        }))


@pytest.fixture
def queue(tmp_path):
    q = EventQueue(db_path=str(tmp_path / "test_queue.db"))
    yield q


@pytest.fixture
def api():
    return FakeApiClient()


# ── Flush with no events ───────────────────────────────────────────────────────

def test_flush_does_nothing_when_queue_empty(queue, api):
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)
    assert api.calls == []


# ── lesson_end dispatch ────────────────────────────────────────────────────────

def test_flush_dispatches_lesson_end(queue, api):
    queue.enqueue("lesson_end", {
        "view_id": "v-abc",
        "duration_s": 120,
        "audio_played": True,
        "experiment_viewed": False,
    })
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    assert len(api.calls) == 1
    call_type, payload = api.calls[0]
    assert call_type == "end_lesson_view"
    assert payload["view_id"] == "v-abc"
    assert payload["duration_s"] == 120
    assert payload["audio_played"] is True


def test_flush_marks_lesson_end_as_sent(queue, api):
    queue.enqueue("lesson_end", {"view_id": "v-abc", "duration_s": 60})
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)
    assert queue.pending() == []


# ── progress_answer dispatch ───────────────────────────────────────────────────

def test_flush_dispatches_progress_answer(queue, api):
    queue.enqueue("progress_answer", {
        "session_id": "sess-1",
        "question_id": "q-1",
        "student_answer": 2,
        "correct_answer": 2,
        "correct": True,
        "ms_taken": 3500,
    })
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    assert len(api.calls) == 1
    call_type, payload = api.calls[0]
    assert call_type == "record_answer"
    assert payload["session_id"] == "sess-1"


# ── Multiple events ───────────────────────────────────────────────────────────

def test_flush_dispatches_multiple_events_in_order(queue, api):
    queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 10})
    queue.enqueue("lesson_end", {"view_id": "v2", "duration_s": 20})
    queue.enqueue("progress_answer", {
        "session_id": "s1", "question_id": "q1",
        "student_answer": 0, "correct_answer": 1, "correct": False, "ms_taken": 1000,
    })

    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    assert len(api.calls) == 3
    assert queue.pending() == []


# ── Failure handling ───────────────────────────────────────────────────────────

def test_failed_event_stays_pending(tmp_path):
    queue = EventQueue(db_path=str(tmp_path / "q.db"))
    api = FakeApiClient(fail_on={"end_lesson_view"})

    queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 30})
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    # Event should still be pending after failure
    assert len(queue.pending()) == 1


def test_successful_events_sent_even_if_one_fails(tmp_path):
    queue = EventQueue(db_path=str(tmp_path / "q.db"))
    api = FakeApiClient(fail_on={"end_lesson_view"})

    queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 30})  # will fail
    queue.enqueue("progress_answer", {
        "session_id": "s1", "question_id": "q1",
        "student_answer": 1, "correct_answer": 1, "correct": True, "ms_taken": 500,
    })  # should succeed

    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    assert len(api.calls) == 1  # only progress_answer succeeded
    pending = queue.pending()
    assert len(pending) == 1
    assert pending[0]["event_type"] == "lesson_end"


# ── Unknown event type ────────────────────────────────────────────────────────

def test_unknown_event_type_is_skipped_and_marked_sent(queue, api):
    queue.enqueue("unknown_future_event", {"data": "something"})
    sm = SyncManager(api, queue)
    sm.flush(blocking=True)

    assert api.calls == []
    # Unknown events are marked sent to prevent queue blockage
    assert queue.pending() == []


# ── Debounce ──────────────────────────────────────────────────────────────────

def test_concurrent_flush_is_debounced(queue, api):
    """Second flush() call while first is running is a no-op."""
    queue.enqueue("lesson_end", {"view_id": "v1", "duration_s": 10})
    sm = SyncManager(api, queue)

    # This test just validates no exception or double-dispatch
    sm.flush(blocking=False)
    sm.flush(blocking=False)  # should be no-op
    sm._flush_thread.join(timeout=5)
    assert len(api.calls) <= 1
