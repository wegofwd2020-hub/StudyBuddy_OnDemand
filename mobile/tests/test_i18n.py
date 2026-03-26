"""
mobile/tests/test_i18n.py

Tests for mobile/src/utils/i18n.py

Validates loading, key resolution, interpolation, and fallback behaviour
for all three supported locales.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import mobile.src.utils.i18n as i18n  # noqa: E402


@pytest.fixture(autouse=True)
def reset_locale():
    """Reset to English before each test."""
    i18n.load_locale("en")
    yield
    i18n.load_locale("en")


# ── load_locale ────────────────────────────────────────────────────────────────

def test_load_locale_en():
    i18n.load_locale("en")
    assert i18n.current_locale() == "en"


def test_load_locale_fr():
    i18n.load_locale("fr")
    assert i18n.current_locale() == "fr"


def test_load_locale_es():
    i18n.load_locale("es")
    assert i18n.current_locale() == "es"


def test_load_unsupported_locale_falls_back_to_en():
    i18n.load_locale("de")  # unsupported
    assert i18n.current_locale() == "en"


# ── t() — English ─────────────────────────────────────────────────────────────

def test_t_returns_english_string():
    assert i18n.t("common.loading") == "Loading…"


def test_t_returns_nested_string():
    assert i18n.t("subject_screen.listen_btn") == "🔊 Listen"


def test_t_returns_key_for_missing_section():
    result = i18n.t("nonexistent_section.some_key")
    assert result == "nonexistent_section.some_key"


def test_t_returns_key_for_missing_key_in_section():
    result = i18n.t("common.nonexistent_key")
    assert result == "common.nonexistent_key"


# ── t() — interpolation ───────────────────────────────────────────────────────

def test_t_interpolates_single_kwarg():
    result = i18n.t("dashboard_screen.streak_label", count=5)
    assert result == "5 day streak 🔥"


def test_t_interpolates_multiple_kwargs():
    result = i18n.t("result_screen.score_label", score=7, total=10, pct=70)
    assert result == "Score: 7/10 (70%)"


def test_t_interpolates_name():
    result = i18n.t("dashboard_screen.greeting", name="Alice")
    assert result == "Hello, Alice!"


def test_t_returns_template_on_missing_kwarg():
    # If the kwarg is missing the raw template is returned
    result = i18n.t("result_screen.score_label")  # missing score, total, pct
    assert "{score}" in result or result == "result_screen.score_label"


# ── t() — French ─────────────────────────────────────────────────────────────

def test_t_french_listen_btn():
    i18n.load_locale("fr")
    assert i18n.t("subject_screen.listen_btn") == "🔊 Écouter"


def test_t_french_loading():
    i18n.load_locale("fr")
    assert i18n.t("common.loading") == "Chargement…"


def test_t_french_streak_with_interpolation():
    i18n.load_locale("fr")
    result = i18n.t("dashboard_screen.streak_label", count=3)
    assert result == "3 jours consécutifs 🔥"


# ── t() — Spanish ─────────────────────────────────────────────────────────────

def test_t_spanish_listen_btn():
    i18n.load_locale("es")
    assert i18n.t("subject_screen.listen_btn") == "🔊 Escuchar"


def test_t_spanish_quiz_btn():
    i18n.load_locale("es")
    assert i18n.t("subject_screen.quiz_btn") == "📝 Hacer el cuestionario"


def test_t_spanish_passed_heading():
    i18n.load_locale("es")
    assert "Superaste" in i18n.t("result_screen.passed_heading")


# ── Fallback to English ────────────────────────────────────────────────────────

def test_missing_key_in_fr_falls_back_to_english(tmp_path, monkeypatch):
    """If a key is absent in the active locale, fall back to English."""
    # Patch the i18n dir to a temp directory with only a partial fr.json
    partial_fr = tmp_path / "fr.json"
    partial_fr.write_text('{"common": {"loading": "Chargement partiel…"}}')
    en_full = tmp_path / "en.json"
    en_full.write_text('{"common": {"loading": "Loading…", "retry": "Retry"}}')

    monkeypatch.setattr(i18n, "_I18N_DIR", str(tmp_path))
    i18n.load_locale("fr")

    assert i18n.t("common.loading") == "Chargement partiel…"   # fr value
    assert i18n.t("common.retry") == "Retry"                   # fallback to en


# ── current_locale ─────────────────────────────────────────────────────────────

def test_current_locale_reflects_load():
    i18n.load_locale("es")
    assert i18n.current_locale() == "es"
    i18n.load_locale("en")
    assert i18n.current_locale() == "en"
