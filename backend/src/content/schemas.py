"""
backend/src/content/schemas.py

Pydantic response/request models for the Content Service.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


# ── Lesson ────────────────────────────────────────────────────────────────────

class LessonResponse(BaseModel):
    unit_id: str
    subject: str
    topic: str
    synopsis: str
    key_concepts: List[str]
    learning_objectives: List[str]
    reading_level: str
    estimated_duration_minutes: int
    language: str
    generated_at: str
    model: str
    content_version: int


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuizOption(BaseModel):
    option_id: str
    text: str


class QuizQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    options: List[QuizOption]
    correct_option: str
    explanation: str
    difficulty: str


class QuizResponse(BaseModel):
    unit_id: str
    set_number: int
    language: str
    questions: List[QuizQuestion]
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
    examples: List[str]
    practice_question: str


class TutorialResponse(BaseModel):
    unit_id: str
    language: str
    title: str
    sections: List[TutorialSection]
    common_mistakes: List[str]
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
    materials: List[str]
    safety_notes: List[str]
    steps: List[ExperimentStep]
    questions: List[ExperimentQuestion]
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
    message: Optional[str] = None


class FeedbackRequest(BaseModel):
    content_type: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    marked_text: Optional[str] = None
    feedback_text: str


# ── App version ───────────────────────────────────────────────────────────────

class AppVersionResponse(BaseModel):
    min_version: str
    latest_version: str
