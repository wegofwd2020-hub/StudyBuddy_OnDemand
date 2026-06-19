"""
tests/test_curriculum_content_flag.py

Unit tests for the per-unit `has_content` probe that backs the student curriculum
tree's content-availability gating (#468/#469). The probe greys out units whose
content has not been generated so the click doesn't dead-end on a 404.
"""

from __future__ import annotations

from src.curriculum.router import _has_content_map


class _FakeStorage:
    """Minimal StorageBackend stand-in: exists() is True for seeded paths."""

    def __init__(self, present: set[str], raises: set[str] | None = None):
        self._present = present
        self._raises = raises or set()

    async def exists(self, path: str) -> bool:
        if path in self._raises:
            raise OSError("storage unavailable")
        return path in self._present


async def test_has_content_map_flags_present_and_absent_units():
    cid = "default-2026-g8"
    storage = _FakeStorage(
        present={f"curricula/{cid}/G8-MATH-001/lesson_en.json"},
    )

    result = await _has_content_map(storage, cid, ["G8-MATH-001", "G8-MATH-002"])

    assert result == {"G8-MATH-001": True, "G8-MATH-002": False}


async def test_has_content_map_empty_units_returns_empty():
    storage = _FakeStorage(present=set())
    assert await _has_content_map(storage, "default-2026-g8", []) == {}


async def test_has_content_map_defaults_available_on_storage_error():
    # A storage hiccup must never hide content that may actually exist — the
    # probe defaults the unit to available rather than greying it out.
    cid = "default-2026-g8"
    storage = _FakeStorage(
        present=set(),
        raises={f"curricula/{cid}/G8-MATH-001/lesson_en.json"},
    )

    result = await _has_content_map(storage, cid, ["G8-MATH-001"])

    assert result == {"G8-MATH-001": True}
