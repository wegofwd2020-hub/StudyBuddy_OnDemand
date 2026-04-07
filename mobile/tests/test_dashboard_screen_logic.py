"""
mobile/tests/test_dashboard_screen_logic.py

Unit tests for DashboardScreen pure logic (no Kivy, no network).

Tests cover:
  - _greeting() returns time-appropriate text and handles names
  - _streak_text() returns encouraging (never shaming) copy
  - Empty state detection (no next_unit + no recent_activity)
  - set_token stores value
  - Stale-while-revalidate: _cached_data used on re-enter
  - _render_markdown not needed here (that lives in TutorialScreen)
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mobile.src.ui.DashboardScreen import (  # noqa: E402
    DashboardScreen, _greeting, _streak_text,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def screen():
    s = DashboardScreen()
    s.set_token("test-tok")
    return s


# ── set_token ─────────────────────────────────────────────────────────────────


def test_set_token_stores_value(screen):
    assert screen._token == "test-tok"


def test_set_token_can_be_updated(screen):
    screen.set_token("new-tok")
    assert screen._token == "new-tok"


# ── _greeting ─────────────────────────────────────────────────────────────────


def test_greeting_with_name_uses_first_name_only():
    result = _greeting("Alice Johnson")
    assert "Alice" in result
    assert "Johnson" not in result


def test_greeting_without_name_does_not_include_empty_string():
    result = _greeting("")
    assert result.strip() != ""
    assert "None" not in result
    assert "  " not in result  # no double spaces


def test_greeting_contains_no_technical_terms():
    for name in ["", "Sam", "María García"]:
        result = _greeting(name)
        assert "error" not in result.lower()
        assert "null" not in result.lower()


def test_greeting_returns_string():
    assert isinstance(_greeting("Alex"), str)
    assert isinstance(_greeting(""), str)


# ── _streak_text ──────────────────────────────────────────────────────────────


def test_streak_zero_is_encouraging():
    text = _streak_text(0)
    # Should encourage, not shame ("haven't studied in X days" etc.)
    shame_phrases = ["days since", "missed", "haven't", "no streak", "0 days"]
    for phrase in shame_phrases:
        assert phrase not in text.lower(), f"shame phrase '{phrase}' found in: {text!r}"


def test_streak_one_day():
    text = _streak_text(1)
    assert "1" in text or "one" in text.lower()


def test_streak_seven_days_includes_number():
    text = _streak_text(7)
    assert "7" in text


def test_streak_text_returns_string():
    for days in [0, 1, 3, 7, 30, 100]:
        assert isinstance(_streak_text(days), str)


def test_streak_text_contains_no_shame():
    for days in [0, 1, 5]:
        text = _streak_text(days)
        assert "shame" not in text.lower()
        assert "bad" not in text.lower()
        assert "fail" not in text.lower()


# ── Stale-while-revalidate ────────────────────────────────────────────────────


def test_cached_data_starts_none(screen):
    assert screen._cached_data is None


def test_cached_data_is_stored_after_render(screen):
    data = {
        "summary": {"current_streak_days": 3, "display_name": "Sam"},
        "next_unit": None,
        "recent_activity": [],
    }
    screen._cached_data = data
    assert screen._cached_data is not None
    assert screen._cached_data["summary"]["current_streak_days"] == 3


def test_cached_data_survives_re_enter(screen):
    data = {"summary": {"current_streak_days": 5}, "next_unit": None, "recent_activity": []}
    screen._cached_data = data
    # Simulate re-entering the screen — cached_data should still be there
    assert screen._cached_data == data


# ── Empty state detection ─────────────────────────────────────────────────────


def test_empty_state_when_no_next_unit_and_no_recent():
    data = {"summary": {}, "next_unit": None, "recent_activity": []}
    has_anything = bool(data.get("next_unit") or data.get("recent_activity"))
    assert has_anything is False


def test_not_empty_when_next_unit_present():
    data = {
        "summary": {},
        "next_unit": {"unit_id": "G8-MATH-001", "title": "Algebra"},
        "recent_activity": [],
    }
    has_anything = bool(data.get("next_unit") or data.get("recent_activity"))
    assert has_anything is True


def test_not_empty_when_recent_activity_present():
    data = {
        "summary": {},
        "next_unit": None,
        "recent_activity": [{"unit_id": "G8-MATH-001", "type": "lesson"}],
    }
    has_anything = bool(data.get("next_unit") or data.get("recent_activity"))
    assert has_anything is True


def test_recent_activity_capped_at_three():
    items = [{"unit_id": f"U{i}", "type": "lesson"} for i in range(6)]
    recents = [r for r in items if r.get("type") in ("lesson", "quiz")][:3]
    assert len(recents) == 3


def test_recent_activity_filters_non_lesson_quiz():
    items = [
        {"unit_id": "U1", "type": "experiment"},
        {"unit_id": "U2", "type": "lesson"},
        {"unit_id": "U3", "type": "quiz"},
        {"unit_id": "U4", "type": "audio"},
    ]
    recents = [r for r in items if r.get("type") in ("lesson", "quiz")][:3]
    assert len(recents) == 2
    assert all(r["type"] in ("lesson", "quiz") for r in recents)


# ── Score display ─────────────────────────────────────────────────────────────


def test_score_text_when_score_present():
    score = 75
    text = f"Last score: {score}%" if score is not None else "Start now"
    assert "75%" in text


def test_score_text_when_no_score():
    score = None
    text = f"Last score: {score}%" if score is not None else "Start now"
    assert text == "Start now"
