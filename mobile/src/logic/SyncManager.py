"""
mobile/src/logic/SyncManager.py

Offline-to-online sync manager for the StudyBuddy mobile app.

Responsibilities:
  - Flush the EventQueue when the app comes to foreground or network is restored.
  - For each pending event, call the appropriate backend endpoint.
  - Mark each event as sent on success (backend deduplicates by event_id).
  - Run all network calls in a daemon thread — never blocks the Kivy event loop.

Usage:
  sync_manager = SyncManager(api_client, event_queue)
  sync_manager.flush()          # call on app foreground / network restore
  sync_manager.flush(blocking=True)  # for tests

Layer rule: SyncManager is in the logic layer; imports api/ but not ui/.
"""

from __future__ import annotations

import threading
from typing import Optional

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):  # type: ignore
        return logging.getLogger(name)

log = get_logger("sync_manager")


class SyncManager:
    """
    Flushes the EventQueue to the backend.

    Each event_type maps to a specific API call:
      progress_answer  → api_client.record_answer(session_id, ...)
      lesson_end       → api_client.end_lesson_view(view_id, ...)

    Unknown event types are logged and skipped (not retried).
    """

    def __init__(self, api_client, event_queue):
        """
        Parameters
        ----------
        api_client  : instance of mobile.src.api.progress_client (duck-typed)
        event_queue : instance of EventQueue
        """
        self._api = api_client
        self._queue = event_queue
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None

    def flush(self, blocking: bool = False) -> None:
        """
        Start a background flush.

        If a flush is already running, this call is a no-op (debounced).
        If blocking=True, runs synchronously in the calling thread (for tests).
        """
        if blocking:
            self._do_flush()
            return

        with self._lock:
            if self._flush_thread and self._flush_thread.is_alive():
                return  # already flushing
            self._flush_thread = threading.Thread(
                target=self._do_flush,
                daemon=True,
                name="SyncManager-flush",
            )
            self._flush_thread.start()

    def _do_flush(self) -> None:
        """Iterate over pending events and POST each to the backend."""
        events = self._queue.pending()
        if not events:
            return

        log.info("sync_flush_start pending=%d", len(events))
        sent = 0
        failed = 0

        for event in events:
            event_id = event["event_id"]
            event_type = event["event_type"]
            payload = event["payload"]

            try:
                self._dispatch(event_type, payload, event_id)
                self._queue.mark_sent(event_id)
                sent += 1
            except Exception as exc:
                log.warning("sync_event_failed event_id=%s event_type=%s error=%s", event_id, event_type, exc)
                failed += 1

        log.info("sync_flush_done sent=%d failed=%d", sent, failed)

        # Purge old delivered events
        try:
            deleted = self._queue.purge_sent(keep_days=7)
            if deleted:
                log.debug("sync_purged_old_events count=%d", deleted)
        except Exception as exc:
            log.warning("sync_purge_failed error=%s", exc)

    def _dispatch(self, event_type: str, payload: dict, event_id: str) -> None:
        """
        Route a single event to the correct API call.

        Raises on API error so the caller can decide whether to mark_sent or not.
        """
        if event_type == "progress_answer":
            # payload: session_id, question_id, student_answer, correct_answer, correct, ms_taken
            self._api.record_answer(
                session_id=payload["session_id"],
                question_id=payload["question_id"],
                student_answer=payload["student_answer"],
                correct_answer=payload["correct_answer"],
                correct=payload["correct"],
                ms_taken=payload.get("ms_taken", 0),
                event_id=event_id,
            )
        elif event_type == "lesson_end":
            # payload: view_id, duration_s, audio_played, experiment_viewed
            self._api.end_lesson_view(
                view_id=payload["view_id"],
                duration_s=payload["duration_s"],
                audio_played=payload.get("audio_played", False),
                experiment_viewed=payload.get("experiment_viewed", False),
            )
        else:
            log.warning("sync_unknown_event_type event_type=%s event_id=%s — skipping", event_type, event_id)
            # Mark as sent so it doesn't block the queue forever
            self._queue.mark_sent(event_id)
