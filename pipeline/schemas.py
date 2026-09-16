"""
pipeline/schemas.py

JSON Schema definitions for validating Claude-generated content.
Uses jsonschema for validation.

Schemas:
  LESSON_SCHEMA       — lesson JSON
  QUIZ_SCHEMA         — quiz set JSON (enforces exactly 8 questions)
  TUTORIAL_SCHEMA     — tutorial JSON
  EXPERIMENT_SCHEMA   — lab experiment JSON (for has_lab units)
  SCENARIO_SCHEMA     — scenario-based compliance training JSON
  META_SCHEMA         — meta.json per unit

Functions:
  validate_lesson(data)      → raises jsonschema.ValidationError on failure
  validate_quiz(data)        → raises jsonschema.ValidationError on failure
  validate_tutorial(data)    → raises jsonschema.ValidationError on failure
  validate_experiment(data)  → raises jsonschema.ValidationError on failure
  validate_scenario(data)    → raises jsonschema.ValidationError on failure
  validate_meta(data)        → raises jsonschema.ValidationError on failure
"""

from __future__ import annotations

import jsonschema

# ── Shared sub-schemas ────────────────────────────────────────────────────────

_GENERATED_AT = {"type": "string"}
_MODEL = {"type": "string", "minLength": 1}
_CONTENT_VERSION = {"type": "integer", "minimum": 1}

# ── Lesson schema ─────────────────────────────────────────────────────────────

_LESSON_SECTION_SCHEMA = {
    "type": "object",
    "required": ["heading", "body"],
    "properties": {
        "heading": {"type": "string", "minLength": 1},
        "body": {"type": "string", "minLength": 10},
    },
}

LESSON_SCHEMA: dict = {
    "type": "object",
    "required": [
        "unit_id", "subject", "topic", "synopsis",
        "sections", "key_points",
        "learning_objectives", "reading_level", "estimated_duration_minutes",
        "language", "generated_at", "model", "content_version",
    ],
    "additionalProperties": True,
    "properties": {
        "unit_id": {"type": "string", "minLength": 1},
        "subject": {"type": "string", "minLength": 1},
        "topic": {"type": "string", "minLength": 1},
        "synopsis": {"type": "string", "minLength": 10},
        "sections": {
            "type": "array",
            "items": _LESSON_SECTION_SCHEMA,
            "minItems": 1,
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        # key_concepts is the old field name — kept as optional for backward compat
        "key_concepts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "learning_objectives": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "reading_level": {"type": "string", "minLength": 1},
        "estimated_duration_minutes": {"type": "integer", "minimum": 1},
        "language": {"type": "string", "minLength": 2},
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
    },
}

# ── Quiz schema ───────────────────────────────────────────────────────────────

_OPTION_SCHEMA = {
    "type": "object",
    "required": ["option_id", "text"],
    "properties": {
        "option_id": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "text": {"type": "string", "minLength": 1},
    },
}

_QUESTION_SCHEMA = {
    "type": "object",
    "required": [
        "question_id", "question_text", "question_type",
        "options", "correct_option", "explanation", "difficulty",
    ],
    "properties": {
        "question_id": {"type": "string", "minLength": 1},
        "question_text": {"type": "string", "minLength": 5},
        "question_type": {"type": "string", "enum": ["multiple_choice"]},
        "options": {
            "type": "array",
            "items": _OPTION_SCHEMA,
            "minItems": 4,
            "maxItems": 4,
        },
        "correct_option": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "explanation": {"type": "string", "minLength": 5},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
    },
}

QUIZ_SCHEMA: dict = {
    "type": "object",
    "required": [
        "unit_id", "set_number", "language", "questions",
        "total_questions", "estimated_duration_minutes", "passing_score",
        "generated_at", "model", "content_version",
    ],
    "additionalProperties": True,
    "properties": {
        "unit_id": {"type": "string", "minLength": 1},
        "set_number": {"type": "integer", "minimum": 1},
        "language": {"type": "string", "minLength": 2},
        "questions": {
            "type": "array",
            "items": _QUESTION_SCHEMA,
            "minItems": 8,
            "maxItems": 8,
        },
        "total_questions": {"type": "integer", "enum": [8]},
        "estimated_duration_minutes": {"type": "integer", "minimum": 1},
        "passing_score": {"type": "integer", "minimum": 1},
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
    },
}

# ── Tutorial schema ───────────────────────────────────────────────────────────

_SECTION_SCHEMA = {
    "type": "object",
    "required": ["section_id", "title", "content", "examples", "practice_question"],
    "properties": {
        "section_id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "content": {"type": "string", "minLength": 10},
        "examples": {"type": "array", "items": {"type": "string"}},
        "practice_question": {"type": "string", "minLength": 5},
    },
}

TUTORIAL_SCHEMA: dict = {
    "type": "object",
    "required": [
        "unit_id", "language", "title", "sections",
        "common_mistakes", "generated_at", "model", "content_version",
    ],
    "additionalProperties": True,
    "properties": {
        "unit_id": {"type": "string", "minLength": 1},
        "language": {"type": "string", "minLength": 2},
        "title": {"type": "string", "minLength": 1},
        "sections": {
            "type": "array",
            "items": _SECTION_SCHEMA,
            "minItems": 1,
        },
        "common_mistakes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
    },
}

# ── Experiment schema ─────────────────────────────────────────────────────────

_STEP_SCHEMA = {
    "type": "object",
    "required": ["step_number", "instruction", "expected_observation"],
    "properties": {
        "step_number": {"type": "integer", "minimum": 1},
        "instruction": {"type": "string", "minLength": 5},
        "expected_observation": {"type": "string", "minLength": 5},
    },
}

_EXP_QUESTION_SCHEMA = {
    "type": "object",
    "required": ["question", "answer"],
    "properties": {
        "question": {"type": "string", "minLength": 5},
        "answer": {"type": "string", "minLength": 1},
    },
}

EXPERIMENT_SCHEMA: dict = {
    "type": "object",
    "required": [
        "unit_id", "language", "experiment_title", "materials",
        "safety_notes", "steps", "questions", "conclusion_prompt",
        "generated_at", "model", "content_version",
    ],
    "additionalProperties": True,
    "properties": {
        "unit_id": {"type": "string", "minLength": 1},
        "language": {"type": "string", "minLength": 2},
        "experiment_title": {"type": "string", "minLength": 1},
        "materials": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "safety_notes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "steps": {
            "type": "array",
            "items": _STEP_SCHEMA,
            "minItems": 1,
        },
        "questions": {
            "type": "array",
            "items": _EXP_QUESTION_SCHEMA,
            "minItems": 1,
        },
        "conclusion_prompt": {"type": "string", "minLength": 10},
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
    },
}

# ── Scenario schema ───────────────────────────────────────────────────────────

_CHARACTER_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "role_label"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "org": {"type": "string"},
        "role_label": {"type": "string", "minLength": 1},
    },
}

_DIALOG_TURN_SCHEMA = {
    "type": "object",
    "required": ["speaker", "text"],
    "properties": {
        "speaker": {"type": "string", "minLength": 1},
        "text": {"type": "string", "minLength": 1},
    },
}

_SCENARIO_QUIZ_SCHEMA = {
    "type": "object",
    "required": ["question", "format", "correct_answer", "explanation"],
    "properties": {
        "question": {"type": "string", "minLength": 5},
        "format": {"type": "string", "enum": ["true_false", "multiple_choice"]},
        "correct_answer": {},
        "explanation": {"type": "string", "minLength": 10},
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
        },
    },
}

SCENARIO_SCHEMA: dict = {
    "type": "object",
    "required": [
        "scenario_id", "title", "domain", "characters", "dialog", "quiz",
        "language", "generated_at", "model", "content_version",
    ],
    "additionalProperties": True,
    "properties": {
        "scenario_id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "domain": {"type": "string", "minLength": 1},
        "content_source": {
            "type": "string",
            "enum": ["ai_generated", "human_authored", "ai_assisted"],
        },
        "characters": {
            "type": "array",
            "items": _CHARACTER_SCHEMA,
            "minItems": 2,
        },
        "dialog": {
            "type": "array",
            "items": _DIALOG_TURN_SCHEMA,
            "minItems": 2,
        },
        "quiz": _SCENARIO_QUIZ_SCHEMA,
        "language": {"type": "string", "minLength": 2},
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
    },
}

# ── Meta schema ───────────────────────────────────────────────────────────────

META_SCHEMA: dict = {
    "type": "object",
    "required": [
        "unit_id", "curriculum_id", "generated_at", "model",
        "content_version", "langs_built",
    ],
    "additionalProperties": True,
    "properties": {
        "unit_id": {"type": "string", "minLength": 1},
        "curriculum_id": {"type": "string", "minLength": 1},
        "generated_at": _GENERATED_AT,
        "model": _MODEL,
        "content_version": _CONTENT_VERSION,
        "langs_built": {
            "type": "array",
            "items": {"type": "string", "minLength": 2},
        },
        "alex_warnings_count": {"type": "integer", "minimum": 0},
    },
}


# ── Validation helpers ────────────────────────────────────────────────────────

def validate_lesson(data: dict) -> None:
    """Validate a lesson dict against LESSON_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=LESSON_SCHEMA)


def validate_quiz(data: dict) -> None:
    """Validate a quiz dict against QUIZ_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=QUIZ_SCHEMA)
    _reject_indistinguishable_options(data)


def _reject_indistinguishable_options(data: dict) -> None:
    """Refuse a question whose options cannot be told apart on screen (#754).

    A sweep of the demo store found 9 questions in 6,960 shipping the correct
    answer twice -- e.g. `['USD 35,000', 'USD 35,000', 'USD 30,000', ...]` --
    every one of them with the correct option at index 0 and a copy of it later
    in the list. A student who knows the answer then has a 1-in-2 chance of
    clicking the copy and being marked wrong, which is what #754 reported.

    `uniqueItems` on the options array cannot express this: the option objects
    differ by `option_id`, so a duplicate TEXT is unique as an object.

    Raised as a ValidationError because `build_grade` retries that up to 3x and
    then fails the unit -- so a bad draw is regenerated rather than written.

    Whitespace is collapsed (HTML collapses it) but case is NOT folded: the same
    sweep found 4 perfectly answerable questions whose options differ only in
    case -- 'Bb' vs 'bB' (genotypes), 'Running' vs 'running' (Python is
    case-sensitive), '2gH' vs '2gh' (different quantities). This must stay in
    step with `_parse_quiz_answer_key`, which accepts by the same rule.
    """
    for question in data.get("questions", []):
        seen: dict[str, str] = {}
        for option in question.get("options", []):
            text = " ".join((option.get("text") or "").split())
            if not text:
                continue
            if text in seen:
                raise jsonschema.ValidationError(
                    f"question {question.get('question_id')!r}: options "
                    f"{seen[text]!r} and {option.get('option_id')!r} have the same "
                    f"text {text!r}; a student cannot choose between them"
                )
            seen[text] = option.get("option_id")


def validate_tutorial(data: dict) -> None:
    """Validate a tutorial dict against TUTORIAL_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=TUTORIAL_SCHEMA)


def validate_experiment(data: dict) -> None:
    """Validate an experiment dict against EXPERIMENT_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=EXPERIMENT_SCHEMA)


def validate_scenario(data: dict) -> None:
    """Validate a scenario dict against SCENARIO_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=SCENARIO_SCHEMA)


def validate_meta(data: dict) -> None:
    """Validate a meta dict against META_SCHEMA. Raises jsonschema.ValidationError on failure."""
    jsonschema.validate(instance=data, schema=META_SCHEMA)
