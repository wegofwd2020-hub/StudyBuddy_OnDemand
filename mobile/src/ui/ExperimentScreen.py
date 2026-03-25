"""
mobile/src/ui/ExperimentScreen.py

Step-by-step lab experiment screen for lab-bearing units.

Flow:
  1. SubjectScreen fetches experiment JSON and caches it.
  2. SubjectScreen navigates here, passing the cached experiment data.
  3. This screen renders: title, materials, safety notes, numbered steps,
     reflection questions, and a conclusion prompt.
  4. "Back to Lesson" returns to SubjectScreen.

Layer rule: UI screens only import from logic/ and api/ layers.
"""

from __future__ import annotations

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):
        return logging.getLogger(name)

log = get_logger("experiment_screen")

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.uix.scrollview import ScrollView  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    _KIVY_AVAILABLE = True
except ImportError:
    _KIVY_AVAILABLE = False

    class Screen:  # type: ignore
        name: str = ""
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "")
        def add_widget(self, widget):
            pass


class ExperimentScreen(Screen):
    """
    Guided lab experiment screen.

    Receives experiment data dict from SubjectScreen (already fetched and cached).
    Never makes network calls itself — data is passed in at construction.
    """

    def __init__(self, experiment_data: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.name = "experiment"
        self._data: dict = experiment_data or {}

        if _KIVY_AVAILABLE:
            self._build_ui()

    def set_experiment(self, data: dict) -> None:
        """Update the screen with new experiment data (called before navigation)."""
        self._data = data
        if _KIVY_AVAILABLE:
            self._refresh_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = ScrollView()
        self._root = BoxLayout(
            orientation="vertical", padding=24, spacing=14, size_hint_y=None
        )
        self._root.bind(minimum_height=self._root.setter("height"))

        # Title
        self._title_label = Label(
            text=self._data.get("experiment_title", "Lab Experiment"),
            font_size=22,
            bold=True,
            size_hint_y=None,
            height=52,
            halign="center",
        )
        self._root.add_widget(self._title_label)

        # Content area — populated by _refresh_ui
        self._content_box = BoxLayout(
            orientation="vertical", spacing=10, size_hint_y=None
        )
        self._content_box.bind(minimum_height=self._content_box.setter("height"))
        self._root.add_widget(self._content_box)

        # Back button
        back_btn = Button(
            text="← Back to Lesson",
            size_hint_y=None,
            height=48,
            background_color=(0.4, 0.4, 0.4, 1),
        )
        back_btn.bind(on_release=self._on_back)
        self._root.add_widget(back_btn)

        scroll.add_widget(self._root)
        self.add_widget(scroll)

        if self._data:
            self._refresh_ui()

    @mainthread
    def _refresh_ui(self) -> None:
        """Populate or repopulate the content area from self._data."""
        if not hasattr(self, "_content_box"):
            return

        self._content_box.clear_widgets()

        if hasattr(self, "_title_label"):
            self._title_label.text = self._data.get("experiment_title", "Lab Experiment")

        # ── Materials ─────────────────────────────────────────────────────────
        materials = self._data.get("materials", [])
        if materials:
            self._content_box.add_widget(self._section_header("🧪 Materials"))
            for item in materials:
                self._content_box.add_widget(self._bullet_label(f"• {item}"))

        # ── Safety notes ──────────────────────────────────────────────────────
        safety = self._data.get("safety_notes", [])
        if safety:
            self._content_box.add_widget(self._section_header("⚠️ Safety Notes"))
            for note in safety:
                self._content_box.add_widget(self._bullet_label(f"• {note}"))

        # ── Steps ─────────────────────────────────────────────────────────────
        steps = self._data.get("steps", [])
        if steps:
            self._content_box.add_widget(self._section_header("📋 Procedure"))
            for step in steps:
                num = step.get("step_number", "")
                instruction = step.get("instruction", "")
                observation = step.get("expected_observation", "")
                self._content_box.add_widget(
                    self._step_label(f"Step {num}: {instruction}", observation)
                )

        # ── Reflection questions ──────────────────────────────────────────────
        questions = self._data.get("questions", [])
        if questions:
            self._content_box.add_widget(self._section_header("🤔 Reflection Questions"))
            for i, q in enumerate(questions, 1):
                self._content_box.add_widget(
                    self._bullet_label(f"Q{i}: {q.get('question', '')}")
                )

        # ── Conclusion prompt ─────────────────────────────────────────────────
        conclusion = self._data.get("conclusion_prompt", "")
        if conclusion:
            self._content_box.add_widget(self._section_header("✏️ Write Your Conclusion"))
            self._content_box.add_widget(self._body_label(conclusion))

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _section_header(self, text: str) -> "Label":
        lbl = Label(
            text=text,
            font_size=17,
            bold=True,
            size_hint_y=None,
            height=36,
            halign="left",
        )
        lbl.bind(width=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
        return lbl

    def _body_label(self, text: str) -> "Label":
        lbl = Label(
            text=text,
            font_size=14,
            size_hint_y=None,
            halign="left",
        )
        lbl.bind(
            width=lambda *_: setattr(lbl, "text_size", (lbl.width, None)),
            texture_size=lambda *_: setattr(lbl, "height", lbl.texture_size[1] + 8),
        )
        return lbl

    def _bullet_label(self, text: str) -> "Label":
        lbl = Label(
            text=text,
            font_size=14,
            size_hint_y=None,
            halign="left",
        )
        lbl.bind(
            width=lambda *_: setattr(lbl, "text_size", (lbl.width, None)),
            texture_size=lambda *_: setattr(lbl, "height", lbl.texture_size[1] + 4),
        )
        return lbl

    def _step_label(self, instruction: str, observation: str) -> "BoxLayout":
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=2, padding=[12, 0, 0, 8])
        box.bind(minimum_height=box.setter("height"))
        box.add_widget(self._bullet_label(instruction))
        if observation:
            obs_lbl = self._bullet_label(f"  → Expected: {observation}")
            box.add_widget(obs_lbl)
        return box

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_back(self, *_) -> None:
        if _KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            try:
                self.manager.current = self.manager.previous()
            except Exception:
                self.manager.current = "subject"
