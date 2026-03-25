"""
mobile/src/logic/EventQueue.py

SQLite-backed offline event queue for the StudyBuddy mobile app.

All progress and analytics events are enqueued here when they occur.
SyncManager flushes the queue when the app is online.

Schema:
  event_queue(
      event_id   TEXT PRIMARY KEY,   -- UUID; used for backend deduplication
      event_type TEXT NOT NULL,      -- 'progress_answer' | 'lesson_end'
      payload    TEXT NOT NULL,      -- JSON blob
      created_at TEXT NOT NULL,
      sent_at    TEXT                -- NULL until successfully delivered
  )

Layer rule: EventQueue is used by logic layer only; never imported by UI.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional

try:
    from mobile.config import SQLITE_PATH  # type: ignore
except ImportError:
    SQLITE_PATH = os.path.join(os.path.expanduser("~"), ".studybuddy", "cache.db")


class EventQueue:
    """
    Thread-safe SQLite queue for offline event buffering.

    Events are identified by a UUID event_id.  The backend uses ON CONFLICT DO NOTHING
    on event_id so duplicate deliveries are safe.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or SQLITE_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the event_queue table if it doesn't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_queue (
                    event_id   TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload    TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent_at    TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_eq_pending
                ON event_queue(sent_at)
                WHERE sent_at IS NULL
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def enqueue(self, event_type: str, payload: dict) -> str:
        """
        Add a new event to the queue.

        Generates a UUID event_id that will be forwarded to the backend
        for deduplication.

        Returns the event_id.
        """
        event_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(payload, ensure_ascii=False)

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO event_queue (event_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                    (event_id, event_type, serialized, created_at),
                )
                conn.commit()

        return event_id

    def pending(self) -> List[dict]:
        """
        Return all unsent events, oldest first.

        Each item has: event_id, event_type, payload (dict), created_at.
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT event_id, event_type, payload, created_at
                    FROM event_queue
                    WHERE sent_at IS NULL
                    ORDER BY created_at ASC
                    """
                ).fetchall()

        events = []
        for row in rows:
            try:
                payload = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                payload = {}
            events.append({
                "event_id": row[0],
                "event_type": row[1],
                "payload": payload,
                "created_at": row[3],
            })
        return events

    def mark_sent(self, event_id: str) -> None:
        """Mark an event as successfully delivered."""
        sent_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE event_queue SET sent_at = ? WHERE event_id = ?",
                    (sent_at, event_id),
                )
                conn.commit()

    def purge_sent(self, keep_days: int = 7) -> int:
        """
        Delete sent events older than keep_days to keep the DB small.
        Returns the number of rows deleted.
        """
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM event_queue WHERE sent_at IS NOT NULL AND sent_at < ?",
                    (cutoff,),
                )
                conn.commit()
                return cursor.rowcount

    def clear(self) -> None:
        """Remove all entries. Used in tests."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM event_queue")
                conn.commit()
