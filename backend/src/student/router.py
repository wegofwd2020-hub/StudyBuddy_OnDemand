"""
backend/src/student/router.py

Student self-service endpoints.

Routes (all prefixed /api/v1 in main.py):
  GET /student/dashboard            → DashboardResponse   (L2 Redis 60 s cache)
  GET /student/progress             → ProgressMapResponse (backed by mat. view)
  GET /student/stats?period=7d|30d|all → StatsResponse

Security:
  All routes require a valid student JWT.
  JWT student_id is the sole source of identity — no URL parameter accepted.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.auth.dependencies import get_current_student
from src.core.db import get_db
from src.student.schemas import DashboardResponse, ProgressMapResponse, StatsResponse
from src.student.service import get_dashboard, get_progress_map, get_stats
from src.utils.logger import get_logger

log = get_logger("student")
router = APIRouter(tags=["student"])


@router.get("/student/dashboard", response_model=DashboardResponse, status_code=200)
async def student_dashboard(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> DashboardResponse:
    """
    Aggregated dashboard card for the authenticated student.

    Cached at L2 Redis (60 s TTL); invalidated on session/end.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    redis = request.app.state.redis
    async with get_db(request) as conn:
        try:
            payload = await get_dashboard(conn, redis, student_id)
        except Exception as exc:
            log.error("dashboard_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not load dashboard.", "correlation_id": cid},
            )

    return DashboardResponse(**payload)


@router.get("/student/progress", response_model=ProgressMapResponse, status_code=200)
async def student_progress_map(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> ProgressMapResponse:
    """
    Curriculum map with per-unit status badges.

    Reads from mv_student_curriculum_progress (materialized view).
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        try:
            payload = await get_progress_map(conn, student_id)
        except Exception as exc:
            log.error("progress_map_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not load progress map.", "correlation_id": cid},
            )

    return ProgressMapResponse(**payload)


@router.get("/student/stats", response_model=StatsResponse, status_code=200)
async def student_stats(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    period: str = Query(default="30d", pattern="^(7d|30d|all)$"),
) -> StatsResponse:
    """
    Usage statistics for the requested period (7d | 30d | all).

    Includes daily_activity breakdown and streak counters from Redis.
    """
    student_id = student["student_id"]
    cid = getattr(request.state, "correlation_id", "")

    redis = request.app.state.redis
    async with get_db(request) as conn:
        try:
            payload = await get_stats(conn, redis, student_id, period)
        except Exception as exc:
            log.error("stats_failed", error=str(exc), correlation_id=cid)
            raise HTTPException(
                status_code=500,
                detail={"error": "internal_error", "detail": "Could not load stats.", "correlation_id": cid},
            )

    return StatsResponse(**payload)
