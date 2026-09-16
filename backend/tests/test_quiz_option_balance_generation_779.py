"""
tests/test_quiz_option_balance_generation_779.py

Both quiz generation paths store balanced options (#779): the content pipeline
(`build_unit`, also used by `build_grade`) and the Authoring Studio
(`authoring_generation.generate_one`). The fixtures return every question with
the correct answer at A, which is the reported skew in its worst form.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from src.admin import authoring_generation as gen
from tests.test_multi_provider_pipeline import (
    _VALID_LESSON,
    _VALID_QUIZ,
    _VALID_TUTORIAL,
    _make_config,
)


def _correct_text(q: dict) -> str:
    return next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"])


def _assert_balanced_and_still_correct(quiz: dict) -> None:
    letters = {q["correct_option"] for q in quiz["questions"]}
    # 8 distinct stems, all starting at A: staying all-A would mean nothing ran.
    assert letters != {"A"}, letters
    for q in quiz["questions"]:
        assert _correct_text(q) == "Mass divided by volume"


def test_build_unit_writes_balanced_quiz_sets():
    from pipeline.build_unit import build_unit
    from pipeline.providers.base import LLMProvider

    provider = MagicMock(spec=LLMProvider)
    provider.provider_id = "anthropic"
    provider.model = "claude-sonnet-4-6"
    responses = [
        json.dumps(_VALID_LESSON),
        json.dumps({**_VALID_QUIZ, "set_number": 1}),
        json.dumps({**_VALID_QUIZ, "set_number": 2}),
        json.dumps({**_VALID_QUIZ, "set_number": 3}),
        json.dumps(_VALID_TUTORIAL),
    ]
    calls = [0]

    def _generate(prompt: str):
        text = responses[calls[0] % len(responses)]
        calls[0] += 1
        return text, 100, 200

    provider.generate.side_effect = _generate

    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tmpdir)
        with (
            patch("pipeline.build_unit.synthesize_lesson"),
            patch("pipeline.build_unit._upload_unit_to_s3"),
            patch(
                "pipeline.alex_runner.run_alex",
                return_value={"warnings_count": 0, "warnings": []},
            ),
        ):
            result = build_unit(
                curriculum_id="default-2026-g8",
                unit_id="G8-SCI-001",
                unit_data={"title": "Density", "subject": "science", "has_lab": False, "grade": 8},
                lang="en",
                config=config,
                force=True,
                provider_id="anthropic",
                provider=provider,
            )
        assert result["status"] == "ok"

        path = os.path.join(
            tmpdir, "curricula", "default-2026-g8", "G8-SCI-001", "quiz_set_1_en.json"
        )
        with open(path) as f:
            _assert_balanced_and_still_correct(json.load(f))


class _Provider:
    model = "fake-model"

    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, prompt: str) -> tuple[str, int, int]:
        return self.text, 5, 5


def test_authoring_generate_one_returns_a_balanced_quiz():
    body, _ = gen.generate_one(
        _Provider(json.dumps(_VALID_QUIZ)),
        content_type="quiz_set_1",
        unit_id="G8-SCI-001",
        subject="Science",
        topic="Density",
        grade=8,
        lang="en",
    )
    _assert_balanced_and_still_correct(body)


def test_authoring_generate_one_leaves_non_quiz_content_alone():
    lesson = {**_VALID_LESSON}
    body, _ = gen.generate_one(
        _Provider(json.dumps(lesson)),
        content_type="lesson",
        unit_id="G8-SCI-001",
        subject="Science",
        topic="Density",
        grade=8,
        lang="en",
    )
    assert body == lesson
