"""
backend/src/progress/schemas.py

Pydantic schemas for progress tracking endpoints.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    unit_id: str = Field(..., min_length=1, max_length=64)
    curriculum_id: str = Field(..., min_length=1, max_length=64)


class RecordAnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=128)
    student_answer: int
    correct_answer: int
    correct: bool
    ms_taken: int = Field(ge=0)
    event_id: Optional[str] = Field(None, max_length=64)  # offline dedup key


class EndSessionRequest(BaseModel):
    score: int = Field(ge=0)
    total_questions: int = Field(ge=1)


# ── Response schemas ──────────────────────────────────────────────────────────

class StartSessionResponse(BaseModel):
    session_id: str
    unit_id: str
    curriculum_id: str
    attempt_number: int
    started_at: str


class RecordAnswerResponse(BaseModel):
    answer_id: str
    correct: bool


class EndSessionResponse(BaseModel):
    session_id: str
    score: int
    total_questions: int
    passed: bool
    attempt_number: int
    ended_at: str


class ProgressAnswerRecord(BaseModel):
    answer_id: str
    question_id: str
    student_answer: Optional[int]
    correct_answer: Optional[int]
    correct: Optional[bool]
    ms_taken: Optional[int]
    recorded_at: str


class SessionRecord(BaseModel):
    session_id: str
    unit_id: str
    curriculum_id: str
    grade: int
    subject: str
    started_at: str
    ended_at: Optional[str]
    score: Optional[int]
    total_questions: Optional[int]
    completed: bool
    passed: Optional[bool]
    attempt_number: int
    answers: list[ProgressAnswerRecord] = []


class ProgressHistoryResponse(BaseModel):
    student_id: str
    sessions: list[SessionRecord]
    total: int
