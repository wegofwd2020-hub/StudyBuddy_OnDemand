"""The "Up next" card's minute estimate comes from the lesson, not a literal.

`"estimated_minutes": 20` was hardcoded in `_build_dashboard`, so every unit in
the product told every student the same thing next to a clock icon. A tester
asked what pattern the card followed; this is half the answer.

Numbers here were calibrated against the real content store rather than picked:
across the 253 non-fixture lesson files, total lesson text runs 129 / 205 / 1835
/ 2233 / 3084 words at min / p25 / median / p75 / max. Only 3 fall under the
20-word floor.
"""

from __future__ import annotations

import pytest

from src.core.reading_time import (
    _wpm_for_grade,
    count_lesson_words,
    estimate_unit_minutes,
)


def _lesson(**kw) -> dict:
    return kw


# ── Word counting across the three lesson shapes (pitfall #33) ────────────────


def test_counts_every_field_a_student_reads():
    lesson = _lesson(
        synopsis="one two three",
        learning_objectives=["four five", "six"],
        key_points=["seven eight"],
        sections=[{"heading": "nine", "body": "ten eleven twelve"}],
    )
    assert count_lesson_words(lesson) == 12


def test_a_legacy_synopsis_only_lesson_still_counts():
    """90 of 253 real lessons predate the C-5 regeneration and have no sections.

    Counting section bodies alone would return nothing for a third of the
    corpus, so the card would silently lose its estimate on exactly the units
    most in need of regeneration.
    """
    lesson = _lesson(synopsis=" ".join(["word"] * 300))
    assert count_lesson_words(lesson) == 300
    assert estimate_unit_minutes(lesson, grade=8) is not None


def test_a_malformed_lesson_costs_only_its_own_estimate():
    """This runs on the dashboard path: it must not raise."""
    assert count_lesson_words(None) == 0
    assert count_lesson_words({}) == 0
    assert count_lesson_words({"sections": "not-a-list"}) == 0
    assert count_lesson_words({"sections": ["not-a-dict"]}) == 0
    assert count_lesson_words({"key_points": None}) == 0


# ── The estimate ──────────────────────────────────────────────────────────────


def test_a_stub_lesson_yields_no_estimate_rather_than_a_guess():
    assert estimate_unit_minutes(_lesson(synopsis="three words here"), grade=8) is None
    assert estimate_unit_minutes({}, grade=8) is None


def test_the_estimate_varies_with_lesson_length():
    """The whole point. A literal 20 is wrong precisely because it never moves."""
    short = _lesson(synopsis=" ".join(["word"] * 205))  # real p25
    long_ = _lesson(synopsis=" ".join(["word"] * 2233))  # real p75
    assert estimate_unit_minutes(short, grade=8) < estimate_unit_minutes(long_, grade=8)


def test_a_younger_student_is_given_longer():
    """Same lesson, lower grade, slower assumed reading rate."""
    lesson = _lesson(synopsis=" ".join(["word"] * 1835))  # real median
    assert estimate_unit_minutes(lesson, grade=5) > estimate_unit_minutes(lesson, grade=12)


def test_the_median_real_lesson_lands_where_measured():
    """1835 words at grade 8 (~168 wpm) + 5 min quiz ≈ 16 → rounds to 15."""
    lesson = _lesson(synopsis=" ".join(["word"] * 1835))
    assert estimate_unit_minutes(lesson, grade=8) == 15


def test_it_rounds_to_five_because_the_card_says_about():
    for words in (300, 800, 1500, 2500):
        minutes = estimate_unit_minutes(_lesson(synopsis=" ".join(["w"] * words)), grade=8)
        assert minutes % 5 == 0, f"{words} words gave {minutes}"


def test_never_below_the_quiz_allowance():
    """A 25-word lesson still has an 8-question quiz attached to it."""
    assert estimate_unit_minutes(_lesson(synopsis=" ".join(["w"] * 25)), grade=8) >= 5


# ── Reading rate ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "grade,expected",
    [(5, 130), (12, 220), (8, 169)],
)
def test_rate_is_linear_between_the_endpoints(grade, expected):
    assert _wpm_for_grade(grade) == expected


def test_out_of_range_and_missing_grades_are_clamped_not_extrapolated():
    """A grade outside 5-12 is a data error, not a licence to invent a rate."""
    assert _wpm_for_grade(1) == _wpm_for_grade(5)
    assert _wpm_for_grade(99) == _wpm_for_grade(12)
    # No grade at all sits mid-range rather than guessing an end.
    assert _wpm_for_grade(5) < _wpm_for_grade(None) < _wpm_for_grade(12)
