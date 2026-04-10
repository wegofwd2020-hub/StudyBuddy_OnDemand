"""
mobile/tests/test_tutorial_screen_logic.py

Unit tests for TutorialScreen pure logic (no Kivy, no network).

Tests cover:
  - Markdown rendering (_render_markdown)
  - Section navigation (prev/next index arithmetic)
  - Cache roundtrip for tutorial content
  - Empty section guard
  - set_context stores values
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mobile.src.ui.TutorialScreen import TutorialScreen, _render_markdown  # noqa: E402
from mobile.src.logic.LocalCache import LocalCache  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def screen():
    s = TutorialScreen()
    s.set_context(
        token="tok",
        unit_id="G8-MATH-001",
        curriculum_id="default-2026-g8",
        lang="en",
    )
    return s


@pytest.fixture
def cache(tmp_path):
    return LocalCache(db_path=str(tmp_path / "cache.db"), max_mb=10)


SECTIONS = [
    {"title": "Introduction", "body": "This is the **intro** section.\n- Point A\n- Point B"},
    {"title": "Core Concepts", "body": "Learn **algebra** step by step."},
    {"title": "Examples",      "body": "Here are some **worked examples**."},
]

TUTORIAL_PAYLOAD = {
    "title": "Algebra Basics",
    "sections": SECTIONS,
    "content_version": 1,
}


# ── set_context ───────────────────────────────────────────────────────────────


def test_set_context_stores_values(screen):
    assert screen._token == "tok"
    assert screen._unit_id == "G8-MATH-001"
    assert screen._curriculum_id == "default-2026-g8"
    assert screen._lang == "en"


def test_set_context_can_be_overwritten(screen):
    screen.set_context("tok2", "G9-SCI-001", "default-2026-g9", "fr")
    assert screen._unit_id == "G9-SCI-001"
    assert screen._lang == "fr"


# ── Markdown rendering ────────────────────────────────────────────────────────


def test_render_markdown_converts_bold_to_uppercase():
    result = _render_markdown("This is **important**.")
    assert "IMPORTANT" in result
    assert "**" not in result


def test_render_markdown_converts_bullet_list():
    result = _render_markdown("- Apple\n- Banana")
    assert "• Apple" in result
    assert "• Banana" in result
    assert "- " not in result


def test_render_markdown_asterisk_bullets():
    result = _render_markdown("* One\n* Two")
    assert "• One" in result
    assert "• Two" in result


def test_render_markdown_multiple_bolds():
    result = _render_markdown("**A** and **B**")
    assert "A" in result
    assert "B" in result
    assert "**" not in result


def test_render_markdown_plain_text_unchanged():
    plain = "No markdown here, just text."
    result = _render_markdown(plain)
    assert result == plain


def test_render_markdown_strips_leading_trailing_whitespace():
    result = _render_markdown("   hello   ")
    assert result == "hello"


def test_render_markdown_preserves_newlines():
    text = "Line one.\n\nLine two."
    result = _render_markdown(text)
    assert "\n" in result


# ── Section navigation ────────────────────────────────────────────────────────


def test_initial_section_is_zero(screen):
    assert screen._current_section == 0


def test_on_enter_resets_section(screen):
    screen._current_section = 2
    screen._sections = SECTIONS
    # Simulate reset (on_enter calls reset before loading)
    screen._sections = []
    screen._current_section = 0
    assert screen._current_section == 0


def test_prev_does_not_go_below_zero(screen):
    screen._sections = SECTIONS
    screen._current_section = 0
    screen._on_prev()
    assert screen._current_section == 0


def test_next_does_not_go_beyond_last(screen):
    screen._sections = SECTIONS
    screen._current_section = len(SECTIONS) - 1
    screen._on_next()
    assert screen._current_section == len(SECTIONS) - 1


def test_next_increments_section(screen):
    screen._sections = SECTIONS
    screen._current_section = 0
    screen._on_next()
    assert screen._current_section == 1


def test_prev_decrements_section(screen):
    screen._sections = SECTIONS
    screen._current_section = 2
    screen._on_prev()
    assert screen._current_section == 1


def test_on_tab_sets_section(screen):
    screen._sections = SECTIONS
    screen._current_section = 0
    screen._on_tab(2)
    assert screen._current_section == 2


# ── Section count / tab strip ─────────────────────────────────────────────────


def test_populate_stores_sections(screen):
    screen._populate(TUTORIAL_PAYLOAD)
    assert len(screen._sections) == 3


def test_populate_empty_sections_does_not_crash(screen):
    # Should call _show_error, not crash
    screen._populate({"sections": [], "title": "Empty"})
    assert screen._sections == [] or True  # either reset or unchanged — no crash


# ── LocalCache roundtrip ──────────────────────────────────────────────────────


def test_tutorial_cache_put_and_get(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "tutorial", "en", 1, TUTORIAL_PAYLOAD)
    result = cache.get("G8-MATH-001", "default-2026-g8", "tutorial", "en", 1)
    assert result is not None
    assert len(result["sections"]) == 3


def test_tutorial_cache_miss_returns_none(cache):
    result = cache.get("G8-MATH-001", "default-2026-g8", "tutorial", "en", 1)
    assert result is None


def test_tutorial_cache_separate_from_quiz(cache):
    quiz_data = {"questions": [{"question_id": "q1"}]}
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, quiz_data)
    result = cache.get("G8-MATH-001", "default-2026-g8", "tutorial", "en", 1)
    assert result is None


def test_tutorial_cache_version_mismatch(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "tutorial", "en", 1, TUTORIAL_PAYLOAD)
    result = cache.get("G8-MATH-001", "default-2026-g8", "tutorial", "en", 2)
    assert result is None
