"""
backend/src/reports/schemas.py

Pydantic schemas for Phase 11 teacher reporting dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class AttemptDistribution(BaseModel):
    one: int = 0
    two: int = 0
    three: int = 0
    four_plus: int = 0


# ── Report 1: Class Overview ──────────────────────────────────────────────────

class OverviewReport(BaseModel):
    school_id: str
    period: str
    enrolled_students: int
    active_students_period: int
    active_pct: float
    lessons_viewed: int
    quiz_attempts: int
    first_attempt_pass_rate_pct: float
    audio_play_rate_pct: float
    units_with_struggles: List[str]
    units_no_activity: List[str]
    unreviewed_feedback_count: int


# ── Report 2: Unit Performance ────────────────────────────────────────────────

class RecentFeedbackItem(BaseModel):
    feedback_id: str
    category: str
    rating: Optional[int] = None
    message: str
    submitted_at: datetime


class UnitReport(BaseModel):
    school_id: str
    unit_id: str
    period: str
    students_viewed_lesson: int
    lesson_view_pct: float
    avg_lesson_duration_s: float
    audio_play_rate_pct: float
    experiment_view_pct: Optional[float] = None
    students_attempted_quiz: int
    quiz_attempt_pct: float
    first_attempt_pass_rate_pct: float
    avg_score_pct: float
    avg_attempts_to_pass: float
    attempt_distribution: AttemptDistribution
    struggle_flag: bool
    feedback_count: int
    avg_rating: Optional[float] = None
    feedback_summary: List[RecentFeedbackItem]


# ── Report 3: Student Progress ────────────────────────────────────────────────

class PerUnitStudentReportItem(BaseModel):
    unit_id: str
    unit_name: Optional[str] = None
    subject: str
    lesson_viewed: bool
    quiz_attempts: int
    best_score: Optional[float] = None
    passed: bool
    avg_duration_s: float


class StudentReport(BaseModel):
    school_id: str
    student_id: str
    student_name: str
    grade: int
    last_active: Optional[datetime] = None
    units_completed: int
    units_in_progress: int
    first_attempt_pass_rate_pct: float
    overall_avg_score_pct: float
    total_time_spent_s: int
    per_unit: List[PerUnitStudentReportItem]
    strongest_subject: Optional[str] = None
    needs_attention_subject: Optional[str] = None


# ── Report 4: Curriculum Health ───────────────────────────────────────────────

class CurriculumHealthUnit(BaseModel):
    unit_id: str
    unit_name: Optional[str] = None
    subject: str
    health_tier: str  # healthy | watch | struggling | no_activity
    first_attempt_pass_rate_pct: float
    avg_attempts_to_pass: float
    avg_score_pct: float
    feedback_count: int
    avg_rating: Optional[float] = None
    recommended_action: str  # none | review_content | add_class_time | report_to_admin


class CurriculumHealthReport(BaseModel):
    school_id: str
    total_units: int
    healthy_count: int
    watch_count: int
    struggling_count: int
    no_activity_count: int
    units: List[CurriculumHealthUnit]


# ── Report 5: Feedback Report ─────────────────────────────────────────────────

class FeedbackReportItem(BaseModel):
    feedback_id: str
    category: str
    rating: Optional[int] = None
    message: str
    submitted_at: datetime
    reviewed: bool


class FeedbackByUnit(BaseModel):
    unit_id: str
    unit_name: Optional[str] = None
    feedback_count: int
    category_breakdown: Dict[str, int]  # content/ux/general → count
    trending: bool  # > 3 items in last 7 days
    feedback_items: List[FeedbackReportItem]


class FeedbackReport(BaseModel):
    school_id: str
    total_feedback_count: int
    unreviewed_count: int
    avg_rating_overall: Optional[float] = None
    by_unit: List[FeedbackByUnit]


# ── Report 6: Trends ──────────────────────────────────────────────────────────

class TrendsWeek(BaseModel):
    week_start: str  # YYYY-MM-DD
    active_students: int
    lessons_viewed: int
    quiz_attempts: int
    avg_score_pct: float
    first_attempt_pass_rate_pct: float


class TrendsReport(BaseModel):
    school_id: str
    period: str
    weeks: List[TrendsWeek]


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(overview|unit|student|curriculum-health|feedback|trends)$")
    filters: Dict[str, Any] = {}


class ExportResponse(BaseModel):
    export_id: str
    download_url: str
    status: str  # queued | ready


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertItem(BaseModel):
    alert_id: str
    alert_type: str
    school_id: str
    details: Dict[str, Any]
    triggered_at: datetime
    acknowledged: bool


class AlertListResponse(BaseModel):
    alerts: List[AlertItem]


class AlertSettings(BaseModel):
    pass_rate_threshold: float = Field(50.0, ge=0, le=100)
    feedback_count_threshold: int = Field(3, ge=1)
    inactive_days_threshold: int = Field(14, ge=1)
    score_drop_threshold: float = Field(10.0, ge=0, le=100)
    new_feedback_immediate: bool = True


class AlertSettingsResponse(BaseModel):
    school_id: str
    pass_rate_threshold: float
    feedback_count_threshold: int
    inactive_days_threshold: int
    score_drop_threshold: float
    new_feedback_immediate: bool
    updated_at: datetime


# ── Digest ────────────────────────────────────────────────────────────────────

class DigestSubscribeRequest(BaseModel):
    email: str
    timezone: str = "UTC"
    enabled: bool = True


class DigestSubscribeResponse(BaseModel):
    subscription_id: str
    school_id: str
    email: str
    timezone: str
    enabled: bool


# ── Refresh ───────────────────────────────────────────────────────────────────

class RefreshResponse(BaseModel):
    refreshed_at: datetime
    views_refreshed: List[str]
