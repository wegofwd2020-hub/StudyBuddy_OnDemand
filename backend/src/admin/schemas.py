"""
backend/src/admin/schemas.py

Pydantic request/response schemas for all Phase 7 admin endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Review queue ──────────────────────────────────────────────────────────────

class ReviewQueueItem(BaseModel):
    version_id: str
    curriculum_id: str
    subject: str
    version_number: int
    status: str
    alex_warnings_count: int
    generated_at: datetime
    published_at: Optional[datetime] = None


class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem]
    total: int


# ── Review session ────────────────────────────────────────────────────────────

class OpenReviewRequest(BaseModel):
    notes: Optional[str] = None


class OpenReviewResponse(BaseModel):
    review_id: str
    version_id: str
    action: str
    reviewed_at: datetime


class AnnotateRequest(BaseModel):
    unit_id: str
    content_type: str
    marked_text: Optional[str] = None
    annotation_text: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


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
    notes: Optional[str] = None


class RateResponse(BaseModel):
    review_id: str
    version_id: str
    language_rating: int
    content_rating: int


# ── Approve / reject ──────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    notes: Optional[str] = None


class ApproveResponse(BaseModel):
    version_id: str
    status: str


class RejectRequest(BaseModel):
    notes: Optional[str] = None
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
    reason: Optional[str] = None


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
    message: Optional[str] = None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: List[FeedbackItem]
    total: int


# ── Subscription analytics ────────────────────────────────────────────────────

class SubscriptionAnalyticsResponse(BaseModel):
    active_monthly: int
    active_annual: int
    total_active: int
    mrr_usd: float
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
    items: List[StruggleItem]


# ── Pipeline status ───────────────────────────────────────────────────────────

class PipelineStatusResponse(BaseModel):
    last_run_at: Optional[datetime]
    total_versions: int
    ready_for_review: int
    approved: int
    published: int
    rejected: int
    pending: int


# ── Dictionary ────────────────────────────────────────────────────────────────

class DictionaryResponse(BaseModel):
    word: str
    definitions: List[str]
    synonyms: List[str]
    antonyms: List[str]
