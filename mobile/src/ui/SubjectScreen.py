"""
mobile/src/ui/SubjectScreen.py

Subject screen — displays a lesson and provides audio + experiment buttons.

Responsibilities:
  - Show lesson content (title, synopsis, key concepts, objectives).
  - "🔊 Listen" button: fetches pre-signed audio URL → downloads MP3 →
    caches to local filesystem → plays via Kivy SoundLoader.
  - Audio is cached by (unit_id, curriculum_id, lang) so offline playback
    works after the first listen.
  - "🔬 Experiment" button: probed on enter by GET /content/{unit_id}/experiment.
    Shown only when backend returns 200 (lab-bearing unit). Experiment JSON is
    cached in LocalCache. Navigates to ExperimentScreen on tap.
  - "📝 Take Quiz" button navigates to quiz screen.
  - Fires POST /analytics/lesson/start on enter; queues lesson_end event
    (via EventQueue) on leave, including experiment_viewed flag.

Layer rule: SubjectScreen is in the ui layer; calls logic/ and api/ via daemon threads.
"""

from __future__ import annotations

import os
import threading
import time

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.uix.scrollview import ScrollView  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object  # type: ignore
    KIVY_AVAILABLE = False

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):
        return logging.getLogger(name)

log = get_logger("subject_screen")

_AUDIO_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".studybuddy", "audio")


class SubjectScreen(Screen):
    """
    Lesson display screen with audio playback and quiz navigation.
    """

    def __init__(self, token: str, unit_id: str, curriculum_id: str, **kwargs):
        super().__init__(**kwargs)
        self.name = "subject"
        self._token = token
        self._unit_id = unit_id
        self._curriculum_id = curriculum_id
        self._view_id: str | None = None
        self._lesson_opened_at: float = 0.0
        self._sound = None
        self._experiment_data: dict | None = None  # set when lab is available
        self._experiment_viewed: bool = False

        if KIVY_AVAILABLE:
            self._build_ui()

    def _build_ui(self) -> None:
        scroll = ScrollView()
        root = BoxLayout(orientation="vertical", padding=24, spacing=12, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        self._title_label = Label(
            text="Loading…",
            font_size=22,
            bold=True,
            size_hint_y=None,
            height=48,
        )
        root.add_widget(self._title_label)

        self._synopsis_label = Label(
            text="",
            font_size=15,
            size_hint_y=None,
            text_size=(None, None),
            halign="left",
        )
        self._synopsis_label.bind(
            width=lambda *x: setattr(self._synopsis_label, "text_size", (self._synopsis_label.width, None)),
            texture_size=lambda *x: setattr(self._synopsis_label, "height", self._synopsis_label.texture_size[1]),
        )
        root.add_widget(self._synopsis_label)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=52, spacing=12)

        self._listen_btn = Button(text="🔊 Listen", size_hint_x=0.33)
        self._listen_btn.bind(on_release=self._on_listen)
        btn_row.add_widget(self._listen_btn)

        self._experiment_btn = Button(
            text="🔬 Experiment",
            size_hint_x=0.33,
            disabled=True,
            opacity=0,
        )
        self._experiment_btn.bind(on_release=self._on_experiment)
        btn_row.add_widget(self._experiment_btn)

        quiz_btn = Button(text="📝 Take Quiz", size_hint_x=0.34)
        quiz_btn.bind(on_release=self._on_take_quiz)
        btn_row.add_widget(quiz_btn)

        root.add_widget(btn_row)

        self._status_label = Label(text="", size_hint_y=None, height=28, font_size=13)
        root.add_widget(self._status_label)

        scroll.add_widget(root)
        self.add_widget(scroll)

    def on_enter(self, *_) -> None:
        """Called by Kivy when screen becomes active — start lesson analytics."""
        self._lesson_opened_at = time.monotonic()
        self._experiment_viewed = False
        self._start_lesson_analytics()
        self._load_lesson_async()
        self._probe_experiment_async()

    def on_leave(self, *_) -> None:
        """Called by Kivy when leaving screen — queue lesson_end event."""
        if self._view_id:
            duration_s = int(time.monotonic() - self._lesson_opened_at)
            self._queue_lesson_end(self._view_id, duration_s)
        self._stop_audio()
        self._experiment_viewed = False

    # ── Lesson analytics ──────────────────────────────────────────────────────

    def _start_lesson_analytics(self) -> None:
        def _start():
            try:
                import asyncio
                from mobile.src.api.progress_client import start_lesson_view  # type: ignore
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    start_lesson_view(self._token, self._unit_id, self._curriculum_id)
                )
                loop.close()
                self._view_id = result.get("view_id")
                log.info("lesson_view_started view_id=%s", self._view_id)
            except Exception as exc:
                log.warning("lesson_start_analytics_failed error=%s", exc)

        threading.Thread(target=_start, daemon=True).start()

    def _queue_lesson_end(self, view_id: str, duration_s: int) -> None:
        def _enqueue():
            try:
                from mobile.src.logic.EventQueue import EventQueue  # type: ignore
                q = EventQueue()
                q.enqueue("lesson_end", {
                    "view_id": view_id,
                    "duration_s": duration_s,
                    "audio_played": self._sound is not None,
                    "experiment_viewed": self._experiment_viewed,
                })
                log.info("lesson_end_queued view_id=%s duration_s=%d", view_id, duration_s)
            except Exception as exc:
                log.warning("lesson_end_queue_failed error=%s", exc)

        threading.Thread(target=_enqueue, daemon=True).start()

    # ── Lesson content ────────────────────────────────────────────────────────

    def _load_lesson_async(self) -> None:
        def _fetch():
            try:
                import asyncio
                import httpx
                try:
                    from mobile.config import BACKEND_URL  # type: ignore
                except ImportError:
                    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

                url = f"{BACKEND_URL}/api/v1/content/{self._unit_id}/lesson"
                loop = asyncio.new_event_loop()
                async def _get():
                    async with httpx.AsyncClient(timeout=15) as c:
                        r = await c.get(url, headers={"Authorization": f"Bearer {self._token}"})
                        r.raise_for_status()
                        return r.json()
                data = loop.run_until_complete(_get())
                loop.close()
                self._populate_lesson(data)
            except Exception as exc:
                log.warning("load_lesson_failed unit_id=%s error=%s", self._unit_id, exc)
                self._set_status(f"Could not load lesson: {exc}")

        threading.Thread(target=_fetch, daemon=True).start()

    @mainthread
    def _populate_lesson(self, data: dict) -> None:
        if hasattr(self, "_title_label"):
            self._title_label.text = data.get("title", self._unit_id)
        if hasattr(self, "_synopsis_label"):
            self._synopsis_label.text = data.get("synopsis", "")

    # ── Experiment probe ──────────────────────────────────────────────────────

    def _probe_experiment_async(self) -> None:
        """
        Probe experiment availability for this unit.

        Tries local cache first (content_type="experiment"). Falls back to
        GET /content/{unit_id}/experiment. Shows the button on HTTP 200,
        keeps it hidden on 404. Caches the experiment JSON locally.
        """
        threading.Thread(target=self._probe_experiment, daemon=True).start()

    def _probe_experiment(self) -> None:
        try:
            # Check local cache first
            try:
                from mobile.src.logic.LocalCache import LocalCache  # type: ignore
                cache = LocalCache()
                cached = cache.get(self._unit_id, self._curriculum_id, "experiment", "en", 1)
                if cached is not None:
                    self._experiment_data = cached
                    self._show_experiment_btn()
                    log.info("experiment_cache_hit unit_id=%s", self._unit_id)
                    return
            except Exception:
                pass

            # Fetch from backend
            import asyncio
            from mobile.src.api.content_client import get_experiment  # type: ignore
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_experiment(self._unit_id, self._token))
            loop.close()

            self._experiment_data = data

            # Cache it alongside lesson JSON
            try:
                from mobile.src.logic.LocalCache import LocalCache  # type: ignore
                content_version = data.get("content_version", 1)
                LocalCache().put(
                    self._unit_id, self._curriculum_id, "experiment", "en",
                    content_version, data
                )
            except Exception as exc:
                log.warning("experiment_cache_write_failed error=%s", exc)

            self._show_experiment_btn()
            log.info("experiment_available unit_id=%s", self._unit_id)

        except Exception as exc:
            # 404 means no lab — keep button hidden
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status != 404:
                log.warning("experiment_probe_failed unit_id=%s error=%s", self._unit_id, exc)

    @mainthread
    def _show_experiment_btn(self) -> None:
        if hasattr(self, "_experiment_btn"):
            self._experiment_btn.disabled = False
            self._experiment_btn.opacity = 1

    # ── Experiment navigation ─────────────────────────────────────────────────

    def _on_experiment(self, *_) -> None:
        """Navigate to ExperimentScreen with cached experiment data."""
        self._experiment_viewed = True
        if not (KIVY_AVAILABLE and hasattr(self, "manager") and self.manager):
            return

        # Set data on existing ExperimentScreen if present, else navigate
        mgr = self.manager
        if hasattr(mgr, "get_screen"):
            try:
                exp_screen = mgr.get_screen("experiment")
                if self._experiment_data:
                    exp_screen.set_experiment(self._experiment_data)
            except Exception:
                pass
        mgr.current = "experiment"

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _on_listen(self, *_) -> None:
        """Fetch audio URL → download → cache → play."""
        self._set_listen_btn_state("Fetching…", enabled=False)
        threading.Thread(target=self._fetch_and_play_audio, daemon=True).start()

    def _fetch_and_play_audio(self) -> None:
        try:
            # Check local cache first
            cached_path = self._audio_cache_path()
            if os.path.exists(cached_path):
                log.info("audio_cache_hit path=%s", cached_path)
                self._play_audio(cached_path)
                return

            # Fetch pre-signed URL from backend
            import asyncio
            import httpx
            try:
                from mobile.config import BACKEND_URL  # type: ignore
            except ImportError:
                BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

            url = f"{BACKEND_URL}/api/v1/content/{self._unit_id}/lesson/audio"
            loop = asyncio.new_event_loop()
            async def _get_url():
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(url, headers={"Authorization": f"Bearer {self._token}"})
                    r.raise_for_status()
                    return r.json()
            data = loop.run_until_complete(_get_url())
            loop.close()

            audio_url = data.get("url", "")
            if not audio_url:
                raise ValueError("empty audio URL from backend")

            # Download MP3 directly from CDN (never proxied through API)
            import urllib.request
            os.makedirs(os.path.dirname(cached_path), exist_ok=True)
            urllib.request.urlretrieve(audio_url, cached_path)
            log.info("audio_downloaded url=%s cached=%s", audio_url[:60], cached_path)

            self._play_audio(cached_path)

        except Exception as exc:
            log.warning("audio_fetch_failed unit_id=%s error=%s", self._unit_id, exc)
            self._set_status(f"Audio unavailable: {exc}")
            self._set_listen_btn_state("🔊 Listen", enabled=True)

    def _audio_cache_path(self) -> str:
        """Local filesystem path for the cached MP3."""
        try:
            from mobile.config import JWT_PATH  # type: ignore
            locale = "en"
        except ImportError:
            locale = "en"
        filename = f"{self._unit_id}_{self._curriculum_id}_{locale}.mp3"
        return os.path.join(_AUDIO_CACHE_DIR, filename)

    def _play_audio(self, path: str) -> None:
        """Load and play an MP3 from local filesystem."""
        self._set_listen_btn_state("▶ Playing…", enabled=False)
        if KIVY_AVAILABLE:
            from kivy.core.audio import SoundLoader  # type: ignore
            self._stop_audio()
            sound = SoundLoader.load(path)
            if sound:
                self._sound = sound
                sound.bind(on_stop=lambda *_: self._set_listen_btn_state("🔊 Listen", enabled=True))
                sound.play()
            else:
                self._set_status("Could not play audio.")
                self._set_listen_btn_state("🔊 Listen", enabled=True)
        else:
            log.info("audio_playback_skipped_no_kivy path=%s", path)
            self._set_listen_btn_state("🔊 Listen", enabled=True)

    def _stop_audio(self) -> None:
        if self._sound:
            try:
                self._sound.stop()
            except Exception:
                pass
            self._sound = None

    # ── Quiz navigation ───────────────────────────────────────────────────────

    def _on_take_quiz(self, *_) -> None:
        if KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            self.manager.current = "quiz"

    # ── UI helpers ────────────────────────────────────────────────────────────

    @mainthread
    def _set_listen_btn_state(self, text: str, enabled: bool = True) -> None:
        if hasattr(self, "_listen_btn"):
            self._listen_btn.text = text
            self._listen_btn.disabled = not enabled

    @mainthread
    def _set_status(self, text: str) -> None:
        if hasattr(self, "_status_label"):
            self._status_label.text = text
