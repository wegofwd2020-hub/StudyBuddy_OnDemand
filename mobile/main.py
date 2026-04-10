"""
mobile/main.py

Kivy application entry point.

On startup:
  1. Initialise SQLite paths from Kivy user_data_dir.
  2. Perform app version check against backend.
     - If below minimum_version: show upgrade modal and block.
     - If below latest_version: show non-blocking upgrade banner.
  3. Navigate to login screen.

This module never calls Anthropic or any AI service directly.
All network calls are through mobile/src/api/.
"""

from __future__ import annotations

import asyncio
import logging
import os
from threading import Thread
from typing import Optional

from kivy.app import App
from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, NoTransition

import config as cfg

log = logging.getLogger("mobile.main")

# ── App version — single source of truth is config.py ─────────────────────────
# Never hardcode the version here; config.APP_VERSION is updated at release time.
APP_VERSION = cfg.APP_VERSION


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert "1.2.3" → (1, 2, 3) for comparison."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


# ── Version check helpers ──────────────────────────────────────────────────────

def _show_upgrade_required(min_version: str) -> None:
    """Show a blocking modal that prevents app use until upgraded."""
    content = BoxLayout(orientation="vertical", padding=16, spacing=12)
    content.add_widget(Label(
        text=(
            f"This version of StudyBuddy ({APP_VERSION}) is no longer supported.\n\n"
            f"Minimum required: {min_version}\n\n"
            "Please update the app to continue."
        ),
        halign="center",
        font_size="15sp",
    ))
    btn = Button(text="OK", size_hint=(1, None), height=44)
    content.add_widget(btn)

    popup = Popup(
        title="Update Required",
        content=content,
        size_hint=(0.85, 0.45),
        auto_dismiss=False,
    )
    btn.bind(on_press=lambda *_: None)  # force user to update — no dismiss
    popup.open()


def _show_upgrade_banner(latest_version: str) -> None:
    """Show a non-blocking notification about a newer version."""
    content = BoxLayout(orientation="vertical", padding=12, spacing=10)
    content.add_widget(Label(
        text=(
            f"A newer version ({latest_version}) is available.\n"
            "Update for the best experience."
        ),
        halign="center",
        font_size="14sp",
    ))
    btn = Button(text="Dismiss", size_hint=(1, None), height=40)
    content.add_widget(btn)

    popup = Popup(
        title="Update Available",
        content=content,
        size_hint=(0.8, 0.38),
        auto_dismiss=True,
    )
    btn.bind(on_press=popup.dismiss)
    popup.open()


# ── Async version check (runs in daemon thread) ───────────────────────────────

def _check_version_thread() -> None:
    """
    Run in a daemon thread.  Calls GET /app/version and triggers the
    appropriate UI response on the main thread.

    The endpoint is unauthenticated — no token is needed or sent.
    """
    async def _fetch():
        from mobile.src.api.content_client import get_app_version
        return await get_app_version()

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_fetch())
        loop.close()

        min_v = result.get("min_version", "0.0.0")
        latest_v = result.get("latest_version", APP_VERSION)

        if _version_tuple(APP_VERSION) < _version_tuple(min_v):
            _show_upgrade_required_main(min_v)
        elif _version_tuple(APP_VERSION) < _version_tuple(latest_v):
            _show_upgrade_banner_main(latest_v)

    except Exception as exc:
        # Version check failure is non-fatal — app continues.
        log.warning("app_version_check_failed: %s", exc)


@mainthread
def _show_upgrade_required_main(min_version: str) -> None:
    _show_upgrade_required(min_version)


@mainthread
def _show_upgrade_banner_main(latest_version: str) -> None:
    _show_upgrade_banner(latest_version)


# ── Kivy App class ────────────────────────────────────────────────────────────

class StudyBuddyApp(App):
    """
    Main Kivy application.

    Responsibilities:
    - Initialise SQLite paths from Kivy's user_data_dir.
    - Launch app version check in a daemon thread on startup.
    - Provide the root ScreenManager to all screens.
    """

    def build(self) -> ScreenManager:
        # ── Initialise SQLite path ────────────────────────────────────────────
        cfg.SQLITE_DB_PATH = os.path.join(self.user_data_dir, "studybuddy.db")
        log.info("sqlite_path=%s", cfg.SQLITE_DB_PATH)

        # ── Set up screen manager ─────────────────────────────────────────────
        sm = ScreenManager(transition=NoTransition())
        # Screens are registered lazily on first navigation.
        # The login screen is the initial screen.
        self._sm = sm
        return sm

    def on_start(self) -> None:
        """Called after build().  Launch version check without blocking the UI."""
        t = Thread(target=_check_version_thread, daemon=True)
        t.start()

        # Navigate to login screen (or home screen if already authenticated).
        self._navigate_initial()

    def _read_stored_token(self) -> Optional[str]:
        """Read the stored internal JWT from disk.  Returns None if absent."""
        if not cfg.SQLITE_DB_PATH:
            return None
        token_path = os.path.join(self.user_data_dir, cfg.JWT_STORAGE_FILENAME)
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except FileNotFoundError:
            return None

    @mainthread
    def _navigate_initial(self) -> None:
        """Navigate to the appropriate initial screen after build."""
        # Screens will be registered by the UI layer.
        # For now, navigate to 'login' if it exists.
        sm = self._sm
        if sm.has_screen("login"):
            sm.current = "login"
        # else: screens not yet registered — UI layer handles first navigation.


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    StudyBuddyApp().run()


if __name__ == "__main__":
    main()
