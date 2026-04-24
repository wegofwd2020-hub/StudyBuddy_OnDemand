"""
tests/test_content_lesson_normalizer.py

Unit tests for src/content/router.py::_normalize_lesson_dict — the
tactical fix for issue #295 (lesson schema drift).

Covers:
  - Legacy shape (placeholder / dev-placeholder seeds) passes through unchanged
  - New pipeline shape (topic/synopsis/key_concepts/learning_objectives)
    maps to LessonResponse fields (title/sections/key_points)
  - Grade parsed from unit_id prefix ("G11-ACC-001" → 11)
  - Missing / partial pipeline fields degrade gracefully (no 500)
  - Non-G unit_ids fall back to grade=0 without crashing
  - Result always satisfies LessonResponse validation
"""

from __future__ import annotations

from src.content.router import _normalize_lesson_dict
from src.content.schemas import LessonResponse


def test_legacy_shape_passes_through_unchanged():
    """A lesson that already has title + sections must be a no-op."""
    legacy = {
        "unit_id": "G8-MATH-001",
        "title": "Linear Equations",
        "grade": 8,
        "subject": "G8-MATH",
        "lang": "en",
        "sections": [{"heading": "Overview", "body": "Single-step equations."}],
        "key_points": ["solve 2x + 3 = 7"],
        "has_audio": False,
        "generated_at": "2026-04-14T14:46:52.218701+00:00",
        "model": "dev-placeholder",
        "content_version": 1,
    }
    result = _normalize_lesson_dict(legacy, unit_id="G8-MATH-001")
    # Same dict (short-circuit).
    assert result is legacy
    # And it's valid under LessonResponse.
    LessonResponse(**result)


def test_new_pipeline_shape_maps_to_lesson_response():
    pipeline = {
        "unit_id": "G11-ACC-001",
        "subject": "G11-ACC",
        "topic": "Theoretical Framework",
        "synopsis": "This lesson introduces the conceptual framework…",
        "key_concepts": [
            "Conceptual Framework for Financial Reporting",
            "Objectives of General Purpose Financial Reporting",
        ],
        "learning_objectives": [
            "Explain the purpose and structure of the conceptual framework.",
            "Identify the primary users of financial reports.",
        ],
        "reading_level": "Grade 11–12 (University Preparatory)",
        "estimated_duration_minutes": 40,
        "language": "en",
        "generated_at": "2026-04-15T11:33:28.570725+00:00",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    result = _normalize_lesson_dict(pipeline, unit_id="G11-ACC-001")

    # Top-level mapping
    assert result["unit_id"] == "G11-ACC-001"
    assert result["title"] == "Theoretical Framework"
    assert result["grade"] == 11  # parsed from unit_id
    assert result["subject"] == "G11-ACC"
    assert result["lang"] == "en"
    assert result["model"] == "claude-sonnet-4-6"

    # Sections built from synopsis + learning_objectives + key_concepts + reading_level
    headings = [s["heading"] for s in result["sections"]]
    assert "Overview" in headings
    assert "Learning objectives" in headings
    assert "Key concepts" in headings
    assert "Reading level" in headings

    # Synopsis body preserved
    overview = next(s for s in result["sections"] if s["heading"] == "Overview")
    assert "conceptual framework" in overview["body"]

    # Bullets render from learning_objectives
    learn = next(s for s in result["sections"] if s["heading"] == "Learning objectives")
    assert "- Explain the purpose" in learn["body"]
    assert "- Identify the primary users" in learn["body"]

    # key_points carries through from key_concepts
    assert result["key_points"] == pipeline["key_concepts"]

    # Valid under LessonResponse.
    LessonResponse(**result)


def test_grade_parsed_from_various_unit_id_prefixes():
    """G5 through G12 should all parse correctly; non-G should fall back to 0."""
    for grade in (5, 8, 11, 12):
        pipeline = {"topic": "x", "synopsis": "y"}
        result = _normalize_lesson_dict(pipeline, unit_id=f"G{grade}-MATH-001")
        assert result["grade"] == grade

    # Fallback for odd unit_ids.
    result = _normalize_lesson_dict({"topic": "x", "synopsis": "y"}, unit_id="custom-unit-1")
    assert result["grade"] == 0
    LessonResponse(**result)  # still validates


def test_missing_synopsis_and_objectives_yield_overview_fallback():
    """Sparse pipeline output → single Overview section, no validation error."""
    pipeline = {
        "unit_id": "G11-ACC-001",
        "topic": "Theoretical Framework",
        "language": "en",
        "model": "claude-sonnet-4-6",
    }
    result = _normalize_lesson_dict(pipeline, unit_id="G11-ACC-001")
    assert len(result["sections"]) == 1
    assert result["sections"][0]["heading"] == "Overview"
    assert result["sections"][0]["body"] == "Theoretical Framework"
    assert result["key_points"] == []
    LessonResponse(**result)


def test_pipeline_shape_with_language_key_not_lang():
    """Pipeline uses 'language'; legacy/response uses 'lang'. Mapping required."""
    result = _normalize_lesson_dict(
        {"topic": "x", "synopsis": "y", "language": "fr"}, unit_id="G8-MATH-001"
    )
    assert result["lang"] == "fr"


def test_legacy_priority_when_both_shapes_collide():
    """A dict with both 'title' and 'topic' → treat as legacy (title wins,
    short-circuit)."""
    mixed = {
        "unit_id": "G8-MATH-001",
        "title": "Legacy Title",
        "topic": "New Pipeline Topic",  # ignored because legacy shape detected
        "grade": 8,
        "subject": "G8-MATH",
        "lang": "en",
        "sections": [{"heading": "Overview", "body": "ok"}],
        "key_points": [],
    }
    result = _normalize_lesson_dict(mixed, unit_id="G8-MATH-001")
    assert result is mixed  # short-circuit
    assert result["title"] == "Legacy Title"


def test_empty_dict_still_produces_valid_response():
    """Degrade-gracefully: empty dict → Overview section with unit_id as title."""
    result = _normalize_lesson_dict({}, unit_id="G11-ACC-001")
    assert result["title"] == "G11-ACC-001"
    assert result["grade"] == 11
    assert len(result["sections"]) == 1
    LessonResponse(**result)
