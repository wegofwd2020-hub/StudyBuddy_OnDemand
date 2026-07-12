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
from src.content.service import get_quiz_answer_key
from src.core.db import get_db
from src.core.storage import StorageBackend, get_storage
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
    count_correct_answers,
    create_session,
    end_session,
    get_raw_history,
    read_tally,
    resolve_session_quiz_set,
    tally_answer,
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
                detail={
                    "error": "internal_error",
                    "detail": "Could not create session.",
                    "correlation_id": cid,
                },
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
    storage: StorageBackend = Depends(get_storage),
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
            detail={
                "error": "invalid_session_id",
                "detail": "session_id must be a UUID.",
                "correlation_id": cid,
            },
        )

    # Verify ownership synchronously (cheap DB hit — just SELECT)
    async with get_db(request) as conn:
        try:
            session = await verify_session_owner(conn, session_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "session_not_found",
                    "detail": "Session not found.",
                    "correlation_id": cid,
                },
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "This session belongs to another student.",
                    "correlation_id": cid,
                },
            )

    # ── Grade server-side ─────────────────────────────────────────────────────
    # The client sends only which option was picked. Correctness is resolved from
    # the content store here; nothing the browser claims about it is trusted.
    redis = request.app.state.redis
    try:
        set_number = await resolve_session_quiz_set(
            redis, session_id=session_id, student_id=student_id, unit_id=session["unit_id"]
        )
        answer_key = await get_quiz_answer_key(
            curriculum_id=session["curriculum_id"],
            unit_id=session["unit_id"],
            set_number=set_number,
            lang=student.get("locale", "en"),
            redis=redis,
            storage=storage,
        )
    except FileNotFoundError:
        # The quiz the student is answering is gone from the store. Refuse rather
        # than recording an ungraded answer.
        raise HTTPException(
            status_code=404,
            detail={
                "error": "quiz_not_found",
                "detail": "This quiz is no longer available.",
                "correlation_id": cid,
            },
        )

    entry = answer_key.get(body.question_id)
    if entry is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_question",
                "detail": "That question is not part of this quiz.",
                "correlation_id": cid,
            },
        )

    correct_index = entry["index"]
    correct = body.student_answer == correct_index

    # Running tally in Redis: the DB write below is fire-and-forget, so the rows
    # may not exist yet when the session ends. This is what end_session reads.
    await tally_answer(redis, session_id=session_id, correct=correct)

    # Fire-and-forget Celery task for the actual write — with the SERVER's verdict
    from src.core.celery_app import celery_app

    celery_app.send_task(
        "src.auth.tasks.write_progress_answer_task",
        kwargs={
            "session_id": session_id,
            "question_id": body.question_id,
            "student_answer": body.student_answer,
            "correct_answer": correct_index,
            "correct": correct,
            "ms_taken": body.ms_taken,
            "event_id": body.event_id,
            "quiz_set": set_number,
        },
        queue="io",
    )

    return RecordAnswerResponse(
        answer_id="",
        correct=correct,
        correct_index=correct_index,
        explanation=entry.get("explanation", ""),
    )


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
    storage: StorageBackend = Depends(get_storage),
) -> EndSessionResponse:
    """
    Close a session and compute the final score + passed flag.

    The score is derived from the answers the SERVER graded during the session
    (Redis tally, falling back to persisted answers) — never from the request
    body. A client that posts a score is ignored.

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
            detail={
                "error": "invalid_session_id",
                "detail": "session_id must be a UUID.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        try:
            session_row = await verify_session_owner(conn, session_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "session_not_found",
                    "detail": "Session not found.",
                    "correlation_id": cid,
                },
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "This session belongs to another student.",
                    "correlation_id": cid,
                },
            )

        if session_row["completed"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "session_already_ended",
                    "detail": "This session has already been ended.",
                    "correlation_id": cid,
                },
            )

        # ── Resolve the score server-side ─────────────────────────────────────
        redis = request.app.state.redis

        score = await read_tally(redis, session_id)
        if score is None:
            # Redis lost the tally (restart / TTL). Fall back to what was graded
            # and persisted. May undercount if writes are still in flight, but it
            # is still a server-derived number, never the client's.
            log.warning("quiz_tally_missing_falling_back_to_db", correlation_id=cid)
            score = await count_correct_answers(conn, session_id)

        # The quiz's real length is the answer key's — not whatever the client says.
        total_questions = body.total_questions or 1
        try:
            set_number = await resolve_session_quiz_set(
                redis,
                session_id=session_id,
                student_id=student_id,
                unit_id=session_row["unit_id"],
            )
            answer_key = await get_quiz_answer_key(
                curriculum_id=session_row["curriculum_id"],
                unit_id=session_row["unit_id"],
                set_number=set_number,
                lang=student.get("locale", "en"),
                redis=redis,
                storage=storage,
            )
            if answer_key:
                total_questions = len(answer_key)
        except FileNotFoundError:
            # Content gone since the attempt started — fall back to the client's
            # hint for the denominator only. The score itself is still ours.
            log.warning("quiz_answer_key_missing_at_end", correlation_id=cid)

        try:
            result = await end_session(
                conn, session_id=session_id, score=score, total_questions=total_questions
            )
        except Exception as exc:
            log.error("end_session_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_error",
                    "detail": "Could not end session.",
                    "correlation_id": cid,
                },
            )

    # Invalidate dashboard L1 + L2 cache
    from src.core.cache import dashboard_cache

    dashboard_cache.pop(student_id, None)
    redis = request.app.state.redis
    await redis.delete(f"dashboard:{student_id}")

    # Fire-and-forget: streak update + materialized view refresh
    from datetime import date

    from src.core.celery_app import celery_app

    today = date.today().isoformat()
    celery_app.send_task(
        "src.auth.tasks.update_streak_task",
        kwargs={"student_id": student_id, "activity_date": today},
        queue="io",
    )
    celery_app.send_task(
        "src.auth.tasks.refresh_progress_view_task", kwargs={"student_id": student_id}, queue="io"
    )

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
                detail={
                    "error": "internal_error",
                    "detail": "Could not retrieve history.",
                    "correlation_id": cid,
                },
            )

    return ProgressHistoryResponse(**history)
