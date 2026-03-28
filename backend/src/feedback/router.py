"""
backend/src/feedback/router.py

Phase 10 feedback endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /feedback          — student submits feedback (rate-limited: 5/student/hour)
  GET  /admin/feedback    — admin lists all feedback (paginated, filterable)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.admin.router import _require
from src.auth.dependencies import get_current_student
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.feedback.schemas import (
    AdminFeedbackListResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
)
from src.feedback.service import (
    check_and_increment_rate_limit,
    list_feedback,
    submit_feedback,
)
from src.utils.logger import get_logger

log = get_logger("feedback")
router = APIRouter(tags=["feedback"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── POST /feedback (student) ──────────────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackSubmitResponse)
async def submit_feedback_endpoint(
    body: FeedbackSubmitRequest,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> FeedbackSubmitResponse:
    """
    Submit product feedback.

    Rate-limited to 5 submissions per student per hour.
    Returns 429 if the limit is exceeded.
    """
    student_id = str(student["student_id"])
    redis = get_redis(request)

    allowed = await check_and_increment_rate_limit(redis, student_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "detail": "Feedback limit reached. You can submit up to 5 per hour.",
                "correlation_id": _cid(request),
            },
        )

    async with get_db(request) as conn:
        result = await submit_feedback(
            conn,
            student_id=student_id,
            category=body.category,
            message=body.message,
            unit_id=body.unit_id,
            curriculum_id=body.curriculum_id,
            rating=body.rating,
        )

    return FeedbackSubmitResponse(**result)


# ── GET /admin/feedback (admin) ───────────────────────────────────────────────

@router.get("/admin/feedback", response_model=AdminFeedbackListResponse)
async def list_admin_feedback(
    request: Request,
    admin: Annotated[dict, Depends(_require("feedback:view"))],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    unit_id: str | None = Query(None),
    curriculum_id: str | None = Query(None),
    reviewed: bool | None = Query(None),
) -> AdminFeedbackListResponse:
    """
    List all student feedback (admin only, requires feedback:view permission).

    Supports pagination and filtering by category, unit, curriculum, and reviewed status.
    """
    async with get_db(request) as conn:
        result = await list_feedback(
            conn,
            page=page,
            per_page=per_page,
            category=category,
            unit_id=unit_id,
            curriculum_id=curriculum_id,
            reviewed=reviewed,
        )

    return AdminFeedbackListResponse(**result)
