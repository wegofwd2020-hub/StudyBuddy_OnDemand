"""
backend/src/admin/schemas.py

Pydantic request/response schemas for all Phase 7 admin endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Review queue ──────────────────────────────────────────────────────────────


class ReviewQueueItem(BaseModel):
    version_id: str
    curriculum_id: str
    subject: str
    subject_name: str | None = None
    version_number: int
    status: str
    alex_warnings_count: int
    generated_at: datetime
    published_at: datetime | None = None
    has_content: bool = False
    provider: str | None = None  # Epic 1 — which LLM generated this version


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int


class ReviewUnitItem(BaseModel):
    unit_id: str
    title: str
    sort_order: int


class ReviewHistoryItem(BaseModel):
    review_id: str
    action: str
    notes: str | None = None
    reviewed_at: datetime
    reviewer_email: str | None = None


class ReviewAnnotationItem(BaseModel):
    annotation_id: str
    unit_id: str
    content_type: str
    annotation_text: str
    created_at: datetime
    reviewer_email: str | None = None


class ReviewDetailResponse(ReviewQueueItem):
    units: list[ReviewUnitItem]
    review_history: list[ReviewHistoryItem]
    annotations: list[ReviewAnnotationItem]


# ── Review session ────────────────────────────────────────────────────────────


class OpenReviewRequest(BaseModel):
    notes: str | None = None


class OpenReviewResponse(BaseModel):
    review_id: str
    version_id: str
    action: str
    reviewed_at: datetime


class AnnotateRequest(BaseModel):
    unit_id: str
    content_type: str
    marked_text: str | None = None
    annotation_text: str
    start_offset: int | None = None
    end_offset: int | None = None


class AnnotateResponse(BaseModel):
    annotation_id: str
    version_id: str
    unit_id: str
    content_type: str
    annotation_text: str
    created_at: datetime


# ── Rating ────────────────────────────────────────────────────────────────────


class RateRequest(BaseModel):
    language_rating: int = Field(..., ge=1, le=5)
    content_rating: int = Field(..., ge=1, le=5)
    notes: str | None = None


class RateResponse(BaseModel):
    review_id: str
    version_id: str
    language_rating: int
    content_rating: int


# ── Approve / reject ──────────────────────────────────────────────────────────


class ApproveRequest(BaseModel):
    notes: str | None = None


class ApproveResponse(BaseModel):
    version_id: str
    status: str


class RejectRequest(BaseModel):
    notes: str | None = None
    regenerate: bool = False


class RejectResponse(BaseModel):
    version_id: str
    status: str
    regenerating: bool


# ── Publish / rollback ────────────────────────────────────────────────────────


class PublishResponse(BaseModel):
    version_id: str
    status: str
    published_at: datetime


class RollbackResponse(BaseModel):
    version_id: str
    status: str


# ── Content block ─────────────────────────────────────────────────────────────


class BlockRequest(BaseModel):
    curriculum_id: str
    unit_id: str
    content_type: str
    reason: str | None = None


class BlockVersionRequest(BaseModel):
    unit_id: str
    content_type: str
    reason: str | None = None


class BlockResponse(BaseModel):
    block_id: str
    curriculum_id: str
    unit_id: str
    content_type: str
    blocked_at: datetime


class UnblockResponse(BaseModel):
    status: str


# ── Student feedback ──────────────────────────────────────────────────────────


class FeedbackItem(BaseModel):
    feedback_id: str
    student_id: str
    curriculum_id: str
    content_type: str
    category: str
    message: str | None = None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: list[FeedbackItem]
    total: int


class FeedbackReportItem(BaseModel):
    unit_id: str
    curriculum_id: str
    report_count: int
    incorrect_count: int
    confusing_count: int
    inappropriate_count: int
    other_count: int


class FeedbackReportResponse(BaseModel):
    items: list[FeedbackReportItem]
    threshold: int


# ── Subscription analytics ────────────────────────────────────────────────────


class SubscriptionAnalyticsResponse(BaseModel):
    by_plan: dict  # plan → {active, new_this_month, cancelled_this_month}
    total_active: int
    mrr_usd: str  # string per Rule 1 — money is never a float
    new_this_month: int
    cancelled_this_month: int
    churn_rate: float  # cancelled / (active + cancelled) for the month


# ── Struggle analytics ────────────────────────────────────────────────────────


class StruggleItem(BaseModel):
    unit_id: str
    curriculum_id: str
    total_attempts: int
    mean_attempts: float
    pass_rate: float  # 0.0–1.0


class StruggleResponse(BaseModel):
    items: list[StruggleItem]


# ── Pipeline status ───────────────────────────────────────────────────────────


class PipelineStatusResponse(BaseModel):
    last_run_at: datetime | None
    total_versions: int
    ready_for_review: int
    approved: int
    published: int
    rejected: int
    pending: int


# ── Dictionary ────────────────────────────────────────────────────────────────


class DictionaryResponse(BaseModel):
    word: str
    definitions: list[str]
    synonyms: list[str]
    antonyms: list[str]


# ── Admin pipeline ────────────────────────────────────────────────────────────


class UploadGradeJsonResponse(BaseModel):
    curriculum_id: str
    grade: int
    unit_count: int
    subject_count: int


class AdminPipelineTriggerRequest(BaseModel):
    grade: int
    langs: str = "en"
    force: bool = False
    year: int = 2026
    # Optional stream suffix — see migration 0044 + admin upload-grade endpoint.
    # When present, the task builds curriculum_id `default-{year}-g{grade}-{stream}`
    # reading from `data/grade{N}_{stream}.json`. When absent, legacy behaviour.
    stream: str | None = None


class AdminPipelineTriggerResponse(BaseModel):
    job_id: str
    status: str
    curriculum_id: str


# ── Batch approve ─────────────────────────────────────────────────────────────


class BatchApproveRequest(BaseModel):
    curriculum_id: str
    notes: str | None = None


class SkippedVersion(BaseModel):
    version_id: str
    reason: str


class BatchApproveResponse(BaseModel):
    approved_count: int
    version_ids: list[str]
    skipped: list[SkippedVersion]


# ── Assign / unassign reviewer ────────────────────────────────────────────────


class AssignRequest(BaseModel):
    admin_id: str | None = None  # None to unassign


class AssignResponse(BaseModel):
    version_id: str
    assigned_to_admin_id: str | None = None
    assigned_to_email: str | None = None
    assigned_at: datetime | None = None


# ── Admin user management ─────────────────────────────────────────────────────


class AdminUserItem(BaseModel):
    admin_user_id: str
    email: str
    role: str


class AdminUsersResponse(BaseModel):
    users: list[AdminUserItem]


# ── Unit content viewer ───────────────────────────────────────────────────────


class UnitContentMetaResponse(BaseModel):
    unit_id: str
    title: str
    curriculum_id: str
    lang: str
    available_types: list[str]
    alex_warnings_count: int = 0
    alex_warnings_by_type: dict[str, int] = {}


class UnitContentFileResponse(BaseModel):
    unit_id: str
    curriculum_id: str
    content_type: str
    lang: str
    data: dict


# ── Alex warning acknowledgements ─────────────────────────────────────────────


class WarningDetail(BaseModel):
    warning_index: int
    unit_id: str
    content_type: str
    message: str
    line: int
    column: int
    acknowledged: bool = False
    is_false_positive: bool = False
    acknowledged_by_email: str | None = None
    acknowledged_at: datetime | None = None


class VersionWarningsResponse(BaseModel):
    version_id: str
    total_count: int
    unacknowledged_count: int
    warnings: list[WarningDetail]


class AcknowledgeWarningRequest(BaseModel):
    is_false_positive: bool = False


class AcknowledgeWarningResponse(BaseModel):
    ack_id: str
    version_id: str
    unit_id: str
    content_type: str
    warning_index: int
    is_false_positive: bool
    acknowledged_by_email: str
    acknowledged_at: datetime
