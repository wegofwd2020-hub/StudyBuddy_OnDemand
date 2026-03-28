"""
backend/src/analytics/schemas.py

Pydantic schemas for lesson analytics endpoints (Phase 4 + Phase 10).
"""

from __future__ import annotations

from pydantic import BaseModel


class LessonStartRequest(BaseModel):
    unit_id: str
    curriculum_id: str


class LessonStartResponse(BaseModel):
    view_id: str


class LessonEndRequest(BaseModel):
    view_id: str
    duration_s: int
    audio_played: bool = False
    experiment_viewed: bool = False


class LessonEndResponse(BaseModel):
    view_id: str
    duration_s: int


# ── Phase 10: student + class analytics ───────────────────────────────────────

class PerUnitStudentMetric(BaseModel):
    unit_id: str
    subject: str
    quiz_attempts: int
    best_score_pct: float | None = None
    passed: bool
    total_time_minutes: float
    lessons_viewed: int


class ImprovementPoint(BaseModel):
    unit_id: str
    attempt_1_score: int | None = None
    best_retry_score: int | None = None
    improvement_pct: float | None = None


class StudentMetricsResponse(BaseModel):
    units_attempted: int
    units_completed: int
    units_passed_first_attempt: int
    overall_avg_score_pct: float
    quizzes_completed: int
    total_time_minutes: float
    lessons_viewed: int
    audio_plays: int
    per_unit: list[PerUnitStudentMetric]
    improvement_trajectory: list[ImprovementPoint]


class PerUnitClassMetric(BaseModel):
    unit_id: str
    subject: str
    students_with_lesson_view: int
    lesson_view_pct: float
    total_quiz_attempts: int
    unique_students_attempted: int
    first_attempt_pass_rate_pct: float
    mean_score_pct: float
    mean_attempts_to_pass: float
    struggle_flag: bool


class ClassMetricsResponse(BaseModel):
    school_id: str
    enrolled_students: int
    metrics_per_unit: list[PerUnitClassMetric]
