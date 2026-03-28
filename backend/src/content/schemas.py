"""
backend/src/content/schemas.py

Pydantic response/request models for the Content Service.
"""

from __future__ import annotations

from pydantic import BaseModel

# ── Lesson ────────────────────────────────────────────────────────────────────

class LessonSection(BaseModel):
    heading: str
    body: str


class LessonResponse(BaseModel):
    unit_id: str
    title: str
    grade: int
    subject: str
    lang: str
    sections: list[LessonSection]
    key_points: list[str]
    has_audio: bool = False
    # Pipeline metadata (optional — not rendered by the frontend)
    generated_at: str | None = None
    model: str | None = None
    content_version: int | None = None


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuizOption(BaseModel):
    option_id: str
    text: str


class QuizQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    options: list[QuizOption]
    correct_option: str
    explanation: str
    difficulty: str


class QuizResponse(BaseModel):
    unit_id: str
    set_number: int
    language: str
    questions: list[QuizQuestion]
    total_questions: int
    estimated_duration_minutes: int
    passing_score: int
    generated_at: str
    model: str
    content_version: int


# ── Tutorial ──────────────────────────────────────────────────────────────────

class TutorialSection(BaseModel):
    section_id: str
    title: str
    content: str
    examples: list[str]
    practice_question: str


class TutorialResponse(BaseModel):
    unit_id: str
    language: str
    title: str
    sections: list[TutorialSection]
    common_mistakes: list[str]
    generated_at: str
    model: str
    content_version: int


# ── Experiment ────────────────────────────────────────────────────────────────

class ExperimentStep(BaseModel):
    step_number: int
    instruction: str
    expected_observation: str


class ExperimentQuestion(BaseModel):
    question: str
    answer: str


class ExperimentResponse(BaseModel):
    unit_id: str
    language: str
    experiment_title: str
    materials: list[str]
    safety_notes: list[str]
    steps: list[ExperimentStep]
    questions: list[ExperimentQuestion]
    conclusion_prompt: str
    generated_at: str
    model: str
    content_version: int


# ── Audio ─────────────────────────────────────────────────────────────────────

class AudioUrlResponse(BaseModel):
    url: str
    expires_in: int


# ── Report / Feedback ─────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    category: str  # incorrect | offensive | unclear | other
    message: str | None = None


class FeedbackRequest(BaseModel):
    content_type: str
    start_offset: int | None = None
    end_offset: int | None = None
    marked_text: str | None = None
    feedback_text: str


# ── App version ───────────────────────────────────────────────────────────────

class AppVersionResponse(BaseModel):
    min_version: str
    latest_version: str
