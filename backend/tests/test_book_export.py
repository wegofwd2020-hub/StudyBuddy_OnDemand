"""
backend/tests/test_book_export.py

Unit tests for the OnDemand → StudyBuddy Q book export transforms
(``src/admin/book_export.py``). Pure functions, no DB — synthetic bodies mirror
the shapes enforced by ``pipeline/schemas.py``.
"""

from __future__ import annotations

import pytest

from src.admin.book_export import (
    BookExportError,
    assemble_book,
    experiment_to_q,
    lesson_to_q,
    quiz_to_q,
    topic_id_for,
    tutorial_to_q,
)

# ── Synthetic bodies (match pipeline/schemas.py required fields) ───────────────


def _lesson_body() -> dict:
    return {
        "unit_id": "AUTH-abc-CE-001",
        "subject": "Context Engineering",
        "topic": "Why Context Engineering Emerged",
        "synopsis": "A short overview of the topic.",
        "sections": [
            {"heading": "Introduction", "body": "Intro **markdown** body."},
            {"heading": "Core Concepts", "body": "Core body with a $formula$."},
        ],
        "key_points": ["point one", "point two"],
        "learning_objectives": ["Explain X", "Identify Y"],
        "reading_level": "Grade 11 reading level",
        "estimated_duration_minutes": 20,
        "language": "en",
        "generated_at": "2026-05-26T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }


def _tutorial_body() -> dict:
    return {
        "unit_id": "AUTH-abc-CE-001",
        "language": "en",
        "title": "Tutorial: Context Engineering",
        "sections": [
            {
                "section_id": "s1",
                "title": "Step 1",
                "content": "Do the thing.",
                "examples": ["example a"],
                "practice_question": "What is the thing?",
            }
        ],
        "common_mistakes": ["forgetting context"],
        "generated_at": "2026-05-26T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }


def _quiz_body(set_number: int) -> dict:
    return {
        "unit_id": "AUTH-abc-CE-001",
        "set_number": set_number,
        "language": "en",
        "questions": [
            {
                "question_id": "q1",
                "question_text": "Which is correct?",
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": "A", "text": "alpha"},
                    {"option_id": "B", "text": "beta"},
                    {"option_id": "C", "text": "gamma"},
                    {"option_id": "D", "text": "delta"},
                ],
                "correct_option": "B",
                "explanation": "Because beta.",
                "difficulty": "medium",
            }
        ],
        "total_questions": 1,
        "estimated_duration_minutes": 5,
        "passing_score": 1,
        "generated_at": "2026-05-26T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }


def _experiment_body() -> dict:
    return {
        "unit_id": "AUTH-abc-CE-001",
        "language": "en",
        "experiment_title": "Observe context windows",
        "materials": ["a laptop"],
        "safety_notes": ["mind the cables"],
        "steps": [
            {"step_number": 1, "instruction": "Open the tool.", "expected_observation": "It opens."}
        ],
        "questions": [{"question": "What happened?", "answer": "It opened."}],
        "conclusion_prompt": "Summarise what you observed.",
        "generated_at": "2026-05-26T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }


# ── Per-type transforms ────────────────────────────────────────────────────────


def test_lesson_to_q_renames_fields():
    q = lesson_to_q(_lesson_body(), unit_title="Why Context Engineering Emerged", grade=11)
    # Renamed/derived fields
    assert q["key_takeaways"] == ["point one", "point two"]  # was key_points
    assert q["level"] == "Grade 11 reading level"  # was reading_level
    assert q["sections"][0] == {
        "heading": "Introduction",
        "body_markdown": "Intro **markdown** body.",
    }
    assert "body" not in q["sections"][0]  # old field name dropped
    # Direct fields
    assert q["topic"] == "Why Context Engineering Emerged"
    assert q["synopsis"] == "A short overview of the topic."
    assert q["learning_objectives"] == ["Explain X", "Identify Y"]
    assert q["language"] == "en"
    # No OnDemand counterpart → empty default
    assert q["further_reading"] == []
    # Pipeline metadata not carried over
    assert "model" not in q and "content_version" not in q


def test_lesson_to_q_level_falls_back_to_grade():
    body = _lesson_body()
    del body["reading_level"]
    q = lesson_to_q(body, unit_title="T", grade=9)
    assert q["level"] == "Grade 9"


def test_lesson_to_q_topic_falls_back_to_unit_title():
    body = _lesson_body()
    del body["topic"]
    q = lesson_to_q(body, unit_title="Fallback Title")
    assert q["topic"] == "Fallback Title"


def test_tutorial_to_q_keeps_schema_strips_metadata():
    q = tutorial_to_q(_tutorial_body())
    assert q["title"] == "Tutorial: Context Engineering"
    assert q["sections"][0]["practice_question"] == "What is the thing?"
    assert q["sections"][0]["examples"] == ["example a"]
    assert q["common_mistakes"] == ["forgetting context"]
    assert "unit_id" not in q and "model" not in q


def test_quiz_to_q_preserves_questions_and_options():
    q = quiz_to_q(_quiz_body(2))
    assert q["set_number"] == 2
    assert q["passing_score"] == 1
    assert q["questions"][0]["correct_option"] == "B"
    assert q["questions"][0]["options"][1] == {"option_id": "B", "text": "beta"}
    assert "model" not in q


def test_experiment_to_q_maps_steps_and_questions():
    q = experiment_to_q(_experiment_body())
    assert q["experiment_title"] == "Observe context windows"
    assert q["steps"][0]["expected_observation"] == "It opens."
    assert q["questions"][0] == {"question": "What happened?", "answer": "It opened."}
    assert q["conclusion_prompt"] == "Summarise what you observed."
    assert "unit_id" not in q


# ── Assembly ────────────────────────────────────────────────────────────────────


def _project(units_titles: list[str]) -> dict:
    return {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "title": "Context Engineering in the Enterprise",
        "grade": 11,
        "structured_toc": {
            "subjects": [
                {
                    "subject_label": "Context Engineering",
                    "units": [
                        {"title": t, "subtopics": ["a", "b"], "prerequisites": []}
                        for t in units_titles
                    ],
                }
            ]
        },
    }


def test_assemble_book_full_fidelity():
    units = [{"unit_id": "U1", "title": "Why Context Engineering Emerged"}]
    versions = [
        {"unit_id": "U1", "content_type": "lesson", "lang": "en", "body": _lesson_body()},
        {"unit_id": "U1", "content_type": "tutorial", "lang": "en", "body": _tutorial_body()},
        {"unit_id": "U1", "content_type": "quiz_set_1", "lang": "en", "body": _quiz_body(1)},
        {"unit_id": "U1", "content_type": "quiz_set_2", "lang": "en", "body": _quiz_body(2)},
        {"unit_id": "U1", "content_type": "quiz_set_3", "lang": "en", "body": _quiz_body(3)},
        {"unit_id": "U1", "content_type": "experiment", "lang": "en", "body": _experiment_body()},
    ]
    book, warnings = assemble_book(_project(["Why Context Engineering Emerged"]), units, versions)

    assert warnings == []
    assert book["id"] == "authored-11111111-1111-1111-1111-111111111111"
    assert book["title"] == "Context Engineering in the Enterprise"

    tid = topic_id_for("U1")
    # TOC unit got the stable id injected so content can be keyed to it.
    assert book["toc"]["subjects"][0]["units"][0]["id"] == tid
    assert tid in book["content"]

    topic = book["content"][tid]
    assert topic["title"] == "Why Context Engineering Emerged"
    assert topic["lesson"]["key_takeaways"] == ["point one", "point two"]
    assert topic["tutorial"]["title"] == "Tutorial: Context Engineering"
    assert [qs["set_number"] for qs in topic["quizSets"]] == [1, 2, 3]  # ordered
    assert topic["experiment"]["experiment_title"] == "Observe context windows"


def test_assemble_book_optional_types_absent_when_not_generated():
    units = [{"unit_id": "U1", "title": "Lesson-only topic"}]
    versions = [
        {"unit_id": "U1", "content_type": "lesson", "lang": "en", "body": _lesson_body()},
    ]
    book, warnings = assemble_book(_project(["Lesson-only topic"]), units, versions)
    topic = book["content"][topic_id_for("U1")]
    assert "lesson" in topic
    assert "tutorial" not in topic
    assert "quizSets" not in topic
    assert "experiment" not in topic
    assert warnings == []


def test_assemble_book_skips_unit_without_lesson_and_warns():
    units = [{"unit_id": "U1", "title": "No lesson here"}]
    versions = [
        {"unit_id": "U1", "content_type": "tutorial", "lang": "en", "body": _tutorial_body()},
    ]
    book, warnings = assemble_book(_project(["No lesson here"]), units, versions)
    assert book["content"] == {}  # nothing emitted without a lesson
    assert len(warnings) == 1 and "no lesson" in warnings[0]


def test_assemble_book_filters_by_language():
    units = [{"unit_id": "U1", "title": "T"}]
    versions = [
        {"unit_id": "U1", "content_type": "lesson", "lang": "fr", "body": _lesson_body()},
    ]
    book, warnings = assemble_book(_project(["T"]), units, versions, lang="en")
    # The only version is fr; exporting en yields no content and a warning.
    assert book["content"] == {}
    assert len(warnings) == 1


def test_assemble_book_raises_on_toc_unit_count_mismatch():
    units = [{"unit_id": "U1", "title": "T1"}]  # 1 curriculum unit
    project = _project(["T1", "T2"])  # 2 TOC units
    with pytest.raises(BookExportError, match="cannot align"):
        assemble_book(project, units, [])


def test_topic_id_is_deterministic():
    assert topic_id_for("U1") == topic_id_for("U1")
    assert topic_id_for("U1") != topic_id_for("U2")
