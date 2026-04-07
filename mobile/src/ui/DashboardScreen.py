"""
mobile/src/ui/DashboardScreen.py

Home dashboard screen — shown immediately after login (#75).

Layout:
  ┌─────────────────────────────────┐
  │  Good morning, Sam              │
  │  🔥 7-day streak                │
  ├─────────────────────────────────┤
  │  Continue where you left off    │
  │  ┌───────────────────────────┐  │
  │  │ G8 · Mathematics          │  │
  │  │ Unit: Algebra Basics      │  │
  │  │ Last score: 75%  [Continue]│  │
  │  └───────────────────────────┘  │
  ├─────────────────────────────────┤
  │  Recently viewed                │
  │  [Unit card] [Unit card] ...    │
  ├─────────────────────────────────┤
  │  [Browse All Subjects]          │
  └─────────────────────────────────┘

Data strategy (stale-while-revalidate):
  - On enter: show _cached_data immediately (if available from last visit)
  - Always kick off an async fetch in the background
  - Refresh the display when fresh data arrives

Empty state (first-time user): "Start exploring →" prompt — no fake data,
no shame about streak length.

Layer rule: ui layer only. All network calls in daemon threads. @mainthread
on all UI mutations.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.scrollview import ScrollView  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object  # type: ignore
    mainthread = lambda f: f  # type: ignore
    KIVY_AVAILABLE = False

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):  # type: ignore
        return logging.getLogger(name)

log = get_logger("dashboard_screen")

_GREETING_HOURS = {
    range(5, 12): "Good morning",
    range(12, 18): "Good afternoon",
    range(18, 24): "Good evening",
}


def _greeting(display_name: str = "") -> str:
    """Return a time-appropriate greeting, optionally personalised."""
    hour = datetime.now().hour
    salutation = "Hey"
    for hours, text in _GREETING_HOURS.items():
        if hour in hours:
            salutation = text
            break
    if display_name:
        return f"{salutation}, {display_name.split()[0]}"
    return salutation


def _streak_text(days: int) -> str:
    """Return encouraging streak string. Never shaming."""
    if days == 0:
        return "Start your streak today!"
    if days == 1:
        return "🔥 1-day streak — great start!"
    return f"🔥 {days}-day streak — keep it going!"


class DashboardScreen(Screen):
    """
    Home screen shown after login.

    Usage:
        dashboard.set_token(token)
        screen_manager.current = "dashboard"
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._token: str = ""
        self._cached_data: dict | None = None   # stale-while-revalidate

        if KIVY_AVAILABLE:
            self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_token(self, token: str) -> None:
        self._token = token

    # ── Kivy lifecycle ────────────────────────────────────────────────────────

    def on_enter(self, *_) -> None:
        """Show cached data immediately, then refresh in background."""
        if self._cached_data:
            self._render(self._cached_data)
        else:
            self._set_loading()
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=20, spacing=0)

        # ── Header (greeting + streak) ────────────────────────────────────────
        header = BoxLayout(orientation="vertical", size_hint=(1, None), height=80, spacing=4)

        self._greeting_label = Label(
            text="Loading…",
            font_size="20sp",
            bold=True,
            halign="left",
            size_hint=(1, None),
            height=36,
        )
        self._greeting_label.bind(
            width=lambda *_: setattr(
                self._greeting_label, "text_size", (self._greeting_label.width, None)
            )
        )
        header.add_widget(self._greeting_label)

        self._streak_label = Label(
            text="",
            font_size="14sp",
            halign="left",
            color=(0.9, 0.5, 0.1, 1),
            size_hint=(1, None),
            height=28,
        )
        self._streak_label.bind(
            width=lambda *_: setattr(
                self._streak_label, "text_size", (self._streak_label.width, None)
            )
        )
        header.add_widget(self._streak_label)

        root.add_widget(header)

        # ── Scrollable content area ───────────────────────────────────────────
        scroll = ScrollView(size_hint=(1, 1))
        self._content = BoxLayout(
            orientation="vertical",
            spacing=12,
            size_hint_y=None,
            padding=(0, 8, 0, 8),
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        scroll.add_widget(self._content)
        root.add_widget(scroll)

        # ── Bottom nav ────────────────────────────────────────────────────────
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=52, spacing=8)

        browse_btn = Button(
            text="Browse All Subjects",
            font_size="14sp",
            size_hint=(0.7, 1),
        )
        browse_btn.bind(on_press=lambda *_: self._go("curriculum_map"))
        nav.add_widget(browse_btn)

        settings_btn = Button(
            text="⚙",
            font_size="18sp",
            size_hint=(0.15, 1),
        )
        settings_btn.bind(on_press=lambda *_: self._go("settings"))
        nav.add_widget(settings_btn)

        stats_btn = Button(
            text="📊",
            font_size="18sp",
            size_hint=(0.15, 1),
        )
        stats_btn.bind(on_press=lambda *_: self._go("stats"))
        nav.add_widget(stats_btn)

        root.add_widget(nav)

        self.add_widget(root)

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def _fetch_thread(self) -> None:
        """Daemon thread: fetch dashboard summary from backend."""
        import asyncio
        try:
            from mobile.src.api.progress_client import get_dashboard  # type: ignore
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_dashboard(self._token))
            loop.close()
            self._cached_data = data
            self._render(data)
            log.info("dashboard_fetched streak=%d",
                     data.get("summary", {}).get("current_streak_days", 0))
        except Exception as exc:
            log.warning("dashboard_fetch_failed error=%s", exc)
            if not self._cached_data:
                self._show_error("Could not load your dashboard. Check your connection.")

    # ── Render ────────────────────────────────────────────────────────────────

    @mainthread
    def _set_loading(self) -> None:
        if hasattr(self, "_greeting_label"):
            self._greeting_label.text = "Loading…"
        if hasattr(self, "_streak_label"):
            self._streak_label.text = ""
        if hasattr(self, "_content"):
            self._content.clear_widgets()

    @mainthread
    def _render(self, data: dict) -> None:
        """Build the full dashboard UI from response data."""
        summary = data.get("summary", {})
        next_unit = data.get("next_unit")
        recent = data.get("recent_activity", [])

        display_name: str = summary.get("display_name", "")
        streak: int = summary.get("current_streak_days", 0)

        # Header
        if hasattr(self, "_greeting_label"):
            self._greeting_label.text = _greeting(display_name)
        if hasattr(self, "_streak_label"):
            self._streak_label.text = _streak_text(streak)

        if not hasattr(self, "_content"):
            return
        self._content.clear_widgets()

        has_anything = bool(next_unit or recent)

        if not has_anything:
            # ── Empty state (new user) ─────────────────────────────────────
            self._content.add_widget(Label(
                text="Welcome to StudyBuddy!",
                font_size="18sp",
                bold=True,
                halign="center",
                size_hint=(1, None),
                height=40,
            ))
            self._content.add_widget(Label(
                text=(
                    'Tap "Browse All Subjects" below to pick your first unit.\n'
                    "Your progress will appear here once you start."
                ),
                font_size="14sp",
                halign="center",
                size_hint=(1, None),
                height=60,
            ))
            start_btn = Button(
                text="Start exploring →",
                font_size="15sp",
                size_hint=(1, None),
                height=52,
            )
            start_btn.bind(on_press=lambda *_: self._go("curriculum_map"))
            self._content.add_widget(start_btn)
            return

        # ── Continue card ──────────────────────────────────────────────────
        if next_unit:
            self._content.add_widget(self._section_header("Continue where you left off"))
            card = self._make_continue_card(next_unit)
            self._content.add_widget(card)

        # ── Recently viewed ────────────────────────────────────────────────
        recents = [r for r in recent if r.get("type") in ("lesson", "quiz")][:3]
        if recents:
            self._content.add_widget(self._section_header("Recently viewed"))
            for item in recents:
                self._content.add_widget(self._make_recent_card(item))

    def _section_header(self, text: str) -> Label:
        lbl = Label(
            text=text,
            font_size="15sp",
            bold=True,
            halign="left",
            size_hint=(1, None),
            height=32,
            color=(0.35, 0.35, 0.35, 1),
        )
        lbl.bind(
            width=lambda *_: setattr(lbl, "text_size", (lbl.width, None))
        )
        return lbl

    def _make_continue_card(self, unit: dict) -> BoxLayout:
        """Build the primary "Continue" card for the last-viewed unit."""
        card = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=96,
            padding=(12, 8),
            spacing=4,
        )

        subject = unit.get("subject", "")
        grade = unit.get("grade", "")
        title = unit.get("title", unit.get("unit_id", ""))
        score = unit.get("last_score")

        grade_subject = f"Grade {grade} · {subject}" if grade else subject
        card.add_widget(Label(
            text=grade_subject,
            font_size="12sp",
            color=(0.55, 0.55, 0.55, 1),
            halign="left",
            size_hint=(1, None),
            height=20,
        ))
        card.add_widget(Label(
            text=title,
            font_size="15sp",
            bold=True,
            halign="left",
            size_hint=(1, None),
            height=28,
        ))

        bottom_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=36, spacing=8)
        score_text = f"Last score: {score}%" if score is not None else "Start now"
        bottom_row.add_widget(Label(
            text=score_text,
            font_size="13sp",
            halign="left",
            size_hint=(0.6, 1),
        ))
        continue_btn = Button(
            text="Continue",
            font_size="14sp",
            size_hint=(0.4, 1),
        )
        unit_id = unit.get("unit_id", "")
        curriculum_id = unit.get("curriculum_id", "")
        continue_btn.bind(on_press=lambda *_: self._go_to_subject(unit_id, curriculum_id))
        bottom_row.add_widget(continue_btn)
        card.add_widget(bottom_row)

        return card

    def _make_recent_card(self, item: dict) -> BoxLayout:
        """Build a compact card for a recently-viewed unit."""
        card = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=52,
            spacing=8,
            padding=(8, 4),
        )
        title = item.get("title", item.get("unit_id", ""))
        score = item.get("score")
        score_str = f"  {score}%" if score is not None else ""

        card.add_widget(Label(
            text=f"{title}{score_str}",
            font_size="13sp",
            halign="left",
            size_hint=(0.7, 1),
        ))
        view_btn = Button(text="Review", font_size="12sp", size_hint=(0.3, 1))
        uid = item.get("unit_id", "")
        cid = item.get("curriculum_id", "")
        view_btn.bind(on_press=lambda *_: self._go_to_subject(uid, cid))
        card.add_widget(view_btn)
        return card

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go(self, screen_name: str) -> None:
        if KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            if self.manager.has_screen(screen_name):
                self.manager.current = screen_name

    def _go_to_subject(self, unit_id: str, curriculum_id: str) -> None:
        if not (KIVY_AVAILABLE and hasattr(self, "manager") and self.manager):
            return
        mgr = self.manager
        if mgr.has_screen("subject"):
            try:
                s = mgr.get_screen("subject")
                # SubjectScreen takes token, unit_id, curriculum_id as constructor args.
                # Re-entry is handled by updating instance attributes directly.
                s._token = self._token
                s._unit_id = unit_id
                s._curriculum_id = curriculum_id
            except Exception:
                pass
        if mgr.has_screen("subject"):
            mgr.current = "subject"

    # ── Error state ───────────────────────────────────────────────────────────

    @mainthread
    def _show_error(self, message: str) -> None:
        if hasattr(self, "_content"):
            self._content.clear_widgets()
            self._content.add_widget(Label(
                text=message,
                font_size="14sp",
                color=(0.8, 0.3, 0.2, 1),
                halign="center",
                size_hint=(1, None),
                height=40,
            ))
