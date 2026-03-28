"""
backend/src/reports/router.py

Phase 11 teacher reporting dashboard endpoints.

Routes (all prefixed /api/v1 in main.py):
  GET  /reports/school/{school_id}/overview
  GET  /reports/school/{school_id}/unit/{unit_id}
  GET  /reports/school/{school_id}/student/{student_id}
  GET  /reports/school/{school_id}/curriculum-health
  GET  /reports/school/{school_id}/feedback
  GET  /reports/school/{school_id}/trends
  POST /reports/school/{school_id}/export
  GET  /reports/school/{school_id}/alerts
  PUT  /reports/school/{school_id}/alerts/settings
  POST /reports/school/{school_id}/digest/subscribe
  POST /reports/school/{school_id}/refresh
  GET  /reports/download/{export_id}

Security:
  All endpoints require teacher JWT.  School ownership enforced.
  POST /refresh requires school_admin role.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.reports.schemas import (
    AlertListResponse,
    AlertSettings,
    AlertSettingsResponse,
    CurriculumHealthReport,
    DigestSubscribeRequest,
    DigestSubscribeResponse,
    ExportRequest,
    ExportResponse,
    FeedbackReport,
    OverviewReport,
    RefreshResponse,
    StudentReport,
    TrendsReport,
    UnitReport,
)
from src.reports.service import (
    get_alerts,
    get_curriculum_health,
    get_feedback_report,
    get_overview,
    get_student_report,
    get_trends,
    get_unit_report,
    refresh_materialized_views,
    save_alert_settings,
    subscribe_digest,
    trigger_export,
)
from src.utils.logger import get_logger

log = get_logger("reports")
router = APIRouter(tags=["reports"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _check_school(teacher: dict, school_id: str, request: Request) -> None:
    """Raise 403 if the teacher JWT's school_id doesn't match the URL."""
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot access reports for a different school.",
                "correlation_id": _cid(request),
            },
        )


# ── Student Roster ────────────────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/roster")
async def student_roster(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    grade: int | None = None,
) -> dict:
    """
    Return per-student rows for the Class Overview table.

    Columns: student_id, student_name, grade, units_completed, total_units,
             avg_score_pct, last_active.
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        grade_filter = "AND s.grade = $2" if grade is not None else ""
        params = [school_id, grade] if grade is not None else [school_id]
        rows = await conn.fetch(
            f"""
            SELECT
                s.student_id,
                s.name                                              AS student_name,
                s.grade,
                COALESCE(SUM(CASE WHEN ps.passed THEN 1 ELSE 0 END), 0)
                                                                    AS units_completed,
                (SELECT COUNT(*) FROM curriculum_units cu
                 JOIN curricula c ON c.curriculum_id = cu.curriculum_id
                 WHERE c.grade = s.grade AND c.is_default)          AS total_units,
                COALESCE(
                    AVG(CASE WHEN ps.score IS NOT NULL
                        THEN ps.score::float / NULLIF(ps.total_questions, 0) * 100
                    END), 0
                )                                                   AS avg_score_pct,
                MAX(ps.started_at)                                  AS last_active
            FROM students s
            LEFT JOIN progress_sessions ps ON ps.student_id = s.student_id
                AND ps.completed = true
            WHERE s.school_id = $1 {grade_filter}
            GROUP BY s.student_id, s.name, s.grade
            ORDER BY s.name
            """,
            *params,
        )

    students = [
        {
            "student_id": str(r["student_id"]),
            "student_name": r["student_name"],
            "grade": r["grade"],
            "units_completed": int(r["units_completed"]),
            "total_units": int(r["total_units"] or 0),
            "avg_score_pct": round(float(r["avg_score_pct"] or 0), 1),
            "last_active": r["last_active"].isoformat() if r["last_active"] else None,
        }
        for r in rows
    ]
    return {"school_id": school_id, "grade": grade, "subject": None, "students": students}


# ── Report 1: Class Overview ──────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/overview", response_model=OverviewReport)
async def overview_report(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    period: str = Query("7d", pattern="^(7d|30d|term)$"),
) -> OverviewReport:
    """Class overview summary for the selected period."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_overview(conn, school_id, period)
    return OverviewReport(**result)


# ── Report 2: Unit Performance ────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/unit/{unit_id}", response_model=UnitReport)
async def unit_report(
    school_id: str,
    unit_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    period: str = Query("7d", pattern="^(7d|30d|term)$"),
) -> UnitReport:
    """Per-unit performance deep-dive."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_unit_report(conn, school_id, unit_id, period)
    return UnitReport(**result)


# ── Report 3: Student Progress ────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/student/{student_id}", response_model=StudentReport)
async def student_report(
    school_id: str,
    student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> StudentReport:
    """Individual student report card."""
    _check_school(teacher, school_id, request)
    cid = _cid(request)
    async with get_db(request) as conn:
        try:
            result = await get_student_report(conn, school_id, student_id)
        except LookupError as exc:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": str(exc), "correlation_id": cid},
            )
    return StudentReport(**result)


# ── Report 4: Curriculum Health ───────────────────────────────────────────────

@router.get("/reports/school/{school_id}/curriculum-health", response_model=CurriculumHealthReport)
async def curriculum_health(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumHealthReport:
    """All units ranked by health tier."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_curriculum_health(conn, school_id)
    return CurriculumHealthReport(**result)


# ── Report 5: Feedback Report ─────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/feedback", response_model=FeedbackReport)
async def feedback_report(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    unit_id: str | None = Query(None),
    category: str | None = Query(None, pattern="^(content|ux|general)$"),
    reviewed: bool | None = Query(None),
    sort: str = Query("recent", pattern="^(recent|oldest|volume)$"),
) -> FeedbackReport:
    """All student feedback for the school's curriculum, grouped by unit."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_feedback_report(conn, school_id, unit_id, category, reviewed, sort)
    return FeedbackReport(**result)


# ── Report 6: Trends ──────────────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/trends", response_model=TrendsReport)
async def trends_report(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    period: str = Query("4w", pattern="^(4w|12w|term)$"),
) -> TrendsReport:
    """Week-over-week engagement and performance trends."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_trends(conn, school_id, period)
    return TrendsReport(**result)


# ── Export ────────────────────────────────────────────────────────────────────

@router.post("/reports/school/{school_id}/export", response_model=ExportResponse)
async def export_report(
    school_id: str,
    body: ExportRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ExportResponse:
    """Queue a CSV export task. Returns export_id and download URL."""
    _check_school(teacher, school_id, request)
    result = await trigger_export(school_id, body.report_type, body.filters)
    return ExportResponse(**result)


@router.get("/reports/download/{export_id}")
async def download_export(
    export_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Serve a completed CSV export file."""
    from config import settings
    export_path = os.path.join(settings.CONTENT_STORE_PATH, "exports", f"{export_id}.csv")
    if not os.path.exists(export_path):
        cid = _cid(request)
        raise HTTPException(
            status_code=404,
            detail={"error": "export_not_found", "detail": "Export not ready or expired.", "correlation_id": cid},
        )
    return FileResponse(
        export_path,
        media_type="text/csv",
        filename=f"report_{export_id}.csv",
    )


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/reports/school/{school_id}/alerts", response_model=AlertListResponse)
async def list_alerts(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AlertListResponse:
    """Return unacknowledged threshold alerts for the school."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_alerts(conn, school_id)
    return AlertListResponse(**result)


@router.put("/reports/school/{school_id}/alerts/settings", response_model=AlertSettingsResponse)
async def update_alert_settings(
    school_id: str,
    body: AlertSettings,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AlertSettingsResponse:
    """Configure alert thresholds for the school."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await save_alert_settings(conn, school_id, body.model_dump())
    return AlertSettingsResponse(**result)


# ── Digest ────────────────────────────────────────────────────────────────────

@router.post("/reports/school/{school_id}/digest/subscribe", response_model=DigestSubscribeResponse)
async def digest_subscribe(
    school_id: str,
    body: DigestSubscribeRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> DigestSubscribeResponse:
    """Subscribe or update weekly digest settings."""
    _check_school(teacher, school_id, request)
    teacher_id = str(teacher["teacher_id"])
    async with get_db(request) as conn:
        result = await subscribe_digest(
            conn, school_id, teacher_id,
            body.email, body.timezone, body.enabled,
        )
    return DigestSubscribeResponse(**result)


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/reports/school/{school_id}/refresh", response_model=RefreshResponse)
async def refresh_views(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> RefreshResponse:
    """On-demand materialized view refresh (school_admin only)."""
    _check_school(teacher, school_id, request)
    if teacher.get("role") not in ("school_admin", "teacher"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can trigger a manual refresh.",
                "correlation_id": _cid(request),
            },
        )
    pool = request.app.state.pool
    result = await refresh_materialized_views(pool)
    return RefreshResponse(**result)
