"""
mobile/src/ui/SettingsScreen.py

Settings screen — language picker + notification preferences.

UI sections:
  1. Language — buttons for English / Français / Español
     On change: updates locale in local storage, clears LocalCache content,
     navigates back to dashboard so next content load uses new locale.

  2. Notifications — toggle switches for streak reminders, weekly summary, quiz nudges
     On change: calls backend PUT /notifications/preferences in a daemon thread.

  3. Account — sign out button

Note:
  - Locale is authoritative from the JWT (set at Auth0 exchange time).
    SettingsScreen stores a *preferred* locale override locally which is sent
    to the backend on next token refresh (Phase 5).
  - Content cache is cleared on locale change so the next lesson load
    fetches the correct language file.

Layer rule: SettingsScreen is in the ui layer; calls logic/ and api/ via daemon threads.
"""

from __future__ import annotations

import os
import threading

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.uix.switch import Switch  # type: ignore
    from kivy.uix.scrollview import ScrollView  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    KIVY_AVAILABLE = True
except ImportError:
    # Allow import without Kivy (for unit tests)
    Screen = object  # type: ignore
    KIVY_AVAILABLE = False

try:
    from mobile.src.logic.LocalCache import LocalCache  # type: ignore
except ImportError:
    LocalCache = None  # type: ignore

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):
        return logging.getLogger(name)

log = get_logger("settings_screen")

_LOCALE_KEY = os.path.join(os.path.expanduser("~"), ".studybuddy", "locale.txt")
_SUPPORTED_LOCALES = [("en", "English"), ("fr", "Français"), ("es", "Español")]


def _read_locale() -> str:
    """Read the locally persisted locale override. Defaults to 'en'."""
    try:
        with open(_LOCALE_KEY) as f:
            return f.read().strip() or "en"
    except OSError:
        return "en"


def _write_locale(locale: str) -> None:
    """Persist the locale override to disk."""
    os.makedirs(os.path.dirname(_LOCALE_KEY), exist_ok=True)
    with open(_LOCALE_KEY, "w") as f:
        f.write(locale)


class SettingsScreen(Screen):
    """
    Settings screen with language picker and notification toggles.
    """

    def __init__(self, token: str, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self._token = token
        self._current_locale = _read_locale()
        self._prefs: dict = {"streak_reminders": True, "weekly_summary": True, "quiz_nudges": True}

        if KIVY_AVAILABLE:
            self._build_ui()
            self._load_prefs_async()

    def _build_ui(self) -> None:
        scroll = ScrollView()
        root = BoxLayout(orientation="vertical", padding=24, spacing=16, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        root.add_widget(Label(text="Settings", font_size=24, bold=True, size_hint_y=None, height=48))

        # ── Language ──────────────────────────────────────────────────────────
        root.add_widget(Label(text="Language", font_size=18, bold=True, size_hint_y=None, height=36))
        lang_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=8)
        for code, label in _SUPPORTED_LOCALES:
            btn = Button(text=label)
            btn.bind(on_release=lambda _, c=code: self._on_locale_change(c))
            lang_row.add_widget(btn)
        root.add_widget(lang_row)

        self._locale_status = Label(
            text=f"Current: {self._current_locale}",
            size_hint_y=None,
            height=28,
        )
        root.add_widget(self._locale_status)

        # ── Notifications ─────────────────────────────────────────────────────
        root.add_widget(Label(text="Notifications", font_size=18, bold=True, size_hint_y=None, height=36))

        self._streak_switch = self._pref_row(root, "Streak reminders", "streak_reminders")
        self._weekly_switch = self._pref_row(root, "Weekly summary", "weekly_summary")
        self._quiz_switch = self._pref_row(root, "Quiz nudges", "quiz_nudges")

        # ── Account ───────────────────────────────────────────────────────────
        root.add_widget(Label(text="Account", font_size=18, bold=True, size_hint_y=None, height=36))
        sign_out_btn = Button(text="Sign out", size_hint_y=None, height=48)
        sign_out_btn.bind(on_release=self._on_sign_out)
        root.add_widget(sign_out_btn)

        scroll.add_widget(root)
        self.add_widget(scroll)

    def _pref_row(self, parent, label_text: str, pref_key: str) -> "Switch":
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48)
        row.add_widget(Label(text=label_text, size_hint_x=0.7))
        switch = Switch(active=self._prefs.get(pref_key, True), size_hint_x=0.3)
        switch.bind(active=lambda sw, val, k=pref_key: self._on_pref_change(k, val))
        row.add_widget(switch)
        parent.add_widget(row)
        return switch

    # ── Language change ───────────────────────────────────────────────────────

    def _on_locale_change(self, locale: str) -> None:
        """User selected a new language. Persist + clear content cache."""
        if locale == self._current_locale:
            return

        _write_locale(locale)
        self._current_locale = locale
        self._update_locale_label(locale)

        # Clear content cache so next lesson load fetches the new language
        def _clear():
            try:
                if LocalCache is not None:
                    LocalCache().clear()
                    log.info("content_cache_cleared_for_locale_change locale=%s", locale)
            except Exception as exc:
                log.warning("cache_clear_failed error=%s", exc)

        threading.Thread(target=_clear, daemon=True).start()

    @mainthread
    def _update_locale_label(self, locale: str) -> None:
        if hasattr(self, "_locale_status"):
            self._locale_status.text = f"Current: {locale}"

    # ── Notification preferences ──────────────────────────────────────────────

    def _load_prefs_async(self) -> None:
        """Fetch current preferences from backend in a daemon thread."""
        def _fetch():
            try:
                import asyncio
                from mobile.src.api.progress_client import get_notification_preferences  # type: ignore
                loop = asyncio.new_event_loop()
                prefs = loop.run_until_complete(get_notification_preferences(self._token))
                loop.close()
                self._prefs = prefs
                self._apply_prefs_to_ui(prefs)
            except Exception as exc:
                log.warning("load_prefs_failed error=%s", exc)

        threading.Thread(target=_fetch, daemon=True).start()

    @mainthread
    def _apply_prefs_to_ui(self, prefs: dict) -> None:
        if hasattr(self, "_streak_switch"):
            self._streak_switch.active = prefs.get("streak_reminders", True)
        if hasattr(self, "_weekly_switch"):
            self._weekly_switch.active = prefs.get("weekly_summary", True)
        if hasattr(self, "_quiz_switch"):
            self._quiz_switch.active = prefs.get("quiz_nudges", True)

    def _on_pref_change(self, key: str, value: bool) -> None:
        """Update a single preference in local state and sync to backend."""
        self._prefs[key] = value

        def _save():
            try:
                import asyncio
                from mobile.src.api.progress_client import update_notification_preferences  # type: ignore
                loop = asyncio.new_event_loop()
                loop.run_until_complete(
                    update_notification_preferences(
                        self._token,
                        streak_reminders=self._prefs.get("streak_reminders", True),
                        weekly_summary=self._prefs.get("weekly_summary", True),
                        quiz_nudges=self._prefs.get("quiz_nudges", True),
                    )
                )
                loop.close()
                log.info("notification_pref_updated key=%s value=%s", key, value)
            except Exception as exc:
                log.warning("pref_update_failed key=%s error=%s", key, exc)

        threading.Thread(target=_save, daemon=True).start()

    # ── Sign out ──────────────────────────────────────────────────────────────

    def _on_sign_out(self, *_) -> None:
        """Clear local token storage and navigate to login screen."""
        try:
            jwt_path = os.path.join(os.path.expanduser("~"), ".studybuddy", "token.json")
            if os.path.exists(jwt_path):
                os.remove(jwt_path)
        except OSError as exc:
            log.warning("sign_out_token_clear_failed error=%s", exc)

        if KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            self.manager.current = "login"
