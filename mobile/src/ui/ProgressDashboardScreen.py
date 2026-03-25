"""
mobile/src/ui/ProgressDashboardScreen.py

Progress dashboard screen — the first screen a student sees after login.

Displays:
  - Streak badge (current_streak_days)
  - Subject completion rings (subject_progress)
  - Next Unit card
  - Recent activity list

Data is fetched from GET /student/dashboard in a daemon thread.
All UI updates go through @mainthread.
"""

from __future__ import annotations

from threading import Thread

from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView


class ProgressDashboardScreen(Screen):
    """
    Dashboard screen showing streak, subject progress, next unit, and recent activity.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._token: str = ""

        root = BoxLayout(orientation="vertical", padding=16, spacing=12)
        self.add_widget(root)

        # Header
        root.add_widget(Label(
            text="My Progress",
            font_size="20sp",
            bold=True,
            size_hint=(1, None),
            height=44,
        ))

        # Loading label (replaced on data load)
        self._status_label = Label(text="Loading…", font_size="14sp", size_hint=(1, None), height=30)
        root.add_widget(self._status_label)

        # Scrollable content area
        scroll = ScrollView(size_hint=(1, 1))
        self._content = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        scroll.add_widget(self._content)
        root.add_widget(scroll)

        # Navigation row
        nav = BoxLayout(orientation="horizontal", spacing=8, size_hint=(1, None), height=44)
        map_btn = Button(text="Curriculum Map")
        map_btn.bind(on_press=lambda *_: self._go("curriculum_map"))
        stats_btn = Button(text="Stats")
        stats_btn.bind(on_press=lambda *_: self._go("stats"))
        nav.add_widget(map_btn)
        nav.add_widget(stats_btn)
        root.add_widget(nav)

        self._root_layout = root

    def on_enter(self) -> None:
        """Called by ScreenManager when this screen becomes active."""
        self._load_data()

    def set_token(self, token: str) -> None:
        self._token = token

    def _load_data(self) -> None:
        Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self) -> None:
        import asyncio
        from mobile.src.api.progress_client import get_dashboard  # type: ignore

        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_dashboard(self._token))
            loop.close()
            self._render(data)
        except Exception as exc:
            self._show_error(str(exc))

    @mainthread
    def _render(self, data: dict) -> None:
        self._status_label.text = ""
        self._content.clear_widgets()

        summary = data.get("summary", {})

        # ── Streak badge ──────────────────────────────────────────────────────
        streak = summary.get("current_streak_days", 0)
        self._content.add_widget(Label(
            text=f"🔥 {streak}-day streak",
            font_size="18sp",
            bold=True,
            size_hint=(1, None),
            height=40,
        ))

        # ── Summary stats ─────────────────────────────────────────────────────
        self._content.add_widget(Label(
            text=(
                f"Units completed: {summary.get('units_completed', 0)}  |  "
                f"Quizzes passed: {summary.get('quizzes_passed', 0)}  |  "
                f"Avg score: {summary.get('avg_quiz_score', 0):.0f}%  |  "
                f"Time: {summary.get('total_time_minutes', 0)} min"
            ),
            font_size="13sp",
            halign="center",
            size_hint=(1, None),
            height=30,
        ))

        # ── Subject progress ──────────────────────────────────────────────────
        self._content.add_widget(Label(text="Subjects", font_size="16sp", bold=True, size_hint=(1, None), height=32))
        for sp in data.get("subject_progress", []):
            self._content.add_widget(Label(
                text=f"{sp['subject']}: {sp['units_completed']}/{sp['units_total']} ({sp['pct']:.0f}%)",
                font_size="13sp",
                size_hint=(1, None),
                height=26,
            ))

        # ── Next unit ─────────────────────────────────────────────────────────
        next_unit = data.get("next_unit")
        if next_unit:
            self._content.add_widget(Label(text="Up Next", font_size="16sp", bold=True, size_hint=(1, None), height=32))
            next_btn = Button(
                text=f"{next_unit['title']} ({next_unit['subject']})",
                size_hint=(1, None),
                height=44,
            )
            next_btn.bind(on_press=lambda *_: self._go("curriculum_map"))
            self._content.add_widget(next_btn)

        # ── Recent activity ────────────────────────────────────────────────────
        recent = data.get("recent_activity", [])
        if recent:
            self._content.add_widget(Label(text="Recent Activity", font_size="16sp", bold=True, size_hint=(1, None), height=32))
            for item in recent[:5]:
                score_str = f" — {item['score']}%" if item.get("score") is not None else ""
                self._content.add_widget(Label(
                    text=f"[{item['type'].upper()}] {item.get('title', item['unit_id'])}{score_str}",
                    font_size="12sp",
                    size_hint=(1, None),
                    height=24,
                ))

    @mainthread
    def _show_error(self, message: str) -> None:
        self._status_label.text = f"Error: {message}"

    def _go(self, screen_name: str) -> None:
        if self.manager and self.manager.has_screen(screen_name):
            self.manager.current = screen_name
