"""
mobile/src/ui/TutorialScreen.py

Tutorial screen — post-quiz recovery path (#74).

Shows a multi-section tutorial for a unit. Students who fail a quiz are
directed here to review the material before retrying.

Content structure (tutorial JSON):
  {
    "title": "...",
    "sections": [
      {"title": "...", "body": "..."},   ← markdown body
      ...
    ],
    "content_version": 1
  }

Markdown rendering: bold (**text**) and bullet lists (- item) are
converted to plain text with visual cues suitable for Kivy Labels.

Entry points:
  - ResultScreen → "Review Tutorial" button (primary — after a failed quiz)
  - SubjectScreen → "📚 Tutorial" button (direct access)

Navigation model:
  - Tab strip at top (one button per section)
  - Section body in a ScrollView
  - Prev / Next buttons at bottom
  - "Take Quiz Again" shown on the last section

Offline: LocalCache first, then GET /content/{unit_id}/tutorial.
         "Tutorial not downloaded" shown if both unavailable.

Layer rule: ui layer only. All API calls in daemon threads. @mainthread
on all UI mutations.
"""

from __future__ import annotations

import threading

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

log = get_logger("tutorial_screen")


def _render_markdown(text: str) -> str:
    """
    Convert a small markdown subset to Kivy-friendly plain text.

    Supported:
      **bold** → ALL CAPS (Kivy Labels have no rich text by default)
      - item   → • item
      Blank lines between paragraphs are preserved.
    """
    import re
    # Bold → uppercase (visual emphasis without markup)
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: m.group(1).upper(), text)
    # Bullet list items
    text = re.sub(r"(?m)^[-*]\s+", "• ", text)
    return text.strip()


class TutorialScreen(Screen):
    """
    Multi-section tutorial viewer with prev/next navigation.

    Usage:
        tutorial_screen.set_context(token, unit_id, curriculum_id, lang)
        screen_manager.current = "tutorial"
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._token: str = ""
        self._unit_id: str = ""
        self._curriculum_id: str = ""
        self._lang: str = "en"

        self._sections: list[dict] = []
        self._current_section: int = 0
        self._tab_buttons: list[Button] = []

        if KIVY_AVAILABLE:
            self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_context(
        self,
        token: str,
        unit_id: str,
        curriculum_id: str,
        lang: str = "en",
    ) -> None:
        """Set context before navigating to this screen."""
        self._token = token
        self._unit_id = unit_id
        self._curriculum_id = curriculum_id
        self._lang = lang

    # ── Kivy lifecycle ────────────────────────────────────────────────────────

    def on_enter(self, *_) -> None:
        self._sections = []
        self._current_section = 0
        self._set_loading()
        threading.Thread(target=self._load_tutorial, daemon=True).start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=16, spacing=8)

        # Unit title / loading header
        self._title_label = Label(
            text="Loading tutorial…",
            font_size="18sp",
            bold=True,
            size_hint=(1, None),
            height=44,
            halign="left",
        )
        self._title_label.bind(
            width=lambda *_: setattr(
                self._title_label, "text_size", (self._title_label.width, None)
            )
        )
        root.add_widget(self._title_label)

        # Tab strip (one button per section, built dynamically)
        self._tab_strip = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=40,
            spacing=4,
        )
        root.add_widget(self._tab_strip)

        # Section body in a scroll view
        scroll = ScrollView(size_hint=(1, 1))
        self._body_label = Label(
            text="",
            font_size="15sp",
            halign="left",
            valign="top",
            size_hint_y=None,
        )
        self._body_label.bind(
            width=lambda *_: setattr(
                self._body_label, "text_size", (self._body_label.width, None)
            ),
            texture_size=lambda *_: setattr(
                self._body_label, "height", self._body_label.texture_size[1]
            ),
        )
        scroll.add_widget(self._body_label)
        root.add_widget(scroll)

        # Navigation row
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=48, spacing=8)

        self._prev_btn = Button(text="← Previous", size_hint=(0.33, 1), disabled=True)
        self._prev_btn.bind(on_press=self._on_prev)
        nav.add_widget(self._prev_btn)

        self._section_counter = Label(
            text="",
            font_size="13sp",
            halign="center",
            size_hint=(0.34, 1),
        )
        nav.add_widget(self._section_counter)

        self._next_btn = Button(text="Next →", size_hint=(0.33, 1), disabled=True)
        self._next_btn.bind(on_press=self._on_next)
        nav.add_widget(self._next_btn)

        root.add_widget(nav)

        # "Take Quiz Again" — shown only on last section
        self._retry_btn = Button(
            text="Take Quiz Again",
            font_size="15sp",
            size_hint=(1, None),
            height=50,
            opacity=0,
            disabled=True,
        )
        self._retry_btn.bind(on_press=self._on_take_quiz_again)
        root.add_widget(self._retry_btn)

        # Status (offline / error)
        self._status_label = Label(
            text="",
            font_size="13sp",
            color=(0.8, 0.3, 0.2, 1),
            size_hint=(1, None),
            height=28,
            halign="center",
        )
        root.add_widget(self._status_label)

        self.add_widget(root)

    # ── Load tutorial content ─────────────────────────────────────────────────

    def _load_tutorial(self) -> None:
        """Daemon thread: cache → API fallback."""
        # Try LocalCache first
        try:
            from mobile.src.logic.LocalCache import LocalCache  # type: ignore
            cached = LocalCache().get(
                self._unit_id, self._curriculum_id, "tutorial", self._lang, 1
            )
            if cached is not None:
                log.info("tutorial_cache_hit unit_id=%s", self._unit_id)
                self._populate(cached)
                return
        except Exception as exc:
            log.warning("tutorial_cache_read_failed error=%s", exc)

        # Fetch from backend
        try:
            import asyncio
            from mobile.src.api.content_client import get_tutorial  # type: ignore
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_tutorial(self._unit_id, self._token))
            loop.close()

            try:
                from mobile.src.logic.LocalCache import LocalCache  # type: ignore
                LocalCache().put(
                    self._unit_id, self._curriculum_id, "tutorial", self._lang,
                    data.get("content_version", 1), data,
                )
            except Exception as exc:
                log.warning("tutorial_cache_write_failed error=%s", exc)

            log.info("tutorial_fetched unit_id=%s sections=%d",
                     self._unit_id, len(data.get("sections", [])))
            self._populate(data)

        except Exception as exc:
            log.warning("tutorial_fetch_failed unit_id=%s error=%s", self._unit_id, exc)
            self._show_offline()

    # ── Populate and render ───────────────────────────────────────────────────

    def _populate(self, data: dict) -> None:
        """Store sections and render the first one."""
        sections = data.get("sections", [])
        if not sections:
            self._show_error("No tutorial content available for this unit.")
            return
        self._sections = sections
        self._current_section = 0
        self._build_tabs(len(sections))
        self._render_section(0, data.get("title", "Tutorial"))

    @mainthread
    def _set_loading(self) -> None:
        if hasattr(self, "_title_label"):
            self._title_label.text = "Loading tutorial…"
        if hasattr(self, "_body_label"):
            self._body_label.text = ""
        if hasattr(self, "_status_label"):
            self._status_label.text = ""
        if hasattr(self, "_retry_btn"):
            self._retry_btn.opacity = 0
            self._retry_btn.disabled = True

    @mainthread
    def _build_tabs(self, n: int) -> None:
        """Rebuild the tab strip for n sections."""
        if not hasattr(self, "_tab_strip"):
            return
        self._tab_strip.clear_widgets()
        self._tab_buttons = []
        for i in range(n):
            btn = Button(
                text=str(i + 1),
                font_size="13sp",
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _b, idx=i: self._on_tab(idx))
            self._tab_strip.add_widget(btn)
            self._tab_buttons.append(btn)

    @mainthread
    def _render_section(self, idx: int, tutorial_title: str = "") -> None:
        """Render section at idx."""
        if not self._sections:
            return

        total = len(self._sections)
        section = self._sections[idx]

        if hasattr(self, "_title_label"):
            self._title_label.text = section.get("title", tutorial_title or "Tutorial")

        if hasattr(self, "_body_label"):
            self._body_label.text = _render_markdown(section.get("body", ""))

        if hasattr(self, "_section_counter"):
            self._section_counter.text = f"{idx + 1} / {total}"

        if hasattr(self, "_prev_btn"):
            self._prev_btn.disabled = idx == 0

        if hasattr(self, "_next_btn"):
            self._next_btn.disabled = idx == total - 1

        # Highlight active tab
        for i, btn in enumerate(self._tab_buttons):
            btn.background_color = (0.25, 0.55, 0.95, 1) if i == idx else (1, 1, 1, 1)
            btn.color = (1, 1, 1, 1) if i == idx else (0, 0, 0, 1)

        # Show "Take Quiz Again" on last section
        if hasattr(self, "_retry_btn"):
            last = idx == total - 1
            self._retry_btn.opacity = 1 if last else 0
            self._retry_btn.disabled = not last

        if hasattr(self, "_status_label"):
            self._status_label.text = ""

        self._current_section = idx

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_tab(self, idx: int) -> None:
        title = ""
        if KIVY_AVAILABLE and hasattr(self, "_title_label"):
            title = self._title_label.text
        self._render_section(idx, title)

    def _on_prev(self, *_) -> None:
        if self._current_section > 0:
            self._render_section(self._current_section - 1)

    def _on_next(self, *_) -> None:
        if self._sections and self._current_section < len(self._sections) - 1:
            self._render_section(self._current_section + 1)

    def _on_take_quiz_again(self, *_) -> None:
        if KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            if self.manager.has_screen("quiz"):
                self.manager.current = "quiz"

    # ── Error / offline states ────────────────────────────────────────────────

    @mainthread
    def _show_offline(self) -> None:
        if hasattr(self, "_title_label"):
            self._title_label.text = "Tutorial not downloaded yet"
        if hasattr(self, "_body_label"):
            self._body_label.text = ""
        if hasattr(self, "_status_label"):
            self._status_label.text = (
                "Connect to the internet to download this tutorial, "
                "then come back."
            )
        log.info("tutorial_offline_shown unit_id=%s", self._unit_id)

    @mainthread
    def _show_error(self, message: str) -> None:
        if hasattr(self, "_title_label"):
            self._title_label.text = "Tutorial unavailable"
        if hasattr(self, "_status_label"):
            self._status_label.text = message
        log.warning("tutorial_error unit_id=%s message=%s", self._unit_id, message)
