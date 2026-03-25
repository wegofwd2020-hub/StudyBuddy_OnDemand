"""
mobile/src/ui/CurriculumMapScreen.py

Curriculum map screen — shows all units with coloured status badges.

Status colours:
  completed   → green
  needs_retry → amber
  in_progress → blue
  not_started → grey

Tapping a unit navigates to the lesson/quiz for that unit.
Data fetched from GET /student/progress.
"""

from __future__ import annotations

from threading import Thread

from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

_STATUS_COLORS = {
    "completed":   (0.18, 0.65, 0.27, 1),
    "needs_retry": (0.90, 0.65, 0.10, 1),
    "in_progress": (0.17, 0.49, 0.82, 1),
    "not_started": (0.55, 0.55, 0.55, 1),
}


class CurriculumMapScreen(Screen):
    """
    Full curriculum map with per-unit status badges.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._token: str = ""

        root = BoxLayout(orientation="vertical", padding=16, spacing=12)
        self.add_widget(root)

        # Header
        header_row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=44)
        back_btn = Button(text="← Back", size_hint=(None, 1), width=80)
        back_btn.bind(on_press=lambda *_: self._go("progress_dashboard"))
        header_row.add_widget(back_btn)
        header_row.add_widget(Label(text="Curriculum Map", font_size="18sp", bold=True))
        root.add_widget(header_row)

        self._status_label = Label(text="Loading…", font_size="14sp", size_hint=(1, None), height=30)
        root.add_widget(self._status_label)

        # Scrollable content
        scroll = ScrollView(size_hint=(1, 1))
        self._content = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        scroll.add_widget(self._content)
        root.add_widget(scroll)

    def on_enter(self) -> None:
        self._load_data()

    def set_token(self, token: str) -> None:
        self._token = token

    def _load_data(self) -> None:
        Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self) -> None:
        import asyncio
        from mobile.src.api.progress_client import get_progress_map  # type: ignore

        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_progress_map(self._token))
            loop.close()
            self._render(data)
        except Exception as exc:
            self._show_error(str(exc))

    @mainthread
    def _render(self, data: dict) -> None:
        self._status_label.text = ""
        self._content.clear_widgets()

        pending = data.get("pending_count", 0)
        needs_retry = data.get("needs_retry_count", 0)
        self._content.add_widget(Label(
            text=f"Pending: {pending}  |  Needs retry: {needs_retry}",
            font_size="13sp",
            size_hint=(1, None),
            height=26,
        ))

        for subject_data in data.get("subjects", []):
            subj = subject_data.get("subject", "")
            completed = subject_data.get("units_completed", 0)
            total = subject_data.get("units_total", 0)

            # Subject heading
            self._content.add_widget(Label(
                text=f"{subj}  ({completed}/{total})",
                font_size="16sp",
                bold=True,
                size_hint=(1, None),
                height=34,
            ))

            for unit in subject_data.get("units", []):
                status = unit.get("status", "not_started")
                color = _STATUS_COLORS.get(status, (0.55, 0.55, 0.55, 1))
                attempts = unit.get("attempts", 0)
                best = unit.get("best_score")
                score_str = f"  Best: {best}" if best is not None else ""
                label_text = f"{unit.get('title', unit['unit_id'])}  [{status.replace('_', ' ')}]{score_str}  (attempts: {attempts})"

                btn = Button(
                    text=label_text,
                    background_color=(*color[:3], 0.25),
                    color=(0, 0, 0, 1),
                    font_size="13sp",
                    size_hint=(1, None),
                    height=40,
                    halign="left",
                    text_size=(None, None),
                )
                unit_id = unit["unit_id"]
                btn.bind(on_press=lambda *_, uid=unit_id: self._open_unit(uid))
                self._content.add_widget(btn)

    @mainthread
    def _show_error(self, message: str) -> None:
        self._status_label.text = f"Error: {message}"

    def _open_unit(self, unit_id: str) -> None:
        """Navigate to the lesson/quiz for the selected unit."""
        if self.manager and self.manager.has_screen("lesson"):
            self.manager.get_screen("lesson").load_unit(unit_id)
            self.manager.current = "lesson"

    def _go(self, screen_name: str) -> None:
        if self.manager and self.manager.has_screen(screen_name):
            self.manager.current = screen_name
