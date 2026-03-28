"""
backend/src/feedback/schemas.py

Pydantic models for Phase 10 feedback endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackSubmitRequest(BaseModel):
    category: str = Field(..., pattern="^(content|ux|general)$")
    unit_id: str | None = None
    curriculum_id: str | None = None
    message: str = Field(..., min_length=1, max_length=500)
    rating: int | None = Field(None, ge=1, le=5)


class FeedbackSubmitResponse(BaseModel):
    feedback_id: str
    submitted_at: datetime


class AdminFeedbackItem(BaseModel):
    feedback_id: str
    student_id: str
    category: str
    unit_id: str | None = None
    curriculum_id: str | None = None
    message: str
    rating: int | None = None
    submitted_at: datetime
    reviewed: bool
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class AdminFeedbackPagination(BaseModel):
    page: int
    per_page: int
    total: int


class AdminFeedbackListResponse(BaseModel):
    pagination: AdminFeedbackPagination
    feedback_items: list[AdminFeedbackItem]
