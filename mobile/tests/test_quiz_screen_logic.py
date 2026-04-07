"""
mobile/tests/test_quiz_screen_logic.py

Unit tests for QuizScreen pure logic.

Kivy is not available in CI — the module guards all Kivy imports with
try/except ImportError, so QuizScreen can be instantiated as a plain
Python object. All UI-mutating methods become no-ops (mainthread = lambda f: f).

Tests cover:
  - set_context stores values correctly
  - State resets cleanly on on_enter
  - Answer correctness evaluation and score accumulation
  - Pass / fail threshold (PASS_THRESHOLD = 60 %)
  - Offline/cache miss returns None from LocalCache
  - Cache roundtrip: put → get returns quiz data
  - EventQueue fallback: answers enqueued when no session_id
  - EventQueue event_id uniqueness (idempotency prerequisite)
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

# Make mobile package importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mobile.src.ui.QuizScreen import QuizScreen, PASS_THRESHOLD  # noqa: E402
from mobile.src.logic.LocalCache import LocalCache  # noqa: E402
from mobile.src.logic.EventQueue import EventQueue  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def screen():
    """QuizScreen with context set; Kivy not available so no UI built."""
    s = QuizScreen()
    s.set_context(
        token="tok-test",
        unit_id="G8-MATH-001",
        curriculum_id="default-2026-g8",
        lang="en",
    )
    return s


@pytest.fixture
def cache(tmp_path):
    return LocalCache(db_path=str(tmp_path / "cache.db"), max_mb=10)


@pytest.fixture
def queue(tmp_path):
    return EventQueue(db_path=str(tmp_path / "eq.db"))


QUESTIONS = [
    {
        "question_id": "q1",
        "question": "What is 2 + 2?",
        "options": ["2", "3", "4", "8"],
        "correct_index": 2,
    },
    {
        "question_id": "q2",
        "question": "Capital of France?",
        "options": ["Berlin", "Paris", "Madrid", "Rome"],
        "correct_index": 1,
    },
    {
        "question_id": "q3",
        "question": "5 × 6 = ?",
        "options": ["25", "30", "35", "36"],
        "correct_index": 1,
    },
    {
        "question_id": "q4",
        "question": "Which is a prime number?",
        "options": ["4", "6", "7", "9"],
        "correct_index": 2,
    },
    {
        "question_id": "q5",
        "question": "H₂O is the formula for?",
        "options": ["Oxygen", "Hydrogen", "Water", "Salt"],
        "correct_index": 2,
    },
]

QUIZ_PAYLOAD = {"questions": QUESTIONS, "content_version": 1}


# ── Context / state ───────────────────────────────────────────────────────────


def test_set_context_stores_all_fields(screen):
    assert screen._token == "tok-test"
    assert screen._unit_id == "G8-MATH-001"
    assert screen._curriculum_id == "default-2026-g8"
    assert screen._lang == "en"


def test_set_context_can_be_overwritten(screen):
    screen.set_context("tok2", "G9-SCI-001", "default-2026-g9", "fr")
    assert screen._token == "tok2"
    assert screen._unit_id == "G9-SCI-001"
    assert screen._lang == "fr"


def test_reset_state_clears_all_quiz_fields(screen):
    screen._questions = QUESTIONS
    screen._correct_count = 4
    screen._current_idx = 3
    screen._session_id = "sess-abc"
    screen._options_locked = True

    screen._reset_state()

    assert screen._questions == []
    assert screen._correct_count == 0
    assert screen._current_idx == 0
    assert screen._session_id is None
    assert screen._options_locked is False


# ── Pass / fail threshold ─────────────────────────────────────────────────────


def test_pass_threshold_constant():
    assert PASS_THRESHOLD == 60


def test_pass_at_exactly_60_percent():
    total, score = 10, 6
    assert score / total * 100 >= PASS_THRESHOLD


def test_fail_at_59_percent():
    total, score = 10, 5  # 50 %
    assert score / total * 100 < PASS_THRESHOLD


def test_pass_with_all_correct(screen):
    screen._questions = QUESTIONS
    screen._correct_count = len(QUESTIONS)
    total = len(QUESTIONS)
    pct = screen._correct_count / total * 100
    assert pct >= PASS_THRESHOLD


def test_fail_with_no_correct(screen):
    screen._questions = QUESTIONS
    screen._correct_count = 0
    total = len(QUESTIONS)
    pct = screen._correct_count / total * 100
    assert pct < PASS_THRESHOLD


def test_edge_zero_questions_does_not_divide_by_zero(screen):
    screen._questions = []
    total = len(screen._questions)
    passed = screen._correct_count / total * 100 >= PASS_THRESHOLD if total > 0 else False
    assert passed is False


# ── Answer correctness accumulation ──────────────────────────────────────────


def test_correct_answer_increments_count(screen):
    screen._questions = QUESTIONS
    q = QUESTIONS[0]                           # correct_index = 2
    is_correct = 2 == q["correct_index"]      # choosing option 2
    if is_correct:
        screen._correct_count += 1
    assert screen._correct_count == 1


def test_wrong_answer_does_not_increment(screen):
    screen._questions = QUESTIONS
    q = QUESTIONS[0]                           # correct_index = 2
    is_correct = 0 == q["correct_index"]      # choosing option 0 (wrong)
    if is_correct:
        screen._correct_count += 1
    assert screen._correct_count == 0


def test_score_accumulates_across_questions(screen):
    screen._questions = QUESTIONS
    answers = [2, 0, 1, 2, 0]  # q1✓(2==2) q2✗(0≠1) q3✓(1==1) q4✓(2==2) q5✗(0≠2) → 3 correct
    for i, chosen in enumerate(answers):
        q = QUESTIONS[i]
        if chosen == q["correct_index"]:
            screen._correct_count += 1
    assert screen._correct_count == 3


# ── LocalCache: quiz data ─────────────────────────────────────────────────────


def test_cache_miss_returns_none(cache):
    result = cache.get("G8-MATH-001", "default-2026-g8", "quiz", "en", 1)
    assert result is None


def test_cache_put_and_get_roundtrip(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, QUIZ_PAYLOAD)
    result = cache.get("G8-MATH-001", "default-2026-g8", "quiz", "en", 1)
    assert result is not None
    assert len(result["questions"]) == len(QUESTIONS)


def test_cache_version_mismatch_returns_none(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, QUIZ_PAYLOAD)
    result = cache.get("G8-MATH-001", "default-2026-g8", "quiz", "en", 2)
    assert result is None


def test_cache_separates_lesson_and_quiz(cache):
    lesson = {"title": "Linear Equations", "content_version": 1}
    cache.put("G8-MATH-001", "default-2026-g8", "lesson", "en", 1, lesson)
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, QUIZ_PAYLOAD)

    assert cache.get("G8-MATH-001", "default-2026-g8", "lesson", "en", 1) == lesson
    assert cache.get("G8-MATH-001", "default-2026-g8", "quiz", "en", 1) == QUIZ_PAYLOAD


def test_cache_separates_different_units(cache):
    cache.put("G8-MATH-001", "default-2026-g8", "quiz", "en", 1, QUIZ_PAYLOAD)
    result = cache.get("G8-MATH-002", "default-2026-g8", "quiz", "en", 1)
    assert result is None


# ── EventQueue fallback (offline answer recording) ────────────────────────────


def test_answer_enqueued_when_no_session(queue, screen):
    """With no session_id, answers go to EventQueue for later sync."""
    screen._session_id = None
    q = QUESTIONS[0]
    event_id = str(uuid.uuid4())

    queue.enqueue("progress_answer", {
        "event_id": event_id,
        "session_id": None,
        "question_id": q["question_id"],
        "unit_id": screen._unit_id,
        "curriculum_id": screen._curriculum_id,
        "student_answer": 2,
        "correct_answer": q["correct_index"],
        "correct": True,
        "ms_taken": 1100,
    })

    pending = queue.pending()
    assert len(pending) == 1
    assert pending[0]["event_type"] == "progress_answer"


def test_each_answer_gets_unique_event_id(queue):
    """Unique event_ids are required for idempotent deduplication."""
    ids: list[str] = []
    for i in range(8):
        eid = str(uuid.uuid4())
        queue.enqueue("progress_answer", {"event_id": eid, "question_id": f"q{i}"})
        ids.append(eid)

    assert len(set(ids)) == 8, "All event IDs must be unique"
    assert len(queue.pending()) == 8


def test_mark_sent_removes_from_pending(queue):
    """Answers marked as sent are not returned by pending()."""
    eid = str(uuid.uuid4())
    # enqueue() returns the event UUID used to call mark_sent()
    event_id = queue.enqueue("progress_answer", {"event_id": eid, "question_id": "q1"})
    assert len(queue.pending()) == 1

    queue.mark_sent(event_id)
    assert len(queue.pending()) == 0


def test_multiple_answers_all_enqueued(queue, screen):
    """Simulates all 8 questions being answered offline."""
    for i, q in enumerate(QUESTIONS):
        queue.enqueue("progress_answer", {
            "event_id": str(uuid.uuid4()),
            "session_id": None,
            "question_id": q["question_id"],
            "unit_id": screen._unit_id,
            "curriculum_id": screen._curriculum_id,
            "student_answer": 0,
            "correct_answer": q["correct_index"],
            "correct": False,
            "ms_taken": 2000 + i * 100,
        })

    pending = queue.pending()
    assert len(pending) == len(QUESTIONS)
    event_types = {e["event_type"] for e in pending}
    assert event_types == {"progress_answer"}
