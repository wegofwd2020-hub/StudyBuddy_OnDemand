"""
mobile/src/ui/ResultScreen.py

Result screen shown after a quiz session ends.

Displays the backend-confirmed score returned by POST /progress/session/{id}/end.
Never computes the score client-side — the backend value is authoritative.

Data passed in via `result_data` dict:
  {session_id, score, total_questions, passed, attempt_number, ended_at}
"""

from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import mainthread


class ResultScreen(Screen):
    """
    Quiz result screen.

    Expected usage:
        screen = ResultScreen(name="result")
        screen.populate(result_data)
        screen_manager.add_widget(screen)
        screen_manager.current = "result"
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._layout = BoxLayout(orientation="vertical", padding=32, spacing=20)
        self.add_widget(self._layout)

    @mainthread
    def populate(self, result_data: dict) -> None:
        """
        Populate the screen with the backend-confirmed result.

        Called from a daemon thread via @mainthread to update the UI safely.
        """
        self._layout.clear_widgets()

        score = result_data.get("score", 0)
        total = result_data.get("total_questions", 0)
        passed = result_data.get("passed", False)
        attempt = result_data.get("attempt_number", 1)
        pct = round(score / total * 100) if total > 0 else 0

        # ── Heading ───────────────────────────────────────────────────────────
        heading = "Great job! You passed! 🎉" if passed else "Keep practising!"
        self._layout.add_widget(Label(
            text=heading,
            font_size="22sp",
            bold=True,
            halign="center",
            size_hint=(1, None),
            height=48,
        ))

        # ── Score ─────────────────────────────────────────────────────────────
        self._layout.add_widget(Label(
            text=f"{score} / {total}  ({pct}%)",
            font_size="36sp",
            halign="center",
            size_hint=(1, None),
            height=60,
        ))

        # ── Attempt number ────────────────────────────────────────────────────
        if attempt > 1:
            self._layout.add_widget(Label(
                text=f"Attempt {attempt}",
                font_size="14sp",
                color=(0.6, 0.6, 0.6, 1),
                halign="center",
                size_hint=(1, None),
                height=28,
            ))

        # ── Pass/fail indicator ───────────────────────────────────────────────
        status_color = (0.2, 0.7, 0.3, 1) if passed else (0.85, 0.3, 0.2, 1)
        status_text = "PASSED" if passed else "NOT PASSED"
        self._layout.add_widget(Label(
            text=status_text,
            font_size="18sp",
            color=status_color,
            bold=True,
            halign="center",
            size_hint=(1, None),
            height=36,
        ))

        # ── Navigation buttons ────────────────────────────────────────────────
        btn_row = BoxLayout(orientation="horizontal", spacing=12, size_hint=(1, None), height=48)

        retry_btn = Button(text="Try Again", size_hint=(0.5, 1))
        retry_btn.bind(on_press=self._on_retry)
        btn_row.add_widget(retry_btn)

        next_btn = Button(text="Next Unit", size_hint=(0.5, 1))
        next_btn.bind(on_press=self._on_next)
        btn_row.add_widget(next_btn)

        self._layout.add_widget(btn_row)

        home_btn = Button(text="My Progress", size_hint=(1, None), height=44)
        home_btn.bind(on_press=self._on_progress)
        self._layout.add_widget(home_btn)

        self._result_data = result_data

    def _on_retry(self, *_) -> None:
        if self.manager and self.manager.has_screen("quiz"):
            self.manager.current = "quiz"

    def _on_next(self, *_) -> None:
        if self.manager and self.manager.has_screen("curriculum_map"):
            self.manager.current = "curriculum_map"

    def _on_progress(self, *_) -> None:
        if self.manager and self.manager.has_screen("progress_dashboard"):
            self.manager.current = "progress_dashboard"
