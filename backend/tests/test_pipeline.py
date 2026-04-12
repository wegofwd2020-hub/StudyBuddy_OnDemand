"""
tests/test_pipeline.py

Tests for the content pipeline (prompts, schemas, build_unit logic).

All external calls (Anthropic SDK, filesystem writes) are mocked.
No live DB, Claude API, or filesystem I/O in CI.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import jsonschema
import pytest


# ── Prompt tests ──────────────────────────────────────────────────────────────

def test_prompts_return_strings():
    """All prompt builder functions return non-empty strings."""
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from pipeline.prompts import (
        build_lesson_prompt,
        build_quiz_prompt,
        build_tutorial_prompt,
        build_experiment_prompt,
    )

    lesson_p = build_lesson_prompt("G8-SCI-001", "Science", "Density", 8, "en")
    assert isinstance(lesson_p, str) and len(lesson_p) > 50

    quiz_p = build_quiz_prompt("G8-SCI-001", "Science", "Density", 8, "en", 1)
    assert isinstance(quiz_p, str) and len(quiz_p) > 50

    tutorial_p = build_tutorial_prompt("G8-SCI-001", "Science", "Density", 8, "en")
    assert isinstance(tutorial_p, str) and len(tutorial_p) > 50

    exp_p = build_experiment_prompt("G8-SCI-001", "Science", "Density", 8, "en")
    assert isinstance(exp_p, str) and len(exp_p) > 50

    # Grade-level descriptor should differ
    p5 = build_lesson_prompt("G5-SCI-001", "Science", "Plants", 5, "en")
    p12 = build_lesson_prompt("G12-SCI-001", "Science", "Quantum", 12, "en")
    assert p5 != p12  # different grade descriptors

    # French prompt should mention FR / French
    p_fr = build_lesson_prompt("G8-SCI-001", "Science", "Density", 8, "fr")
    assert "FR" in p_fr or "French" in p_fr or "french" in p_fr.lower()


# ── Schema validation tests ───────────────────────────────────────────────────

def test_schema_validation_lesson():
    """Valid lesson dict passes; missing required field fails."""
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from pipeline.schemas import validate_lesson

    valid = {
        "unit_id": "G8-SCI-001",
        "subject": "Science",
        "topic": "Density",
        "synopsis": "Learn about density and buoyancy.",
        "key_concepts": ["density", "buoyancy"],
        "learning_objectives": ["Explain density"],
        "reading_level": "Grade 8",
        "estimated_duration_minutes": 30,
        "language": "en",
        "generated_at": "2026-03-25T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    validate_lesson(valid)  # must not raise

    # Missing required field
    invalid = dict(valid)
    del invalid["synopsis"]
    with pytest.raises(jsonschema.ValidationError):
        validate_lesson(invalid)


def test_schema_validation_quiz_8_questions():
    """Quiz with 8 questions passes; 7 questions fails."""
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from pipeline.schemas import validate_quiz

    def _make_question(n: int) -> dict:
        return {
            "question_id": f"q{n}",
            "question_text": f"Question {n}?",
            "question_type": "multiple_choice",
            "options": [
                {"option_id": "A", "text": "Option A"},
                {"option_id": "B", "text": "Option B"},
                {"option_id": "C", "text": "Option C"},
                {"option_id": "D", "text": "Option D"},
            ],
            "correct_option": "A",
            "explanation": "Because A is correct.",
            "difficulty": "medium",
        }

    valid_quiz = {
        "unit_id": "G8-SCI-001",
        "set_number": 1,
        "language": "en",
        "questions": [_make_question(i) for i in range(1, 9)],  # 8 questions
        "total_questions": 8,
        "estimated_duration_minutes": 10,
        "passing_score": 6,
        "generated_at": "2026-03-25T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    validate_quiz(valid_quiz)  # must not raise

    # 7 questions should fail
    invalid_quiz = dict(valid_quiz)
    invalid_quiz["questions"] = [_make_question(i) for i in range(1, 8)]  # 7 questions
    invalid_quiz["total_questions"] = 7
    with pytest.raises(jsonschema.ValidationError):
        validate_quiz(invalid_quiz)

    # 9 questions should also fail
    invalid_quiz2 = dict(valid_quiz)
    invalid_quiz2["questions"] = [_make_question(i) for i in range(1, 10)]  # 9 questions
    with pytest.raises(jsonschema.ValidationError):
        validate_quiz(invalid_quiz2)


# ── Idempotency test ──────────────────────────────────────────────────────────

def test_idempotency_skip():
    """build_unit skips generation when meta.json has matching version and all files exist."""
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from pipeline.build_unit import build_unit

    # Create a temp content store
    with tempfile.TemporaryDirectory() as tmpdir:
        curriculum_id = "default-2026-g8"
        unit_id = "G8-MATH-001"
        lang = "en"

        store_path = os.path.join(tmpdir, "curricula", curriculum_id, unit_id)
        os.makedirs(store_path, exist_ok=True)

        # Write mock meta.json with matching content_version
        meta = {
            "unit_id": unit_id,
            "curriculum_id": curriculum_id,
            "generated_at": "2026-03-25T00:00:00Z",
            "model": "claude-sonnet-4-6",
            "content_version": 1,
            "langs_built": ["en"],
            "alex_warnings_count": 0,
        }
        with open(os.path.join(store_path, "meta.json"), "w") as f:
            json.dump(meta, f)

        # Write all expected content files
        for filename in [
            "lesson_en.json", "quiz_set_1_en.json", "quiz_set_2_en.json",
            "quiz_set_3_en.json", "tutorial_en.json"
        ]:
            with open(os.path.join(store_path, filename), "w") as f:
                json.dump({"unit_id": unit_id}, f)

        # Create a mock config
        config = MagicMock()
        config.CONTENT_STORE_PATH = tmpdir
        config.CONTENT_VERSION = 1
        config.CLAUDE_MODEL = "claude-sonnet-4-6"
        config.ANTHROPIC_API_KEY = "test-key"
        config.DEFAULT_PROVIDER = "anthropic"
        config.TOKEN_COST_INPUT_USD = 0.000003
        config.TOKEN_COST_OUTPUT_USD = 0.000015
        config.MAX_PIPELINE_COST_USD = 50.0

        unit_data = {
            "title": "Linear Equations",
            "description": "Solving equations",
            "subject": "G8-MATH",
            "has_lab": False,
            "grade": 8,
        }

        result = build_unit(
            curriculum_id=curriculum_id,
            unit_id=unit_id,
            unit_data=unit_data,
            lang=lang,
            config=config,
            force=False,
        )

    assert result["status"] == "skipped"
    assert result["tokens_used"] == 0


# ── Spend cap test ────────────────────────────────────────────────────────────

def test_spend_cap_raises():
    """
    build_unit raises SpendCapExceeded when estimated cost exceeds MAX_PIPELINE_COST_USD.
    We mock the Claude API to return a huge token count.
    """
    import sys
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from pipeline.build_unit import build_unit, SpendCapExceeded

    # Build a minimal valid lesson response
    valid_lesson = {
        "unit_id": "G8-SCI-001",
        "subject": "Science",
        "topic": "Density",
        "synopsis": "Learn about density and buoyancy in this lesson.",
        "key_concepts": ["density", "buoyancy"],
        "learning_objectives": ["Explain density"],
        "reading_level": "Grade 8",
        "estimated_duration_minutes": 30,
        "language": "en",
        "generated_at": "2026-03-25T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    valid_quiz_questions = [
        {
            "question_id": f"q{i}",
            "question_text": f"Question {i}?",
            "question_type": "multiple_choice",
            "options": [
                {"option_id": "A", "text": "A"},
                {"option_id": "B", "text": "B"},
                {"option_id": "C", "text": "C"},
                {"option_id": "D", "text": "D"},
            ],
            "correct_option": "A",
            "explanation": "A is correct.",
            "difficulty": "medium",
        }
        for i in range(1, 9)
    ]
    valid_quiz = {
        "unit_id": "G8-SCI-001",
        "set_number": 1,
        "language": "en",
        "questions": valid_quiz_questions,
        "total_questions": 8,
        "estimated_duration_minutes": 10,
        "passing_score": 6,
        "generated_at": "2026-03-25T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    valid_tutorial = {
        "unit_id": "G8-SCI-001",
        "language": "en",
        "title": "Density Tutorial",
        "sections": [
            {
                "section_id": "s1",
                "title": "What is Density?",
                "content": "Density is mass divided by volume.",
                "examples": ["A rock is denser than wood."],
                "practice_question": "Calculate density.",
            }
        ],
        "common_mistakes": ["Confusing mass with weight"],
        "generated_at": "2026-03-25T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        config = MagicMock()
        config.CONTENT_STORE_PATH = tmpdir
        config.CONTENT_VERSION = 1
        config.CLAUDE_MODEL = "claude-sonnet-4-6"
        config.ANTHROPIC_API_KEY = "test-key"
        config.DEFAULT_PROVIDER = "anthropic"
        config.S3_BUCKET_NAME = None
        # Very low spend cap — even 1 output token exceeds it
        config.TOKEN_COST_INPUT_USD = 0.000003
        config.TOKEN_COST_OUTPUT_USD = 0.000015
        config.MAX_PIPELINE_COST_USD = 0.000001  # $0.000001 — essentially zero

        unit_data = {
            "title": "Density and Buoyancy",
            "description": "Test",
            "subject": "G8-SCI",
            "has_lab": False,
            "grade": 8,
        }

        # Mock Claude responses: each call returns a valid JSON response with huge token usage
        responses_cycle = [
            json.dumps(valid_lesson),
            json.dumps({**valid_quiz, "set_number": 1}),
            json.dumps({**valid_quiz, "set_number": 2}),
            json.dumps({**valid_quiz, "set_number": 3}),
            json.dumps(valid_tutorial),
        ]
        call_count = 0

        def mock_create(**kwargs):
            nonlocal call_count
            text = responses_cycle[call_count % len(responses_cycle)]
            call_count += 1
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text=text)]
            # Report 1 million output tokens to blow the spend cap
            mock_msg.usage.input_tokens = 1_000_000
            mock_msg.usage.output_tokens = 1_000_000
            return mock_msg

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = mock_create

        # Patch at the build_unit module level where it imports anthropic
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with pytest.raises(SpendCapExceeded):
                build_unit(
                    curriculum_id="default-2026-g8",
                    unit_id="G8-SCI-001",
                    unit_data=unit_data,
                    lang="en",
                    config=config,
                    force=True,
                )
