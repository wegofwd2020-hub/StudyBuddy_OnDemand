"""
mobile/src/ui/StatsScreen.py

Usage statistics screen.

Displays:
  - Period picker (7d / 30d / All time)
  - Summary stat cards (quizzes, score, time, streak)
  - Day-by-day activity list

Data fetched from GET /student/stats?period=...
"""

from __future__ import annotations

from threading import Thread

from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

_PERIODS = ["7d", "30d", "all"]
_PERIOD_LABELS = {"7d": "7 Days", "30d": "30 Days", "all": "All Time"}


class StatsScreen(Screen):
    """
    Usage statistics screen with period picker and daily activity breakdown.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._token: str = ""
        self._current_period: str = "30d"

        root = BoxLayout(orientation="vertical", padding=16, spacing=12)
        self.add_widget(root)

        # Header
        header_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=44)
        back_btn = Button(text="← Back", size_hint=(None, 1), width=80)
        back_btn.bind(on_press=lambda *_: self._go("progress_dashboard"))
        header_row.add_widget(back_btn)
        header_row.add_widget(Label(text="My Stats", font_size="18sp", bold=True))
        root.add_widget(header_row)

        # Period picker
        period_row = BoxLayout(orientation="horizontal", spacing=6, size_hint=(1, None), height=40)
        self._period_buttons: dict[str, Button] = {}
        for p in _PERIODS:
            btn = Button(text=_PERIOD_LABELS[p], size_hint=(1, 1))
            btn.bind(on_press=lambda *_, period=p: self._select_period(period))
            period_row.add_widget(btn)
            self._period_buttons[p] = btn
        root.add_widget(period_row)
        self._highlight_period("30d")

        self._status_label = Label(text="Loading…", font_size="14sp", size_hint=(1, None), height=30)
        root.add_widget(self._status_label)

        # Scrollable content
        scroll = ScrollView(size_hint=(1, 1))
        self._content = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        scroll.add_widget(self._content)
        root.add_widget(scroll)

    def on_enter(self) -> None:
        self._load_data()

    def set_token(self, token: str) -> None:
        self._token = token

    def _select_period(self, period: str) -> None:
        self._current_period = period
        self._highlight_period(period)
        self._load_data()

    def _highlight_period(self, period: str) -> None:
        for p, btn in self._period_buttons.items():
            btn.background_color = (0.2, 0.5, 0.85, 1) if p == period else (0.35, 0.35, 0.35, 1)

    def _load_data(self) -> None:
        self._status_label.text = "Loading…"
        Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self) -> None:
        import asyncio
        from mobile.src.api.progress_client import get_stats  # type: ignore

        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_stats(self._token, period=self._current_period))
            loop.close()
            self._render(data)
        except Exception as exc:
            self._show_error(str(exc))

    @mainthread
    def _render(self, data: dict) -> None:
        self._status_label.text = ""
        self._content.clear_widgets()

        # ── Stat cards ────────────────────────────────────────────────────────
        cards = [
            ("Lessons Viewed",   data.get("lessons_viewed", 0)),
            ("Quizzes Done",     data.get("quizzes_completed", 0)),
            ("Quizzes Passed",   data.get("quizzes_passed", 0)),
            ("Avg Score",        f"{data.get('avg_quiz_score', 0):.0f}%"),
            ("Time Spent",       f"{data.get('total_time_minutes', 0)} min"),
            ("Audio Plays",      data.get("audio_plays", 0)),
            ("Current Streak",   f"{data.get('streak_current_days', 0)} days"),
            ("Longest Streak",   f"{data.get('streak_longest_days', 0)} days"),
        ]

        row: BoxLayout | None = None
        for i, (label, value) in enumerate(cards):
            if i % 2 == 0:
                row = BoxLayout(orientation="horizontal", spacing=8, size_hint=(1, None), height=56)
                self._content.add_widget(row)
            card = BoxLayout(orientation="vertical", size_hint=(0.5, 1), padding=4)
            card.add_widget(Label(text=str(value), font_size="20sp", bold=True, size_hint=(1, 0.6)))
            card.add_widget(Label(text=label, font_size="11sp", color=(0.6, 0.6, 0.6, 1), size_hint=(1, 0.4)))
            if row is not None:
                row.add_widget(card)

        # ── Daily activity ────────────────────────────────────────────────────
        daily = data.get("daily_activity", [])
        if daily:
            self._content.add_widget(Label(
                text="Daily Activity",
                font_size="16sp",
                bold=True,
                size_hint=(1, None),
                height=32,
            ))
            for day_data in daily[:30]:
                self._content.add_widget(Label(
                    text=(
                        f"{day_data['date']}  "
                        f"Lessons: {day_data['lessons']}  "
                        f"Quizzes: {day_data['quizzes']}  "
                        f"Time: {day_data['minutes']} min"
                    ),
                    font_size="12sp",
                    size_hint=(1, None),
                    height=24,
                    halign="left",
                ))

    @mainthread
    def _show_error(self, message: str) -> None:
        self._status_label.text = f"Error: {message}"

    def _go(self, screen_name: str) -> None:
        if self.manager and self.manager.has_screen(screen_name):
            self.manager.current = screen_name
