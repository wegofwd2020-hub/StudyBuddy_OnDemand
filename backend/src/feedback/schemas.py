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
    # ADR-008 Phase 2 — narrow this feedback to ONE question.
    #
    # The POSITIONAL id the student was shown (`q1…qN`) plus the session it was
    # shown in. The server resolves the stable identity from the set that session
    # was graded against; the client never sends the stable id and so cannot name
    # a question it was not served. Same shape as the answer path, same reason.
    #
    # Both are required together or not at all — a question id without a session
    # cannot be resolved, and a session without a question narrows nothing.
    session_id: str | None = None
    question_id: str | None = None

    @model_validator(mode="after")
    def question_needs_its_session(self) -> FeedbackSubmitRequest:
        """A question id is meaningless without the session that served it.

        Rejected rather than silently ignored: dropping half a pair would record
        feedback the student believes is attached to a question, and attach it to
        nothing.
        """
        if bool(self.question_id) != bool(self.session_id):
            raise ValueError(
                "question_id and session_id must be provided together"
            )
        return self

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


class FeedbackResolveResponse(BaseModel):
    feedback_id: str
    reviewed: bool
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
