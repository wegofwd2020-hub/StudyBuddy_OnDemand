"""
backend/src/feedback/schemas.py

Pydantic models for Phase 10 feedback endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class FeedbackSubmitRequest(BaseModel):
    category: str = Field(..., pattern="^(content|ux|general)$")
    unit_id: str | None = None
    curriculum_id: str | None = None
    # Optional since the thumbs widget has no text box (#600). `helpful` carries
    # the verdict instead; never synthesise message text on the student's behalf.
    message: str | None = Field(None, min_length=1, max_length=500)
    rating: int | None = Field(None, ge=1, le=5)
    helpful: bool | None = None
    content_type: str | None = Field(None, pattern="^(lesson|tutorial|experiment|quiz)$")

    @model_validator(mode="after")
    def require_some_content(self) -> FeedbackSubmitRequest:
        """Reject feedback that says nothing.

        Making `message` optional removed the only thing keeping blank rows out,
        so the request must still carry at least one signal a reviewer can act
        on. Mirrors the `feedback_has_content` CHECK (migration 0062) so the
        caller gets a 422 rather than a 500 from the database.
        """
        if self.message is None and self.rating is None and self.helpful is None:
            raise ValueError("Feedback must include a message, a rating, or a helpful verdict.")
        return self


class FeedbackSubmitResponse(BaseModel):
    feedback_id: str
    submitted_at: datetime


class AdminFeedbackItem(BaseModel):
    feedback_id: str
    student_id: str
    category: str
    unit_id: str | None = None
    curriculum_id: str | None = None
    message: str | None = None
    rating: int | None = None
    helpful: bool | None = None
    content_type: str | None = None
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
