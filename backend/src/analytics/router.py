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

from src.analytics.schemas import (
    ClassMetricsResponse,
    LessonEndRequest,
    LessonEndResponse,
    LessonStartRequest,
    LessonStartResponse,
    StudentMetricsResponse,
)
from src.analytics.service import (
    get_class_metrics,
    get_student_metrics,
    start_lesson_view,
    verify_view_owner,
)
from src.auth.dependencies import get_current_student, get_current_teacher
from src.core.db import get_db
from src.core.subjects import display_subject, resolve_subject_labels
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
                detail={
                    "error": "internal_error",
                    "detail": "Could not record lesson start.",
                    "correlation_id": cid,
                },
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
            detail={
                "error": "invalid_view_id",
                "detail": "view_id must be a UUID.",
                "correlation_id": cid,
            },
        )

    # Verify ownership synchronously
    async with get_db(request) as conn:
        try:
            view_row = await verify_view_owner(conn, body.view_id, student_id)
        except LookupError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "view_not_found",
                    "detail": "Lesson view not found.",
                    "correlation_id": cid,
                },
            )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "This view belongs to another student.",
                    "correlation_id": cid,
                },
            )

        if view_row.get("ended_at") is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "view_already_ended",
                    "detail": "This lesson view has already been ended.",
                    "correlation_id": cid,
                },
            )

    # Fire-and-forget: write duration + flags
    from src.core.celery_app import celery_app

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


# ── GET /analytics/student/stats ─────────────────────────────────────────────


_PERIOD_DAYS: dict[str, int | None] = {"7d": 7, "30d": 30, "all": None}


@router.get("/analytics/student/stats")
async def student_stats(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    period: str = "30d",
) -> dict:
    """
    Return streak, session dates, and summary stats for the student dashboard.

    period          — "7d" | "30d" | "all": scopes the charts and totals
                      (session_dates, quiz counts, subject breakdown). Previously
                      this query param was sent by the web client but ignored,
                      so the selector did nothing.
    streak_days     — consecutive days with at least one completed session
                      (ending today), computed over a fixed window so it is never
                      truncated by a short selected period.
    """
    student_id = str(student["student_id"])
    days = _PERIOD_DAYS.get(period, 30)

    # Period-scoped time filter shared by the charts/totals queries. "all" → no
    # filter. days is bound as $2 only when present, so the parameter numbering
    # stays consistent across all three queries.
    if days is None:
        period_clause = ""
        period_params: list[int] = []
    else:
        period_clause = "AND started_at >= NOW() - make_interval(days => $2)"
        period_params = [days]

    async with get_db(request) as conn:
        rows = await conn.fetch(
            f"""
            SELECT DATE(started_at AT TIME ZONE 'UTC') AS session_date,
                   COUNT(*) AS sessions,
                   AVG(score::float / NULLIF(total_questions, 0) * 100) FILTER (WHERE score IS NOT NULL) AS avg_score,
                   SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS passed_count,
                   COUNT(*) FILTER (WHERE score IS NOT NULL) AS scored_count
            FROM progress_sessions
            WHERE student_id = $1
              {period_clause}
            GROUP BY 1
            ORDER BY 1 DESC
            """,
            student_id,
            *period_params,
        )

        # Lesson views + audio in the selected period
        view_rows = await conn.fetch(
            f"""
            SELECT COUNT(*) AS lessons_viewed,
                   SUM(CASE WHEN audio_played THEN 1 ELSE 0 END) AS audio_sessions
            FROM lesson_views
            WHERE student_id = $1
              {period_clause}
            """,
            student_id,
            *period_params,
        )

        # Subject breakdown (selected period). Grouped per unit so we can resolve
        # human-readable subject names (issue #462) before aggregating — the raw
        # progress_sessions.subject column holds codes / "unknown".
        unit_subj_rows = await conn.fetch(
            f"""
            SELECT unit_id, subject,
                   COUNT(*) AS lessons,
                   SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS passed_count
            FROM progress_sessions
            WHERE student_id = $1
              {period_clause}
            GROUP BY unit_id, subject
            """,
            student_id,
            *period_params,
        )
        subject_labels = await resolve_subject_labels(conn, [r["unit_id"] for r in unit_subj_rows])

        # Streak is independent of the selected period: pull distinct active days
        # over a generous fixed window so picking "7d" never truncates a longer
        # current streak.
        streak_rows = await conn.fetch(
            """
            SELECT DISTINCT DATE(started_at AT TIME ZONE 'UTC') AS d
            FROM progress_sessions
            WHERE student_id = $1
              AND started_at >= NOW() - INTERVAL '400 days'
            """,
            student_id,
        )

    session_dates = [str(r["session_date"]) for r in rows]
    total_sessions = sum(r["sessions"] for r in rows)
    total_scored = sum(r["scored_count"] for r in rows)
    total_passed = sum(r["passed_count"] for r in rows)

    # Compute streak from today backwards over the fixed-window active days.
    from datetime import date, timedelta

    today = date.today()
    streak_dates = {str(r["d"]) for r in streak_rows}
    streak = 0
    check = today
    while str(check) in streak_dates:
        streak += 1
        check -= timedelta(days=1)

    avg_score = 0.0
    if rows:
        scores = [r["avg_score"] for r in rows if r["avg_score"] is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0

    vr = dict(view_rows[0]) if view_rows else {}

    # Aggregate the per-unit rows into per-(display)-subject totals.
    breakdown: dict[str, dict[str, int]] = {}
    for r in unit_subj_rows:
        label = display_subject(subject_labels, r["unit_id"], r["subject"])
        agg = breakdown.setdefault(label, {"lessons": 0, "passed": 0})
        agg["lessons"] += int(r["lessons"])
        agg["passed"] += int(r["passed_count"] or 0)
    subject_breakdown = [
        {
            "subject": label,
            "lessons": agg["lessons"],
            "pass_rate": round(agg["passed"] / agg["lessons"], 4) if agg["lessons"] else 0.0,
        }
        for label, agg in sorted(breakdown.items())
    ]

    return {
        "streak_days": streak,
        "session_dates": session_dates,
        "lessons_viewed": int(vr.get("lessons_viewed") or 0),
        "quizzes_completed": int(total_sessions),
        "pass_rate": round(total_passed / total_scored, 4) if total_scored else 0.0,
        "avg_score": round(avg_score / 100, 4),
        "audio_sessions": int(vr.get("audio_sessions") or 0),
        "subject_breakdown": subject_breakdown,
    }


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
            detail={
                "error": "forbidden",
                "detail": "Cannot view analytics for a different school.",
                "correlation_id": cid,
            },
        )
    async with get_db(request) as conn:
        result = await get_class_metrics(conn, school_id, grade=grade, subject=subject)
    return ClassMetricsResponse(**result)
