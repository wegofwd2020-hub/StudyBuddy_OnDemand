"""
backend/src/reports/schemas.py

Pydantic schemas for Phase 11 teacher reporting dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
    units_with_struggles: list[str]
    units_no_activity: list[str]
    unreviewed_feedback_count: int


# ── Report 2: Unit Performance ────────────────────────────────────────────────


class RecentFeedbackItem(BaseModel):
    feedback_id: str
    category: str
    rating: int | None = None
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
    experiment_view_pct: float | None = None
    students_attempted_quiz: int
    quiz_attempt_pct: float
    first_attempt_pass_rate_pct: float
    avg_score_pct: float
    avg_attempts_to_pass: float
    attempt_distribution: AttemptDistribution
    struggle_flag: bool
    feedback_count: int
    avg_rating: float | None = None
    feedback_summary: list[RecentFeedbackItem]


# ── Report 3: Student Progress ────────────────────────────────────────────────


class PerUnitStudentReportItem(BaseModel):
    unit_id: str
    unit_name: str | None = None
    subject: str
    lesson_viewed: bool
    quiz_attempts: int
    best_score: float | None = None
    passed: bool
    avg_duration_s: float


class StudentReport(BaseModel):
    school_id: str
    student_id: str
    student_name: str
    grade: int
    last_active: datetime | None = None
    units_completed: int
    units_in_progress: int
    first_attempt_pass_rate_pct: float
    overall_avg_score_pct: float
    total_time_spent_s: int
    per_unit: list[PerUnitStudentReportItem]
    strongest_subject: str | None = None
    needs_attention_subject: str | None = None


# ── Report 4: Curriculum Health ───────────────────────────────────────────────


class CurriculumHealthUnit(BaseModel):
    unit_id: str
    unit_name: str | None = None
    subject: str
    health_tier: str  # healthy | watch | struggling | no_activity
    first_attempt_pass_rate_pct: float
    avg_attempts_to_pass: float
    avg_score_pct: float
    feedback_count: int
    avg_rating: float | None = None
    recommended_action: str  # none | review_content | add_class_time | report_to_admin


class CurriculumHealthReport(BaseModel):
    school_id: str
    total_units: int
    healthy_count: int
    watch_count: int
    struggling_count: int
    no_activity_count: int
    units: list[CurriculumHealthUnit]


# ── Report 5: Feedback Report ─────────────────────────────────────────────────


class FeedbackReportItem(BaseModel):
    feedback_id: str
    category: str
    rating: int | None = None
    message: str
    submitted_at: datetime
    reviewed: bool


class FeedbackByUnit(BaseModel):
    unit_id: str
    unit_name: str | None = None
    feedback_count: int
    category_breakdown: dict[str, int]  # content/ux/general → count
    trending: bool  # > 3 items in last 7 days
    feedback_items: list[FeedbackReportItem]


class FeedbackReport(BaseModel):
    school_id: str
    total_feedback_count: int
    unreviewed_count: int
    avg_rating_overall: float | None = None
    by_unit: list[FeedbackByUnit]


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
    weeks: list[TrendsWeek]


# ── Export ────────────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    report_type: str = Field(
        ..., pattern="^(overview|unit|student|curriculum-health|feedback|trends)$"
    )
    filters: dict[str, Any] = {}


class ExportResponse(BaseModel):
    export_id: str
    download_url: str
    status: str  # queued | ready


# ── Alerts ────────────────────────────────────────────────────────────────────


class AlertItem(BaseModel):
    alert_id: str
    alert_type: str
    school_id: str
    details: dict[str, Any]
    triggered_at: datetime
    acknowledged: bool


class AlertListResponse(BaseModel):
    alerts: list[AlertItem]


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
    views_refreshed: list[str]


# ── At-Risk Student Action Queue (#79) ───────────────────────────────────────


class AtRiskReason(BaseModel):
    inactive: bool = False
    low_pass_rate: bool = False


class AtRiskStudent(BaseModel):
    student_id: str
    student_name: str
    grade: int
    last_active: datetime | None = None
    inactive_days: int | None = None
    pass_rate_pct: float | None = None
    units_completed: int
    total_units: int
    risk_reasons: AtRiskReason
    is_seen: bool = False
    seen_at: datetime | None = None


class AtRiskListResponse(BaseModel):
    school_id: str
    inactive_days_threshold: int
    pass_rate_threshold: float
    students: list[AtRiskStudent]
    total: int


class MarkSeenResponse(BaseModel):
    school_id: str
    student_id: str
    seen: bool
    seen_at: datetime | None = None


class SendReminderResponse(BaseModel):
    school_id: str
    student_id: str
    queued: bool
