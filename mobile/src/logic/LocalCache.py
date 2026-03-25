"""
mobile/src/logic/LocalCache.py

SQLite-based local content cache for the StudyBuddy mobile app.

Schema:
  cached_content(unit_id, curriculum_id, content_type, lang, content_version,
                 data TEXT, cached_at TEXT)

Methods:
  get(unit_id, curriculum_id, content_type, lang, content_version) → dict|None
  put(unit_id, curriculum_id, content_type, lang, content_version, data: dict)
  evict_lru(max_mb)  — enforce MAX_CACHE_MB limit

Layer rule: LocalCache is used by logic layer only; never imported by UI.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Optional

try:
    from mobile.config import SQLITE_PATH, MAX_CACHE_MB  # type: ignore
except ImportError:
    SQLITE_PATH = os.path.join(os.path.expanduser("~"), ".studybuddy", "cache.db")
    MAX_CACHE_MB = 100


class LocalCache:
    """
    Thread-safe SQLite cache for pre-fetched content JSON.

    Each entry is keyed by (unit_id, curriculum_id, content_type, lang, content_version).
    LRU eviction enforces the MAX_CACHE_MB limit.
    """

    def __init__(self, db_path: Optional[str] = None, max_mb: Optional[int] = None):
        self._db_path = db_path or SQLITE_PATH
        self._max_mb = max_mb or MAX_CACHE_MB
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the cache table if it doesn't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_content (
                    unit_id         TEXT NOT NULL,
                    curriculum_id   TEXT NOT NULL,
                    content_type    TEXT NOT NULL,
                    lang            TEXT NOT NULL,
                    content_version INTEGER NOT NULL,
                    data            TEXT NOT NULL,
                    cached_at       TEXT NOT NULL DEFAULT (datetime('now')),
                    last_accessed   TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (unit_id, curriculum_id, content_type, lang)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_cc_accessed
                ON cached_content(last_accessed)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def get(
        self,
        unit_id: str,
        curriculum_id: str,
        content_type: str,
        lang: str,
        content_version: int,
    ) -> Optional[dict]:
        """
        Return cached content dict, or None if not cached / version mismatch.
        Updates last_accessed timestamp on hit.
        """
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT data, content_version FROM cached_content
                    WHERE unit_id = ? AND curriculum_id = ? AND content_type = ? AND lang = ?
                    """,
                    (unit_id, curriculum_id, content_type, lang),
                ).fetchone()

                if row is None:
                    return None

                cached_version = row[1]
                if cached_version != content_version:
                    # Stale — evict this entry
                    conn.execute(
                        "DELETE FROM cached_content WHERE unit_id = ? AND curriculum_id = ? AND content_type = ? AND lang = ?",
                        (unit_id, curriculum_id, content_type, lang),
                    )
                    conn.commit()
                    return None

                # Update last_accessed for LRU
                conn.execute(
                    """
                    UPDATE cached_content SET last_accessed = datetime('now')
                    WHERE unit_id = ? AND curriculum_id = ? AND content_type = ? AND lang = ?
                    """,
                    (unit_id, curriculum_id, content_type, lang),
                )
                conn.commit()

                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None

    def put(
        self,
        unit_id: str,
        curriculum_id: str,
        content_type: str,
        lang: str,
        content_version: int,
        data: dict,
    ) -> None:
        """
        Insert or replace a cache entry. Triggers LRU eviction if needed.
        """
        serialized = json.dumps(data, ensure_ascii=False)

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cached_content
                        (unit_id, curriculum_id, content_type, lang, content_version,
                         data, cached_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """,
                    (unit_id, curriculum_id, content_type, lang, content_version, serialized),
                )
                conn.commit()

        # Evict if over limit
        self.evict_lru(self._max_mb)

    def evict_lru(self, max_mb: int) -> None:
        """
        Evict least-recently-used entries until the cache is below max_mb.
        """
        max_bytes = max_mb * 1024 * 1024

        with self._lock:
            with self._connect() as conn:
                # Get total data size
                total_row = conn.execute(
                    "SELECT SUM(LENGTH(data)) FROM cached_content"
                ).fetchone()
                total_bytes = total_row[0] or 0

                if total_bytes <= max_bytes:
                    return

                # Fetch LRU entries ordered by last_accessed ASC
                rows = conn.execute(
                    """
                    SELECT unit_id, curriculum_id, content_type, lang, LENGTH(data)
                    FROM cached_content
                    ORDER BY last_accessed ASC
                    """
                ).fetchall()

                bytes_to_free = total_bytes - max_bytes
                freed = 0
                evicted = 0

                for row in rows:
                    if freed >= bytes_to_free:
                        break
                    conn.execute(
                        "DELETE FROM cached_content WHERE unit_id = ? AND curriculum_id = ? AND content_type = ? AND lang = ?",
                        (row[0], row[1], row[2], row[3]),
                    )
                    freed += row[4] or 0
                    evicted += 1

                conn.commit()

    def clear(self) -> None:
        """Remove all entries. Used in tests."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM cached_content")
                conn.commit()
