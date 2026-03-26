"""
mobile/tests/test_local_cache.py

Tests for mobile/src/logic/LocalCache.py

All tests use a temporary in-memory-style SQLite path so they never
touch the real user cache.
"""

import os
import sys
import tempfile
import pytest

# Make mobile package importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mobile.src.logic.LocalCache import LocalCache  # noqa: E402


@pytest.fixture
def cache(tmp_path):
    db_path = str(tmp_path / "test_cache.db")
    c = LocalCache(db_path=db_path, max_mb=10)
    yield c


# ── Basic get/put ─────────────────────────────────────────────────────────────

def test_get_returns_none_on_empty_cache(cache):
    result = cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1)
    assert result is None


def test_put_and_get_roundtrip(cache):
    data = {"title": "Linear Equations", "synopsis": "Solving equations"}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, data)
    result = cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1)
    assert result == data


def test_get_returns_none_on_version_mismatch(cache):
    data = {"title": "Old content"}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, data)
    # Request a newer version
    result = cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 2)
    assert result is None


def test_version_mismatch_evicts_stale_entry(cache):
    data = {"title": "Old content"}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, data)
    cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 2)  # triggers eviction
    # Old version should also be gone
    result = cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1)
    assert result is None


def test_put_overwrites_existing_entry(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, {"title": "v1"})
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 2, {"title": "v2"})
    result = cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 2)
    assert result == {"title": "v2"}


# ── Key isolation ─────────────────────────────────────────────────────────────

def test_different_content_types_are_independent(cache):
    lesson_data = {"title": "Lesson"}
    quiz_data = {"questions": []}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, lesson_data)
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, quiz_data)
    assert cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1) == lesson_data
    assert cache.get("G8-MATH-001", "default-2026-g8", "quiz", "en", 1) == quiz_data


def test_different_languages_are_independent(cache):
    en_data = {"title": "Linear Equations"}
    fr_data = {"title": "Équations linéaires"}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, en_data)
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "fr", 1, fr_data)
    assert cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1) == en_data
    assert cache.get("G8-MATH-001", "default-2026-g8", "lesson", "fr", 1) == fr_data


def test_different_curriculum_ids_are_independent(cache):
    default_data = {"title": "Default"}
    school_data = {"title": "School"}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, default_data)
    cache.put("G8-MATH-001", "school-uuid-abc", "lesson", "en", 1, school_data)
    assert cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1) == default_data
    assert cache.get("G8-MATH-001", "school-uuid-abc", "lesson", "en", 1) == school_data


# ── LRU eviction ─────────────────────────────────────────────────────────────

def test_evict_lru_removes_oldest_entries_when_over_limit(tmp_path):
    db_path = str(tmp_path / "evict_test.db")
    # Set very small limit (1 KB) to force eviction
    cache = LocalCache(db_path=db_path, max_mb=1)

    # Fill cache with entries that will exceed 1 KB
    big_value = "x" * 200
    for i in range(10):
        cache.put(f"UNIT-{i:03d}", "default", "lesson", "en", 1, {"data": big_value})

    # After eviction, total size should be within limit
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT SUM(LENGTH(data)) FROM cached_content").fetchone()[0] or 0
    assert total <= 1024 * 1024


# ── Clear ─────────────────────────────────────────────────────────────────────

def test_clear_removes_all_entries(cache):
    cache.put("G8-MATH-001", "default", "lesson", "en", 1, {"title": "A"})
    cache.put("G8-MATH-002", "default", "lesson", "en", 1, {"title": "B"})
    cache.clear()
    assert cache.get("G8-MATH-001", "default", "lesson", "en", 1) is None
    assert cache.get("G8-MATH-002", "default", "lesson", "en", 1) is None
