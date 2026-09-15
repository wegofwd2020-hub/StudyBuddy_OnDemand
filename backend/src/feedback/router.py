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
    FeedbackResolveResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
)
from src.feedback.service import (
    check_and_increment_rate_limit,
    list_feedback,
    resolve_feedback,
    submit_feedback,
)
from src.utils.logger import get_logger

log = get_logger("feedback")
router = APIRouter(tags=["feedback"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── POST /feedback (student) ──────────────────────────────────────────────────


async def _resolve_stable_question_id(
    request: Request,
    conn,
    student_id: str,
    session_id: str,
    question_id: str,
) -> str | None:
    """Positional question id -> the question's stable identity, or None.

    Ownership is verified first: without it, any student could attach feedback to
    any other student's session by guessing a UUID. Returns None rather than
    raising on every failure path — see the caller for why the narrowing is
    best-effort while the feedback itself is not.
    """
    from src.content.service import resolve_quiz_answer_key
    from src.progress.service import resolve_session_quiz_set, verify_session_owner

    try:
        session = await verify_session_owner(conn, session_id, student_id)
    except Exception:
        log.info("feedback_question_session_not_owned", extra={"session_id": session_id})
        return None

    try:
        set_number = await resolve_session_quiz_set(
            get_redis(request),
            session_id=session_id,
            student_id=student_id,
            unit_id=session["unit_id"],
        )
        key = await resolve_quiz_answer_key(
            None,
            session["curriculum_id"],
            session["unit_id"],
            set_number,
            "en",
            request.app.state.pool,
            get_redis(request),
            request.app.state.storage,
        )
    except Exception as exc:
        log.info("feedback_question_unresolved", extra={"error": str(exc)[:120]})
        return None

    entry = key.get(question_id)
    return entry.get("stable_question_id") if entry else None


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
        # ADR-008 Phase 2. The client sends the POSITIONAL id it was shown; the
        # stable identity is resolved here from the set that session was actually
        # graded against, so a client cannot attach a comment to a question it was
        # never served. Same shape as the answer path (pitfall #35).
        #
        # Resolution failing is not a submission failure: the student wrote
        # something, and losing it because a session expired would be a worse
        # outcome than storing it against the unit alone. The narrowing is
        # best-effort; the feedback is not.
        stable_qid = None
        if body.question_id and body.session_id:
            stable_qid = await _resolve_stable_question_id(
                request, conn, student_id, body.session_id, body.question_id
            )

        result = await submit_feedback(
            conn,
            student_id=student_id,
            category=body.category,
            message=body.message,
            unit_id=body.unit_id,
            curriculum_id=body.curriculum_id,
            rating=body.rating,
            helpful=body.helpful,
            content_type=body.content_type,
            stable_question_id=stable_qid,
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


# ── POST /admin/feedback/{feedback_id}/resolve (admin) ────────────────────────


@router.post(
    "/admin/feedback/{feedback_id}/resolve",
    response_model=FeedbackResolveResponse,
)
async def resolve_feedback_endpoint(
    feedback_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("feedback:resolve"))],
) -> FeedbackResolveResponse:
    """Mark a feedback item reviewed.

    The admin Feedback page has shipped this button since it was built, but the
    endpoint never existed and the click 404'd. It went unnoticed because no
    feedback was ever stored, so there was never a button to press (#603).
    """
    async with get_db(request) as conn:
        result = await resolve_feedback(conn, feedback_id, str(admin["admin_id"]))

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "That feedback item does not exist.",
                "correlation_id": _cid(request),
            },
        )
    return FeedbackResolveResponse(**result)
