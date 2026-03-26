"""
backend/src/analytics/router.py

Lesson analytics endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /analytics/lesson/start              → LessonStartResponse  (201)
  POST /analytics/lesson/end                → LessonEndResponse    (200) — fire-and-forget write
  GET  /analytics/student/me                → StudentMetricsResponse
  GET  /analytics/school/{school_id}/class  → ClassMetricsResponse

Performance:
  POST /analytics/lesson/end — dispatches Celery task, returns 200 immediately.
  Ownership is verified synchronously first (cheap SELECT).

Security:
  All routes require a valid student JWT.
  View ownership enforced on the /end endpoint.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_student, get_current_teacher
from src.core.db import get_db
from src.analytics.schemas import (
    ClassMetricsResponse,
    LessonEndRequest,
    LessonEndResponse,
    LessonStartRequest,
    LessonStartResponse,
    StudentMetricsResponse,
)
from src.analytics.service import (
    end_lesson_view,
    get_class_metrics,
    get_student_metrics,
    start_lesson_view,
    verify_view_owner,
)
from src.utils.logger import get_logger

log = get_logger("analytics")
router = APIRouter(tags=["analytics"])


@router.post("/analytics/lesson/start", response_model=LessonStartResponse, status_code=201)
async def lesson_start(
    request: Request,
    body: LessonStartRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> LessonStartResponse:
    """
    Record that a student opened a lesson.

    Creates a lesson_views row with started_at = NOW().
    The mobile app stores the returned view_id and sends it when the lesson closes.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            result = await start_lesson_view(
                conn,
                student_id=student_id,
                unit_id=body.unit_id,
                curriculum_id=body.curriculum_id,
            )
        except Exception as exc:
            log.error("lesson_start_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not record lesson start.", "correlation_id": cid},
            )

    return LessonStartResponse(**result)


@router.post("/analytics/lesson/end", response_model=LessonEndResponse, status_code=200)
async def lesson_end(
    request: Request,
    body: LessonEndRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> LessonEndResponse:
    """
    Record that a student closed a lesson (fire-and-forget write).

    Verifies view ownership synchronously, then dispatches a Celery task
    for the actual DB write. Returns 200 before the write completes.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    # Validate view_id format
    try:
        uuid.UUID(body.view_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_view_id", "detail": "view_id must be a UUID.", "correlation_id": cid},
        )

    # Verify ownership synchronously
    async with get_db(request) as conn:
        try:
            view_row = await verify_view_owner(conn, body.view_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={"error": "view_not_found", "detail": "Lesson view not found.", "correlation_id": cid},
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "detail": "This view belongs to another student.", "correlation_id": cid},
            )

        if view_row.get("ended_at") is not None:
            raise HTTPException(
                status_code=409,
                detail={"error": "view_already_ended", "detail": "This lesson view has already been ended.", "correlation_id": cid},
            )

    # Fire-and-forget: write duration + flags
    from src.auth.tasks import celery_app
    celery_app.send_task(
        "src.auth.tasks.write_lesson_end_task",
        kwargs={
            "view_id": body.view_id,
            "duration_s": body.duration_s,
            "audio_played": body.audio_played,
            "experiment_viewed": body.experiment_viewed,
        },
        queue="io",
    )

    return LessonEndResponse(view_id=body.view_id, duration_s=body.duration_s)


# ── GET /analytics/student/me ─────────────────────────────────────────────────

@router.get("/analytics/student/me", response_model=StudentMetricsResponse)
async def student_metrics(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> StudentMetricsResponse:
    """Return self-service analytics for the authenticated student."""
    student_id = str(student["student_id"])
    async with get_db(request) as conn:
        result = await get_student_metrics(conn, student_id)
    return StudentMetricsResponse(**result)


# ── GET /analytics/school/{school_id}/class ───────────────────────────────────

@router.get("/analytics/school/{school_id}/class", response_model=ClassMetricsResponse)
async def class_metrics(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    grade: int | None = None,
    subject: str | None = None,
) -> ClassMetricsResponse:
    """
    Return aggregate per-unit analytics for all enrolled students in a school.

    Requires teacher JWT. Teachers can only view their own school's data.
    """
    cid = getattr(request.state, "correlation_id", "")
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "Cannot view analytics for a different school.", "correlation_id": cid},
        )
    async with get_db(request) as conn:
        result = await get_class_metrics(conn, school_id, grade=grade, subject=subject)
    return ClassMetricsResponse(**result)
