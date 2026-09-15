"""
backend/src/student/schemas.py

Pydantic schemas for student dashboard, progress map, and stats endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel

# ── Dashboard ─────────────────────────────────────────────────────────────────


class DashboardSummary(BaseModel):
    units_completed: int
    quizzes_passed: int
    current_streak_days: int
    total_time_minutes: int
    avg_quiz_score: float


class SubjectProgress(BaseModel):
    subject: str
    units_total: int
    units_completed: int
    pct: float
    # None when the student has answered nothing in the subject yet, so the UI
    # can say "not started" rather than show a 0% they did not earn.
    avg_score: float | None = None


class Standing(BaseModel):
    """The student's average beside their grade cohort's.

    Omitted entirely (None on the response) when the cohort is too small to
    aggregate without disclosing an individual's record — see
    `_MIN_COHORT_FOR_STANDING` in service.py.
    """

    you: float
    cohort: float
    cohort_size: int
    grade: int


class NextUnit(BaseModel):
    unit_id: str
    title: str
    subject: str
    estimated_minutes: int


class RecentActivityItem(BaseModel):
    type: str  # "quiz" | "lesson"
    unit_id: str
    title: str
    score: int | None = None
    at: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    subject_progress: list[SubjectProgress]
    next_unit: NextUnit | None
    standing: Standing | None = None
    recent_activity: list[RecentActivityItem]


# ── Progress map ──────────────────────────────────────────────────────────────


class UnitProgressItem(BaseModel):
    unit_id: str
    title: str
    status: str  # not_started | in_progress | needs_retry | completed
    best_score: int | None
    attempts: int
    last_attempt_at: str | None


class SubjectProgressMap(BaseModel):
    subject: str
    units_total: int
    units_completed: int
    units: list[UnitProgressItem]


class ProgressMapResponse(BaseModel):
    curriculum_id: str
    pending_count: int
    needs_retry_count: int
    subjects: list[SubjectProgressMap]


# ── Stats ─────────────────────────────────────────────────────────────────────


class DailyActivity(BaseModel):
    date: str
    lessons: int
    quizzes: int
    minutes: int


class StatsResponse(BaseModel):
    period: str
    lessons_viewed: int
    quizzes_completed: int
    quizzes_passed: int
    avg_quiz_score: float
    total_time_minutes: int
    audio_plays: int
    streak_current_days: int
    streak_longest_days: int
    daily_activity: list[DailyActivity]
