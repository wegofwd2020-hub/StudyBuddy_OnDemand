"""
mobile/src/utils/i18n.py

UI string loader for the StudyBuddy mobile app.

Loads the appropriate language JSON from mobile/i18n/{lang}.json at startup.
Falls back to English on any missing key or unsupported language.

Usage:
    from mobile.src.utils.i18n import t, load_locale
    load_locale("fr")
    label = t("subject_screen.listen_btn")          # "🔊 Écouter"
    label = t("result_screen.score_label", score=7, total=10, pct=70)

Layer rule: i18n is in the utils layer — no imports from ui/, logic/, or api/.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Path to the i18n directory relative to this file's location.
# __file__ = mobile/src/utils/i18n.py  →  ../../.. = mobile/
_I18N_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "i18n")
_I18N_DIR = os.path.normpath(_I18N_DIR)

_SUPPORTED_LOCALES = ("en", "fr", "es")
_FALLBACK_LOCALE = "en"

# Module-level state: the active locale and its string table.
_locale: str = _FALLBACK_LOCALE
_strings: dict = {}
_fallback_strings: dict = {}


def _load_json(locale: str) -> dict:
    """Load and return the JSON for a given locale. Returns {} on error."""
    path = os.path.join(_I18N_DIR, f"{locale}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_locale(locale: str) -> None:
    """
    Load the string table for the given locale.

    Call once at app startup (or when the user changes language in Settings).
    Always loads English as the fallback before loading the target locale.

    Parameters
    ----------
    locale : str
        One of "en", "fr", "es".  Unsupported locales fall back to "en".
    """
    global _locale, _strings, _fallback_strings

    if locale not in _SUPPORTED_LOCALES:
        locale = _FALLBACK_LOCALE

    _fallback_strings = _load_json(_FALLBACK_LOCALE)
    _strings = _load_json(locale) if locale != _FALLBACK_LOCALE else _fallback_strings
    _locale = locale


def t(key: str, **kwargs: Any) -> str:
    """
    Translate a dot-separated key, interpolating any kwargs.

    Examples
    --------
    t("common.loading")                             # "Loading…"
    t("result_screen.score_label", score=7, total=10, pct=70)
    t("dashboard_screen.streak_label", count=5)

    Falls back to English if the key is missing in the active locale.
    Returns the key itself if missing in both.
    """
    # Ensure strings are loaded (lazy default to English)
    if not _strings and not _fallback_strings:
        load_locale(_FALLBACK_LOCALE)

    parts = key.split(".")
    value = _resolve(parts, _strings)

    # Fall back to English strings
    if value is None and _strings is not _fallback_strings:
        value = _resolve(parts, _fallback_strings)

    # Final fallback: return the key
    if value is None:
        return key

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value


def _resolve(parts: list[str], table: dict) -> str | None:
    """Walk nested dict by key parts. Returns None if any part is missing."""
    node: Any = table
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def current_locale() -> str:
    """Return the currently active locale code."""
    return _locale
