"""
tests/test_placeholder_content.py

Placeholder content must never reach a student.

`scripts/seed_dev_content.py` and `scripts/setup_dev.py` fill gaps in the content
store with stub lessons/quizzes ("Sample question 1 about X?", options "Option A"
… "Option D", correct answer always "A"). They are tagged `model:
"dev-placeholder"`. Because the seeders only write where a file is *absent*, any
unit the pipeline has not generated keeps its stub indefinitely — and the serving
path used to hand it to students as if it were real, generated content.

The content service now treats a `dev-placeholder` file as absent, so the student
sees the ordinary "not available yet" state instead of a fake graded quiz.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.content.service import PLACEHOLDER_MODEL, get_content_file

# ── Fixtures ──────────────────────────────────────────────────────────────────

REAL_LESSON = {
    "unit_id": "G8-SCI-001",
    "title": "Density and Buoyancy",
    "sections": [{"heading": "Introduction", "body": "Real generated content."}],
    "model": "claude-sonnet-4-6",
    "content_version": 1,
}

PLACEHOLDER_LESSON = {
    "unit_id": "G8-SCI-001",
    "title": "Density and Buoyancy",
    "sections": [{"heading": "Overview", "body": "This lesson covers Density and Buoyancy."}],
    "model": PLACEHOLDER_MODEL,
    "content_version": 1,
}

PLACEHOLDER_QUIZ = {
    "unit_id": "G8-SCI-001",
    "questions": [
        {
            "question_text": "Sample question 1 about Density and Buoyancy?",
            "options": [{"option_id": "A", "text": "Option A"}],
            "correct_option": "A",
        }
    ],
    "model": PLACEHOLDER_MODEL,
}


def _redis(cached: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.get = AsyncMock(return_value=json.dumps(cached) if cached else None)
    r.set = AsyncMock()
    return r


def _storage(payload: dict) -> MagicMock:
    s = MagicMock()
    s.read_json = AsyncMock(return_value=payload)
    return s


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_placeholder_lesson_is_treated_as_absent():
    """A dev-placeholder lesson read from the store raises FileNotFoundError (→ 404)."""
    with pytest.raises(FileNotFoundError):
        await get_content_file(
            "default-2026-g8", "G8-SCI-001", "lesson_en.json",
            _redis(), _storage(PLACEHOLDER_LESSON),
        )


@pytest.mark.asyncio
async def test_placeholder_quiz_is_treated_as_absent():
    """The stub quiz (always-'A' answers) must never be served as a graded quiz."""
    with pytest.raises(FileNotFoundError):
        await get_content_file(
            "default-2026-g8", "G8-SCI-001", "quiz_set_1_en.json",
            _redis(), _storage(PLACEHOLDER_QUIZ),
        )


@pytest.mark.asyncio
async def test_placeholder_is_not_cached():
    """Rejected placeholders must not be written into the L2 cache."""
    redis = _redis()
    with pytest.raises(FileNotFoundError):
        await get_content_file(
            "default-2026-g8", "G8-SCI-001", "lesson_en.json",
            redis, _storage(PLACEHOLDER_LESSON),
        )
    redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_placeholder_already_in_cache_is_still_rejected():
    """A placeholder cached by an older build must still be refused on read."""
    storage = _storage(REAL_LESSON)  # store would return real content...
    with pytest.raises(FileNotFoundError):
        await get_content_file(
            "default-2026-g8", "G8-SCI-001", "lesson_en.json",
            _redis(cached=PLACEHOLDER_LESSON), storage,  # ...but cache holds a stub
        )
    storage.read_json.assert_not_called()  # served from cache, rejected there


@pytest.mark.asyncio
async def test_real_content_is_served_normally():
    """Pipeline-generated content is unaffected and still cached."""
    redis = _redis()
    data = await get_content_file(
        "default-2026-g8", "G8-SCI-001", "lesson_en.json",
        redis, _storage(REAL_LESSON),
    )
    assert data == REAL_LESSON
    redis.set.assert_called_once()
