"""
mobile/src/ui/QuizScreen.py

Quiz screen — student north star blocker (#72).

Responsibilities:
  - Load quiz from LocalCache (offline-capable), falling back to
    GET /content/{unit_id}/quiz when not cached.
  - Show one MCQ question at a time — 4 options, no timer.
  - Show correct/incorrect colour feedback immediately after answer.
  - Queue record_answer() via EventQueue (fire-and-forget, offline-safe).
  - Open a progress session on enter; close it after the last question.
  - Navigate to ResultScreen with the backend-confirmed score.
  - Show "Download required" when content is absent and device is offline.

Layer rule: QuizScreen is in the ui layer.
  - All API calls go through mobile/src/api/ in daemon threads.
  - All UI mutations are wrapped in @mainthread.
  - record_answer is fire-and-forget — never await it before advancing.
"""

from __future__ import annotations

import threading
import time
import uuid as _uuid

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.clock import mainthread, Clock  # type: ignore
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object  # type: ignore
    mainthread = lambda f: f  # type: ignore  # no-op in tests / CI
    KIVY_AVAILABLE = False

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):  # type: ignore
        return logging.getLogger(name)

log = get_logger("quiz_screen")

PASS_THRESHOLD = 60  # percent — score / total * 100 must be >= this to pass


class QuizScreen(Screen):
    """
    MCQ quiz screen with fire-and-forget answer recording.

    Caller must call set_context() before switching to this screen:
        quiz_screen.set_context(token, unit_id, curriculum_id, lang)
        screen_manager.current = "quiz"
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._token: str = ""
        self._unit_id: str = ""
        self._curriculum_id: str = ""
        self._lang: str = "en"

        # Quiz session state
        self._questions: list[dict] = []
        self._current_idx: int = 0
        self._correct_count: int = 0
        self._session_id: str | None = None
        self._question_started_at: float = 0.0
        self._options_locked: bool = False  # prevents double-tap

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
        """Set quiz context before navigating to this screen."""
        self._token = token
        self._unit_id = unit_id
        self._curriculum_id = curriculum_id
        self._lang = lang

    # ── Kivy lifecycle ────────────────────────────────────────────────────────

    def on_enter(self, *_) -> None:
        """Called by Kivy when screen becomes active."""
        self._reset_state()
        threading.Thread(target=self._load_and_start, daemon=True).start()

    def on_leave(self, *_) -> None:
        """Called by Kivy when leaving — unlock options so retry works."""
        self._options_locked = False

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=24, spacing=14)

        # "Question N of 8" progress indicator
        self._progress_label = Label(
            text="",
            font_size="13sp",
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, None),
            height=26,
            halign="right",
        )
        self._progress_label.bind(
            width=lambda *_: setattr(
                self._progress_label, "text_size",
                (self._progress_label.width, None),
            )
        )
        root.add_widget(self._progress_label)

        # Question text
        self._question_label = Label(
            text="Loading quiz…",
            font_size="18sp",
            halign="left",
            valign="top",
            size_hint=(1, 0.3),
        )
        self._question_label.bind(
            size=lambda *_: setattr(
                self._question_label, "text_size", self._question_label.size
            )
        )
        root.add_widget(self._question_label)

        # Correct / incorrect feedback (shown briefly after answer)
        self._feedback_label = Label(
            text="",
            font_size="16sp",
            bold=True,
            halign="center",
            size_hint=(1, None),
            height=36,
        )
        root.add_widget(self._feedback_label)

        # Four option buttons (A–D)
        self._option_buttons: list[Button] = []
        for i in range(4):
            btn = Button(
                text="",
                font_size="15sp",
                halign="left",
                size_hint=(1, None),
                height=54,
            )
            btn.bind(on_press=lambda _btn, idx=i: self._on_option_pressed(idx))
            root.add_widget(btn)
            self._option_buttons.append(btn)

        # Status / offline notice
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

    # ── State management ──────────────────────────────────────────────────────

    def _reset_state(self) -> None:
        self._questions = []
        self._current_idx = 0
        self._correct_count = 0
        self._session_id = None
        self._question_started_at = 0.0
        self._options_locked = False
        if KIVY_AVAILABLE and hasattr(self, "_question_label"):
            self._set_loading("Loading quiz…")

    # ── Load quiz + open session (daemon thread) ──────────────────────────────

    def _load_and_start(self) -> None:
        """Daemon thread: fetch quiz content then open a progress session."""
        quiz_data = self._load_quiz()
        if quiz_data is None:
            return  # _show_offline() already called

        questions = quiz_data.get("questions", [])
        if not questions:
            self._show_error("No questions available for this unit.")
            return
        self._questions = questions

        # Open progress session — continue without one if it fails (offline path)
        try:
            import asyncio
            from mobile.src.api.progress_client import start_session  # type: ignore
            loop = asyncio.new_event_loop()
            session = loop.run_until_complete(
                start_session(self._token, self._unit_id, self._curriculum_id)
            )
            loop.close()
            self._session_id = session.get("session_id")
            log.info("quiz_session_started session_id=%s unit_id=%s",
                     self._session_id, self._unit_id)
        except Exception as exc:
            log.warning("session_start_failed unit_id=%s error=%s — continuing offline",
                        self._unit_id, exc)

        self._render_question(self._current_idx)

    def _load_quiz(self) -> dict | None:
        """Return quiz JSON. Tries LocalCache first, then the backend API."""
        # ── L1: local cache ────────────────────────────────────────────────
        try:
            from mobile.src.logic.LocalCache import LocalCache  # type: ignore
            cached = LocalCache().get(
                self._unit_id, self._curriculum_id, "quiz", self._lang, 1
            )
            if cached is not None:
                log.info("quiz_cache_hit unit_id=%s", self._unit_id)
                return cached
        except Exception as exc:
            log.warning("quiz_cache_read_failed error=%s", exc)

        # ── L2: backend API ───────────────────────────────────────────────
        try:
            import asyncio
            from mobile.src.api.content_client import get_quiz  # type: ignore
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(get_quiz(self._unit_id, self._token))
            loop.close()

            # Write to cache for next offline use
            try:
                from mobile.src.logic.LocalCache import LocalCache  # type: ignore
                LocalCache().put(
                    self._unit_id, self._curriculum_id, "quiz", self._lang,
                    data.get("content_version", 1), data,
                )
            except Exception as exc:
                log.warning("quiz_cache_write_failed error=%s", exc)

            log.info("quiz_fetched_from_api unit_id=%s questions=%d",
                     self._unit_id, len(data.get("questions", [])))
            return data

        except Exception as exc:
            log.warning("quiz_fetch_failed unit_id=%s error=%s", self._unit_id, exc)
            self._show_offline()
            return None

    # ── Question rendering ────────────────────────────────────────────────────

    @mainthread
    def _set_loading(self, text: str) -> None:
        if hasattr(self, "_question_label"):
            self._question_label.text = text
        if hasattr(self, "_progress_label"):
            self._progress_label.text = ""
        if hasattr(self, "_feedback_label"):
            self._feedback_label.text = ""
        for btn in getattr(self, "_option_buttons", []):
            btn.text = ""
            btn.disabled = True

    @mainthread
    def _render_question(self, idx: int) -> None:
        """Build question UI for the question at position idx."""
        if not self._questions:
            return
        q = self._questions[idx]
        total = len(self._questions)

        self._question_label.text = q.get("question", "")
        self._progress_label.text = f"Question {idx + 1} of {total}"
        self._feedback_label.text = ""
        self._feedback_label.color = (1, 1, 1, 1)
        self._status_label.text = ""

        options = q.get("options", [])
        for i, btn in enumerate(self._option_buttons):
            if i < len(options):
                btn.text = options[i]
                btn.disabled = False
                btn.background_color = (1, 1, 1, 1)
            else:
                btn.text = ""
                btn.disabled = True

        self._options_locked = False
        self._question_started_at = time.monotonic()

    # ── Answer flow ───────────────────────────────────────────────────────────

    def _on_option_pressed(self, chosen_idx: int) -> None:
        """Button callback (main thread). Show feedback then advance."""
        if self._options_locked or not self._questions:
            return
        self._options_locked = True

        q = self._questions[self._current_idx]
        correct_idx: int = q.get("correct_index", -1)
        is_correct = chosen_idx == correct_idx
        ms_taken = int((time.monotonic() - self._question_started_at) * 1000)

        if is_correct:
            self._correct_count += 1

        self._show_answer_feedback(chosen_idx, correct_idx, is_correct)

        # Fire-and-forget answer recording — never blocks the UI thread
        threading.Thread(
            target=self._record_answer_async,
            args=(q, chosen_idx, correct_idx, is_correct, ms_taken),
            daemon=True,
        ).start()

        # Advance after 0.9 s so student can absorb the feedback
        if KIVY_AVAILABLE:
            Clock.schedule_once(lambda _dt: self._advance(), 0.9)
        else:
            self._advance()

    @mainthread
    def _show_answer_feedback(
        self,
        chosen_idx: int,
        correct_idx: int,
        is_correct: bool,
    ) -> None:
        """Colour buttons and set feedback text. Always on the main thread."""
        for i, btn in enumerate(self._option_buttons):
            btn.disabled = True
            if i == correct_idx:
                btn.background_color = (0.2, 0.75, 0.3, 1)   # green — correct answer
            elif i == chosen_idx and not is_correct:
                btn.background_color = (0.85, 0.25, 0.2, 1)  # red — wrong choice

        if hasattr(self, "_feedback_label"):
            if is_correct:
                self._feedback_label.text = "✓ Correct!"
                self._feedback_label.color = (0.2, 0.75, 0.3, 1)
            else:
                letters = ["A", "B", "C", "D"]
                letter = letters[correct_idx] if 0 <= correct_idx < len(letters) else "?"
                self._feedback_label.text = f"✗  Correct answer: {letter}"
                self._feedback_label.color = (0.85, 0.25, 0.2, 1)

    def _advance(self) -> None:
        """Move to next question; end session when all questions answered."""
        next_idx = self._current_idx + 1
        if next_idx < len(self._questions):
            self._current_idx = next_idx
            self._render_question(next_idx)
        else:
            threading.Thread(target=self._end_session_thread, daemon=True).start()

    def _record_answer_async(
        self,
        question: dict,
        chosen_idx: int,
        correct_idx: int,
        is_correct: bool,
        ms_taken: int,
    ) -> None:
        """
        Fire-and-forget answer recording.

        Tries the backend API when a session_id is available.
        Falls back to EventQueue on failure or when offline.
        EventQueue is flushed by SyncManager on next connectivity.
        """
        question_id: str = question.get("question_id", "")
        event_id: str = str(_uuid.uuid4())

        if self._session_id:
            try:
                import asyncio
                from mobile.src.api.progress_client import record_answer  # type: ignore
                loop = asyncio.new_event_loop()
                loop.run_until_complete(record_answer(
                    self._token,
                    self._session_id,
                    question_id,
                    chosen_idx,
                    correct_idx,
                    is_correct,
                    ms_taken,
                    event_id=event_id,
                ))
                loop.close()
                log.info("answer_recorded q=%s correct=%s", question_id, is_correct)
                return
            except Exception as exc:
                log.warning("answer_api_failed q=%s error=%s — falling back to queue",
                            question_id, exc)

        # EventQueue fallback (offline-safe, SyncManager flushes on reconnect)
        try:
            from mobile.src.logic.EventQueue import EventQueue  # type: ignore
            EventQueue().enqueue("progress_answer", {
                "event_id": event_id,
                "session_id": self._session_id,
                "question_id": question_id,
                "unit_id": self._unit_id,
                "curriculum_id": self._curriculum_id,
                "student_answer": chosen_idx,
                "correct_answer": correct_idx,
                "correct": is_correct,
                "ms_taken": ms_taken,
            })
            log.info("answer_queued_offline q=%s", question_id)
        except Exception as exc:
            log.warning("answer_queue_failed q=%s error=%s", question_id, exc)

    # ── Session end ───────────────────────────────────────────────────────────

    def _end_session_thread(self) -> None:
        """Daemon thread: close the session and navigate to ResultScreen."""
        total = len(self._questions)

        # Local fallback result (used if end_session API call fails)
        result_data: dict = {
            "session_id": self._session_id or "",
            "score": self._correct_count,
            "total_questions": total,
            "passed": (
                self._correct_count / total * 100 >= PASS_THRESHOLD
                if total > 0 else False
            ),
            "attempt_number": 1,
            "ended_at": "",
        }

        if self._session_id:
            try:
                import asyncio
                from mobile.src.api.progress_client import end_session  # type: ignore
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    end_session(
                        self._token, self._session_id,
                        self._correct_count, total,
                    )
                )
                loop.close()
                # Backend score + passed flag are authoritative
                result_data.update(result)
                log.info(
                    "session_ended session_id=%s score=%d/%d passed=%s",
                    self._session_id,
                    result_data.get("score"),
                    total,
                    result_data.get("passed"),
                )
            except Exception as exc:
                log.warning(
                    "end_session_failed session_id=%s error=%s — using local score",
                    self._session_id, exc,
                )

        self._navigate_to_result(result_data)

    @mainthread
    def _navigate_to_result(self, result_data: dict) -> None:
        """Navigate to ResultScreen, passing the backend-confirmed result."""
        if not (KIVY_AVAILABLE and hasattr(self, "manager") and self.manager):
            return
        if self.manager.has_screen("result"):
            try:
                self.manager.get_screen("result").populate(result_data)
            except Exception as exc:
                log.warning("result_screen_populate_failed error=%s", exc)
        self.manager.current = "result"

    # ── Offline / error states ────────────────────────────────────────────────

    @mainthread
    def _show_offline(self) -> None:
        """Displayed when quiz is not in cache and network is unreachable."""
        if hasattr(self, "_question_label"):
            self._question_label.text = "Download required"
        if hasattr(self, "_status_label"):
            self._status_label.text = (
                "This quiz isn't available offline. "
                "Connect to the internet and try again."
            )
        if hasattr(self, "_progress_label"):
            self._progress_label.text = ""
        if hasattr(self, "_feedback_label"):
            self._feedback_label.text = ""
        for btn in getattr(self, "_option_buttons", []):
            btn.text = ""
            btn.disabled = True
        log.info("quiz_offline_shown unit_id=%s", self._unit_id)

    @mainthread
    def _show_error(self, message: str) -> None:
        if hasattr(self, "_question_label"):
            self._question_label.text = "Quiz unavailable"
        if hasattr(self, "_status_label"):
            self._status_label.text = message
        log.warning("quiz_error unit_id=%s message=%s", self._unit_id, message)
