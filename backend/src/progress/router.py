"""
backend/src/progress/router.py

Progress tracking endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /progress/session                        → StartSessionResponse
  POST /progress/session/{session_id}/answer    → RecordAnswerResponse   (fire-and-forget write)
  POST /progress/session/{session_id}/end       → EndSessionResponse
  GET  /progress/student                        → ProgressHistoryResponse

Security:
  All routes require a valid student JWT.
  Session ownership enforced on answer + end endpoints.
  JWT student_id must match the URL / data being accessed.

Performance:
  POST /progress/session/{id}/answer — dispatches Celery task, returns 200 immediately.
  POST /progress/session/{id}/end   — writes session synchronously (needed for score response),
                                      then dispatches Celery tasks (streak + view refresh).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.auth.dependencies import get_current_student
from src.core.db import get_db
from src.progress.schemas import (
    EndSessionRequest,
    EndSessionResponse,
    ProgressHistoryResponse,
    RecordAnswerRequest,
    RecordAnswerResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from src.progress.service import (
    create_session,
    end_session,
    get_raw_history,
    verify_session_owner,
)
from src.utils.logger import get_logger

log = get_logger("progress")
router = APIRouter(tags=["progress"])


@router.post("/progress/session", response_model=StartSessionResponse, status_code=201)
async def start_session(
    request: Request,
    body: StartSessionRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> StartSessionResponse:
    """
    Open a new quiz session for a student.

    attempt_number is computed server-side (COUNT prior completed sessions + 1).
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            result = await create_session(
                conn,
                student_id=student_id,
                unit_id=body.unit_id,
                curriculum_id=body.curriculum_id,
            )
        except Exception as exc:
            log.error("start_session_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not create session.", "correlation_id": cid},
            )

    return StartSessionResponse(**result)


@router.post(
    "/progress/session/{session_id}/answer",
    response_model=RecordAnswerResponse,
    status_code=200,
)
async def record_answer(
    request: Request,
    session_id: str,
    body: RecordAnswerRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> RecordAnswerResponse:
    """
    Record a single quiz answer.

    Write is fire-and-forget via Celery task — returns 200 before DB write.
    The session_id ownership is verified synchronously first.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    # Validate session_id format
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_session_id", "detail": "session_id must be a UUID.", "correlation_id": cid},
        )

    # Verify ownership synchronously (cheap DB hit — just SELECT)
    async with get_db(request) as conn:
        try:
            await verify_session_owner(conn, session_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "detail": "Session not found.", "correlation_id": cid},
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "detail": "This session belongs to another student.", "correlation_id": cid},
            )

    # Fire-and-forget Celery task for the actual write
    from src.auth.tasks import celery_app
    celery_app.send_task(
        "src.auth.tasks.write_progress_answer_task",
        kwargs={
            "session_id": session_id,
            "question_id": body.question_id,
            "student_answer": body.student_answer,
            "correct_answer": body.correct_answer,
            "correct": body.correct,
            "ms_taken": body.ms_taken,
            "event_id": body.event_id,
        },
        queue="io",
    )

    return RecordAnswerResponse(answer_id="", correct=body.correct)


@router.post(
    "/progress/session/{session_id}/end",
    response_model=EndSessionResponse,
    status_code=200,
)
async def end_session_endpoint(
    request: Request,
    session_id: str,
    body: EndSessionRequest,
    student: Annotated[dict, Depends(get_current_student)],
) -> EndSessionResponse:
    """
    Close a session and compute the final score + passed flag.

    Score is written synchronously (client needs the result immediately).
    Streak update and progress view refresh are dispatched as Celery tasks.
    Dashboard cache for this student is invalidated.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_session_id", "detail": "session_id must be a UUID.", "correlation_id": cid},
        )

    async with get_db(request) as conn:
        try:
            session_row = await verify_session_owner(conn, session_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "detail": "Session not found.", "correlation_id": cid},
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "detail": "This session belongs to another student.", "correlation_id": cid},
            )

        if session_row["completed"]:
            raise HTTPException(
                status_code=409,
                detail={"error": "session_already_ended", "detail": "This session has already been ended.", "correlation_id": cid},
            )

        try:
            result = await end_session(conn, session_id=session_id, score=body.score, total_questions=body.total_questions)
        except Exception as exc:
            log.error("end_session_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not end session.", "correlation_id": cid},
            )

    # Invalidate dashboard L1 + L2 cache
    from src.core.cache import dashboard_cache
    dashboard_cache.pop(student_id, None)
    redis = request.app.state.redis
    await redis.delete(f"dashboard:{student_id}")

    # Fire-and-forget: streak update + materialized view refresh
    from datetime import date

    from src.auth.tasks import celery_app
    today = date.today().isoformat()
    celery_app.send_task("src.auth.tasks.update_streak_task", kwargs={"student_id": student_id, "activity_date": today}, queue="io")
    celery_app.send_task("src.auth.tasks.refresh_progress_view_task", kwargs={"student_id": student_id}, queue="io")

    return EndSessionResponse(**result)


@router.get("/progress/student", response_model=ProgressHistoryResponse, status_code=200)
async def get_student_history(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProgressHistoryResponse:
    """
    Return the full raw progress history for the authenticated student.

    Returns sessions ordered newest-first, with answers nested inside.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            history = await get_raw_history(conn, student_id=student_id, limit=limit, offset=offset)
        except Exception as exc:
            log.error("get_history_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not retrieve history.", "correlation_id": cid},
            )

    return ProgressHistoryResponse(**history)
