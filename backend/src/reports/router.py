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
  GET  /reports/school/{school_id}/alerts
  PUT  /reports/school/{school_id}/alerts/settings
  POST /reports/school/{school_id}/digest/subscribe
  POST /reports/school/{school_id}/refresh

Security:
  All endpoints require teacher JWT.  School ownership enforced.
  POST /refresh requires school_admin role.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.grade_scope import grade_filter, permitted_grades
from src.core.redis_client import get_redis
from src.reports.schemas import (
    AlertListResponse,
    AlertSettings,
    AlertSettingsResponse,
    AtRiskListResponse,
    CurriculumHealthReport,
    DigestSubscribeRequest,
    DigestSubscribeResponse,
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

    Thin wrapper over `src.core.grade_scope` — the rule moved to core in #647
    after living here caused it to be missed by two endpoints, one of them in
    this very file (alerts). Kept as a local name so the ~20 call sites below
    read unchanged.
    """
    return await permitted_grades(conn, teacher, school_id)


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
    return await grade_filter(conn, teacher, school_id)


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

    # Import here to avoid circular dependencies.
    from src.core.subjects import display_subject, resolve_subject_labels

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
                MAX(ps.started_at)                                  AS last_active,
                STRING_AGG(DISTINCT cu.unit_id, ', ' ORDER BY cu.unit_id) AS unit_ids,
                STRING_AGG(DISTINCT c.name, ', ' ORDER BY c.name) AS curriculum_names
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
            LEFT JOIN classroom_students cs ON cs.student_id = s.student_id
            LEFT JOIN classroom_packages cp ON cp.classroom_id = cs.classroom_id
            LEFT JOIN curriculum_units cu ON cu.curriculum_id = cp.curriculum_id
            LEFT JOIN curricula c ON c.curriculum_id = cp.curriculum_id
            WHERE se.school_id = $1 AND se.status = 'active' {grade_filter}
            GROUP BY s.student_id, s.name, s.grade
            ORDER BY s.name
            """,
            *params,
        )

        # Resolve human-readable subject names (same pattern as #839 fix for analytics).
        unit_ids = []
        for r in rows:
            if r["unit_ids"]:
                unit_ids.extend(r["unit_ids"].split(", "))
        subject_labels = await resolve_subject_labels(conn, list(set(unit_ids))) if unit_ids else {}

    # The denominator is each student's OWN curriculum, resolved the same way
    # their content is (#638). Summing every default curriculum at their grade
    # measured a Grade 11 student against four streams at once.
    totals = await total_units_by_student(
        request.app.state.pool, get_redis(request), rows, school_id
    )

    students = []
    log.warning("roster_debug", extra={"num_rows": len(rows), "subject_labels_size": len(subject_labels)})
    for r in rows:
        # Aggregate display names from the unit_ids for this student's curricula.
        subject_names = set()
        if r["unit_ids"]:
            for uid in r["unit_ids"].split(", "):
                # subject_labels keys are unit_ids; we don't have raw subject values here
                # because we're pulling from curriculum_units. Use the unit's resolved name.
                display = display_subject(subject_labels, uid, None)
                subject_names.add(display)
        # Fallback to curriculum names if no units found. This handles cases where
        # a curriculum has no units (edge case) or provides readable names.
        if not subject_names and r["curriculum_names"]:
            subject_names = set(n.strip() for n in r["curriculum_names"].split(", ") if n.strip())
        subject_str = ", ".join(sorted(subject_names)) if subject_names else None
        log.warning("roster_student", extra={"name": r["student_name"], "unit_ids_count": len(r["unit_ids"].split(", ")) if r["unit_ids"] else 0, "subject": subject_str})

        students.append(
            {
                "student_id": str(r["student_id"]),
                "student_name": r["student_name"],
                "grade": r["grade"],
                "subject": subject_str,
                "units_completed": int(r["units_completed"]),
                "total_units": totals.get(str(r["student_id"]), 0),
                "avg_score_pct": round(float(r["avg_score_pct"] or 0), 1),
                "last_active": r["last_active"].isoformat() if r["last_active"] else None,
            }
        )
    return {"school_id": school_id, "grade": grade, "subject": None, "students": students}


# ── Report 1: Class Overview ──────────────────────────────────────────────────


@router.get("/reports/school/{school_id}/overview", response_model=OverviewReport)
async def overview_report(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    period: str = Query("7d", pattern="^(7d|30d|term)$"),
    grade: int | None = Query(None),
    subject: str | None = Query(None, max_length=128),
) -> OverviewReport:
    """Class overview summary for the selected period, optionally narrowed.

    `?grade=` is a filter WITHIN the caller's entitlement and is refused, not
    ignored, when it names a grade they do not teach — the same rule and the
    same 403 as every other report here.

    `?subject=` needs no such check: it narrows the unit LISTS within a cohort
    that is already scoped, so a subject the caller cannot see contributes no
    units and is not offered in `available_subjects`.
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        permitted = await _permitted_grades(conn, teacher, school_id)
        if grade is not None and permitted is not None and grade not in permitted:
            raise _deny_grade(request)
        grades = None if permitted is None else sorted(permitted)
        result = await get_overview(
            conn,
            school_id,
            period,
            grades,
            pool=request.app.state.pool,
            redis=get_redis(request),
            grade=grade,
            subject=subject,
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
            result = await get_student_report(
                conn, school_id, student_id, request.app.state.pool, get_redis(request)
            )
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
    grade: int | None = None,
    stream: str | None = Query(None, max_length=64),
) -> CurriculumHealthReport:
    """All units ranked by health tier, optionally narrowed to one grade/stream.

    `?grade=` is a filter WITHIN the caller's entitlement, never a way around
    it: a grade the caller is not assigned to is refused with the same 403 the
    roster uses, rather than being silently ignored. Silently ignoring it would
    be worse than refusing — the teacher would read a school-wide report while
    the control on screen said "Grade 7".

    `?stream=` is the same kind of filter and carries the same rule. It needs no
    separate 403: a stream is a property of the curricula the COHORT resolves
    to, and the cohort is already scoped to the caller's grades before any
    stream narrowing happens — so a stream the caller cannot see contributes no
    students and is not offered in `available_streams`. Selecting one anyway
    yields an empty report rather than another school's data.
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        permitted = await _permitted_grades(conn, teacher, school_id)
        if grade is not None and permitted is not None and grade not in permitted:
            raise _deny_grade(request)
        # `_grade_filter` is `sorted(_permitted_grades)`, so deriving it here
        # saves a second identical query AND makes the check and the scope
        # provably the same set — calling both would let a refusal be decided
        # against one read of the assignments and the report built from another.
        grades = None if permitted is None else sorted(permitted)
        result = await get_curriculum_health(
            conn,
            school_id,
            grades,
            pool=request.app.state.pool,
            redis=get_redis(request),
            grade=grade,
            stream=stream,
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
    grade: int | None = Query(None),
    stream: str | None = Query(None, max_length=64),
) -> FeedbackReport:
    """A page of student feedback for the school, newest first by default.

    Paginated since #611: the report previously returned every item ever
    recorded, so the response grew without bound as a school accumulated
    feedback.

    `?grade=` is a filter WITHIN the caller's entitlement and is refused, not
    ignored, when it names a grade they do not teach — the same rule and the
    same 403 as the roster and the curriculum-health report. `?stream=` needs
    no separate check: the cohort is scoped to the caller's grades before any
    stream narrowing, so a stream they cannot see contributes no students.
    """
    _check_school(teacher, school_id, request)
    async with get_db(request) as conn:
        permitted = await _permitted_grades(conn, teacher, school_id)
        if grade is not None and permitted is not None and grade not in permitted:
            raise _deny_grade(request)
        result = await get_feedback_report(
            conn,
            school_id,
            unit_id=unit_id,
            category=category,
            reviewed=reviewed,
            sort=sort,
            page=page,
            page_size=page_size,
            allowed_grades=None if permitted is None else sorted(permitted),
            pool=request.app.state.pool,
            redis=get_redis(request),
            grade=grade,
            stream=stream,
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
        # Scoped to the caller's grades (#647): alerts filtered on school
        # alone, so a Grade-8 teacher's landing page listed breaches for
        # Grades 5, 10 and 11.
        grades = await _grade_filter(conn, teacher, school_id)
        result = await get_alerts(conn, school_id, grades)
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
