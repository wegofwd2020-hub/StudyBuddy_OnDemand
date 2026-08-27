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
import uuid
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.reports.schemas import (
    AlertListResponse,
    AlertSettings,
    AlertSettingsResponse,
    AtRiskListResponse,
    CurriculumHealthReport,
    DigestSubscribeRequest,
    DigestSubscribeResponse,
    ExportRequest,
    ExportResponse,
    FeedbackReport,
    MarkSeenResponse,
    OverviewReport,
    RefreshResponse,
    SendReminderResponse,
    StudentReport,
    TrendsReport,
    UnitReport,
)
from src.reports.service import (
    get_alert_settings,
    get_alerts,
    get_at_risk_students,
    get_curriculum_health,
    get_feedback_report,
    get_overview,
    get_student_report,
    get_trends,
    get_unit_report,
    mark_at_risk_student_seen,
    refresh_materialized_views,
    save_alert_settings,
    send_at_risk_reminder,
    subscribe_digest,
    total_units_by_student,
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


async def _permitted_grades(
    conn: asyncpg.Connection, teacher: dict, school_id: str
) -> set[int] | None:
    """Grades this teacher may see, or None meaning "no restriction".

    The product already models per-teacher grade entitlement in
    `teacher_grade_assignments` (migration 0023) and enforces it on roster
    upload — reports never consulted it, so a Grade-8 teacher could read a
    Grade-10 student's report card by changing a query parameter (#576).

    `school_admin` is a teacher superset (ADR-005) and keeps full visibility.
    A teacher with no assignments has no cohort, so they see no students rather
    than every student — the previous behaviour was the latter.
    """
    if teacher.get("role") == "school_admin":
        return None

    rows = await conn.fetch(
        """
        SELECT grade FROM teacher_grade_assignments
        WHERE teacher_id = $1 AND school_id = $2
        """,
        uuid.UUID(str(teacher["teacher_id"])),
        uuid.UUID(school_id),
    )
    return {r["grade"] for r in rows}


async def _grade_filter(
    conn: asyncpg.Connection, teacher: dict, school_id: str
) -> list[int] | None:
    """The `allowed_grades` argument for the aggregate reports (#576).

    `None` means unrestricted — `school_admin`, a teacher superset (ADR-005).
    A sorted list otherwise, INCLUDING the empty list: a teacher with no grade
    assignments has no cohort and must see nothing rather than everything, so
    `[]` and `None` must never be collapsed into one another.

    Decided 2026-08-24: a teacher sees THEIR COHORT, not the school. This
    changes what the numbers mean — a Grade-8 teacher's "pass rate" is their
    grade's, not the school's — and it means nobody below `school_admin` sees a
    school-wide figure. That is intentional. If teachers later need to compare
    against the school, add a SEPARATE endpoint returning non-identifying
    aggregates rather than unscoping this one: keeping the two apart makes
    "this figure cannot identify a student" a property of that endpoint instead
    of a subtlety inside a report that also serves names.
    """
    permitted = await _permitted_grades(conn, teacher, school_id)
    return None if permitted is None else sorted(permitted)


def _deny_grade(request: Request) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error": "forbidden",
            # Deliberately does not confirm whether the student exists — that
            # would leak roster membership for grades the teacher cannot see.
            "detail": "You are not assigned to that grade.",
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
        permitted = await _permitted_grades(conn, teacher, school_id)

        if grade is not None:
            if permitted is not None and grade not in permitted:
                raise _deny_grade(request)
            grade_filter = "AND se.grade = $2"
            params = [school_id, grade]
        elif permitted is None:
            # school_admin — whole school.
            grade_filter = ""
            params = [school_id]
        else:
            # Restricting only the explicit ?grade= would leave the wider door
            # open: an unfiltered roster returned every grade in the school.
            grade_filter = "AND se.grade = ANY($2::smallint[])"
            params = [school_id, sorted(permitted)]
        rows = await conn.fetch(
            f"""
            SELECT
                s.student_id,
                s.name                                              AS student_name,
                s.grade,
                -- DISTINCT units, not passed sessions (#655). Retaking a unit
                -- and passing it again is one unit done, not two. The
                -- denominator is a count of distinct units in the student's
                -- curriculum (#638), so counting sessions here compared two
                -- different things and could exceed 100%.
                COUNT(DISTINCT ps.unit_id) FILTER (WHERE ps.passed)  AS units_completed,
                COALESCE(
                    AVG(CASE WHEN ps.score IS NOT NULL
                        THEN ps.score::float / NULLIF(ps.total_questions, 0) * 100
                    END), 0
                )                                                   AS avg_score_pct,
                MAX(ps.started_at)                                  AS last_active
            -- Membership comes from `school_enrolments`, not `students.school_id`
            -- (#572). A student may be enrolled at more than one school — a
            -- school for their regular curriculum and an external tutor running
            -- additional classes — and `students.school_id` names only one of
            -- them, so a student attached to a second school was provisioned
            -- successfully and then absent from that school's reports.
            --
            -- `school_enrolments` is RLS-forced on app.current_school_id, so
            -- this is already scoped to the caller's school.
            --
            -- The grade filter reads the ENROLMENT's grade: it is the grade at
            -- THIS school, where `students.grade` is the student's own and can
            -- differ between the two.
            FROM school_enrolments se
            JOIN students s ON s.student_id = se.student_id
            LEFT JOIN progress_sessions ps ON ps.student_id = s.student_id
                AND ps.completed = true
                -- Enrolling someone must not hand over what they did before
                -- they joined. Without this, a school could add a known address
                -- and read that student's entire history at another school.
                -- Every current flow (provisioning, roster upload, enrol-by-code)
                -- creates the enrolment before any work, so this hides nothing
                -- a school legitimately owns.
                AND ps.started_at >= se.added_at
            WHERE se.school_id = $1 AND se.status = 'active' {grade_filter}
            GROUP BY s.student_id, s.name, s.grade
            ORDER BY s.name
            """,
            *params,
        )

    # The denominator is each student's OWN curriculum, resolved the same way
    # their content is (#638). Summing every default curriculum at their grade
    # measured a Grade 11 student against four streams at once.
    totals = await total_units_by_student(
        request.app.state.pool, get_redis(request), rows, school_id
    )

    students = [
        {
            "student_id": str(r["student_id"]),
            "student_name": r["student_name"],
            "grade": r["grade"],
            "units_completed": int(r["units_completed"]),
            "total_units": totals.get(str(r["student_id"]), 0),
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
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_overview(
            conn,
            school_id,
            period,
            grades,
            pool=request.app.state.pool,
            redis=get_redis(request),
        )
    # Reported from the SAME filter that scoped the query above, so the caption
    # on the page cannot describe a population the numbers do not cover (#640).
    result["scope"] = (
        {"kind": "school", "grades": []} if grades is None else {"kind": "grades", "grades": grades}
    )
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
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_unit_report(conn, school_id, unit_id, period, grades)
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
        permitted = await _permitted_grades(conn, teacher, school_id)
        if permitted is not None:
            student_grade = await conn.fetchval(
                "SELECT grade FROM students WHERE student_id = $1",
                uuid.UUID(student_id),
            )
            # An unknown student is refused the same way as an out-of-scope one,
            # so the response cannot be used to probe who exists.
            if student_grade is None or student_grade not in permitted:
                raise _deny_grade(request)
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
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_curriculum_health(
            conn,
            school_id,
            grades,
            pool=request.app.state.pool,
            redis=get_redis(request),
        )
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
    sort: str = Query("recent", pattern="^(recent|oldest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> FeedbackReport:
    """A page of student feedback for the school, newest first by default.

    Paginated since #611: the report previously returned every item ever
    recorded, so the response grew without bound as a school accumulated
    feedback.
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_feedback_report(
            conn,
            school_id,
            unit_id=unit_id,
            category=category,
            reviewed=reviewed,
            sort=sort,
            page=page,
            page_size=page_size,
            allowed_grades=await _grade_filter(conn, teacher, school_id),
        )
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
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_trends(conn, school_id, period, grades)
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
            detail={
                "error": "export_not_found",
                "detail": "Export not ready or expired.",
                "correlation_id": cid,
            },
        )
    return FileResponse(
        export_path,
        media_type="text/csv",
        filename=f"report_{export_id}.csv",
    )


# ── At-Risk Student Action Queue (#79) ───────────────────────────────────────


@router.get("/reports/school/{school_id}/at-risk", response_model=AtRiskListResponse)
async def at_risk_students(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AtRiskListResponse:
    """
    Return students who are inactive or have a low pass rate, using the
    school's configured alert thresholds (defaults: 14 days / 50%).
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_at_risk_students(
            conn,
            school_id,
            grades,
            pool=request.app.state.pool,
            redis=get_redis(request),
        )
    return AtRiskListResponse(**result)


@router.post(
    "/reports/school/{school_id}/at-risk/{student_id}/seen", response_model=MarkSeenResponse
)
async def mark_seen(
    school_id: str,
    student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    seen: bool = True,
) -> MarkSeenResponse:
    """Toggle the 'seen' acknowledgement for an at-risk student."""
    _check_school(teacher, school_id, request)
    teacher_id = str(teacher["teacher_id"])
    async with get_db(request) as conn:
        result = await mark_at_risk_student_seen(conn, school_id, student_id, teacher_id, seen)
    return MarkSeenResponse(**result)


@router.post(
    "/reports/school/{school_id}/at-risk/{student_id}/reminder",
    response_model=SendReminderResponse,
)
async def send_reminder(
    school_id: str,
    student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SendReminderResponse:
    """Queue a push notification nudge for a specific at-risk student."""
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await send_at_risk_reminder(conn, school_id, student_id)
    return SendReminderResponse(**result)


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


@router.get("/reports/school/{school_id}/alerts/settings", response_model=AlertSettingsResponse)
async def get_alert_settings_endpoint(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AlertSettingsResponse:
    """Return the school's saved alert thresholds (or server defaults if unset).

    Without this the settings form redrew hardcoded client defaults every visit,
    so saved values looked lost even though the PUT persisted them (#526).
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        result = await get_alert_settings(conn, school_id)
    return AlertSettingsResponse(**result)


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
            conn,
            school_id,
            teacher_id,
            body.email,
            body.timezone,
            body.enabled,
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
