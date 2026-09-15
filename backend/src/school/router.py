"""
backend/src/school/router.py

Phase 8–9 school endpoints.

Routes (all prefixed /api/v1 in main.py):

  POST /schools/register                        — create school + school_admin (public)
  GET  /schools/{school_id}                     — school profile (teacher-scoped)
  POST /schools/{school_id}/teachers/invite     — invite a teacher (school_admin only)
  POST /schools/{school_id}/enrolment           — upload student email roster (school_admin only)
  GET  /schools/{school_id}/enrolment           — get enrolment roster (school_admin only)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_student, get_current_teacher
from src.core.db import get_db
from src.core.events import emit_event, write_audit_log
from src.core.grade_scope import grade_filter
from src.core.permissions import has_any_curriculum_capability
from src.core.storage import get_storage
from src.school.capability_guards import (
    require_commission,
    require_curriculum_view,
    require_review,
)
from src.school.enrolment_service import (
    assign_student,
    get_roster,
    get_student_assignment,
    reassign_students_bulk,
    upload_roster,
)
from src.school.schemas import (
    AdoptCurriculumRequest,
    AdoptionItem,
    ApproveRequest,
    AssignPackageRequest,
    AssignStudentRequest,
    BulkReassignRequest,
    BulkReassignResponse,
    CapabilityGrantRequest,
    CatalogResponse,
    ClassroomCreateRequest,
    ClassroomDetailResponse,
    ClassroomItem,
    ClassroomPackageItem,
    ClassroomStudentItem,
    ClassroomUpdateRequest,
    CurriculumDefinitionRequest,
    CurriculumDefinitionResponse,
    DefinitionListResponse,
    EnrolConfirmRequest,
    EnrolConfirmResponse,
    EnrolmentRosterItem,
    EnrolmentRosterResponse,
    EnrolmentUploadRequest,
    EnrolmentUploadResponse,
    GradeScopeResponse,
    LibraryResponse,
    OverrideItem,
    PromoteTeacherResponse,
    ProvisionStudentRequest,
    ProvisionStudentResponse,
    ProvisionTeacherRequest,
    ProvisionTeacherResponse,
    RejectDefinitionRequest,
    RejectRequest,
    ReorderPackageRequest,
    ResetPasswordResponse,
    ReviewActionRequest,
    SaveDraftRequest,
    SchoolLLMConfigResponse,
    SchoolLLMConfigUpdateRequest,
    SchoolProfileResponse,
    SchoolRegisterRequest,
    SchoolRegisterResponse,
    SchoolThemeResponse,
    SchoolThemeUpdateRequest,
    SetupStatusResponse,
    StudentAssignmentRequest,
    StudentAssignmentResponse,
    TeacherCapabilitiesResponse,
    TeacherGradeAssignRequest,
    TeacherGradeAssignResponse,
    TeacherInviteRequest,
    TeacherInviteResponse,
    TeacherRosterResponse,
    UpdateAdoptionRequest,
)
from src.school.service import (
    AlreadyEnrolledError,
    NotPrimarySchoolError,
    approve_definition,
    assign_package_to_classroom,
    assign_student_to_classroom,
    create_classroom,
    enrol_student_by_code,
    fetch_school,
    get_classroom_detail,
    get_definition,
    get_llm_config,
    get_school_theme,
    get_setup_status,
    get_student_school_theme,
    invite_teacher,
    list_catalog,
    list_classrooms,
    list_definitions,
    promote_to_school_admin,
    provision_student,
    provision_teacher,
    register_school,
    reject_definition,
    remove_package_from_classroom,
    remove_student_from_classroom,
    reorder_package_in_classroom,
    reset_student_password,
    reset_teacher_password,
    submit_definition,
    update_classroom,
    update_llm_config,
    update_school_theme,
)
from src.school.subscription_service import get_seat_usage
from src.utils.logger import get_logger

log = get_logger("school")
router = APIRouter(tags=["school"])

# Unique constraints that genuinely mean "this email is taken" — used to keep
# registration conflicts honest about which field actually clashed (#597).
_EMAIL_UNIQUE_CONSTRAINTS = frozenset(
    {"uq_schools_contact_email", "teachers_email_key", "students_email_key"}
)


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── School registration (public — no JWT required) ────────────────────────────


@router.post(
    "/schools/register",
    response_model=SchoolRegisterResponse,
    status_code=201,
)
async def register_school_endpoint(
    body: SchoolRegisterRequest,
    request: Request,
) -> SchoolRegisterResponse:
    """
    Register a new school.

    Auto-approves the school and creates a school_admin teacher account.
    Returns an access token for immediate use.
    """
    async with get_db(request) as conn:
        try:
            result = await register_school(
                conn, body.school_name, body.contact_email, body.country, body.password
            )
        except asyncpg.UniqueViolationError as exc:
            # Branch on the constraint, never on a substring of the error text:
            # every unique violation used to be reported as a duplicate email,
            # so an enrolment-code clash told a school its address was taken
            # and sent it retrying with addresses that were never the problem
            # (issue #597).
            if exc.constraint_name == "schools_enrolment_code_key":
                message = (
                    "Could not allocate a unique enrolment code. Please try registering again."
                )
            elif exc.constraint_name in _EMAIL_UNIQUE_CONSTRAINTS:
                message = "A school or account with that email already exists."
            else:
                message = "That registration conflicts with an existing record."
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": message,
                    "correlation_id": _cid(request),
                },
            )
    return SchoolRegisterResponse(**result)


# ── School profile ────────────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}",
    response_model=SchoolProfileResponse,
)
async def get_school_profile(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolProfileResponse:
    """Return the profile for the teacher's school."""
    async with get_db(request) as conn:
        school = await fetch_school(conn, school_id, teacher["school_id"])
    if not school:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "School not found.",
                "correlation_id": _cid(request),
            },
        )
    return SchoolProfileResponse(**school)


# ── Setup status (Layer 1.5 onboarding checklist) ────────────────────────────


@router.get(
    "/schools/{school_id}/setup-status",
    response_model=SetupStatusResponse,
)
async def get_setup_status_endpoint(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SetupStatusResponse:
    """
    Return the school's first-run setup progress.

    Reports whether the admin has completed each of the four required steps:
    add a teacher, enrol a student, create a classroom, assign a curriculum.
    Used by the dashboard SetupChecklist banner.
    """
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can view setup status.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view setup status for a different school.",
                "correlation_id": _cid(request),
            },
        )
    async with get_db(request) as conn:
        status = await get_setup_status(conn, school_id)
    return SetupStatusResponse(**status)


# ── Teacher invite ────────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/teachers/invite",
    response_model=TeacherInviteResponse,
    status_code=201,
)
async def invite_teacher_endpoint(
    school_id: str,
    body: TeacherInviteRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherInviteResponse:
    """Invite a new teacher to the school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can invite teachers.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot invite to a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        # Seat limit check — only enforced if school has an active subscription
        sub_row = await conn.fetchrow(
            """
            SELECT max_teachers FROM school_subscriptions
            WHERE school_id = $1 AND status IN ('active', 'trialing')
            """,
            _uuid.UUID(school_id),
        )
        if sub_row is not None:
            usage = await get_seat_usage(conn, school_id)
            if usage["seats_used_teachers"] >= sub_row["max_teachers"]:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "seat_limit_reached",
                        "detail": "Teacher seat limit reached for this plan.",
                        "limit": sub_row["max_teachers"],
                        "correlation_id": _cid(request),
                    },
                )
        try:
            result = await invite_teacher(conn, school_id, body.name, body.email)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "Teacher email already registered.",
                        "correlation_id": _cid(request),
                    },
                )
            raise
    return TeacherInviteResponse(**result)


# ── Enrolment roster upload ───────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/enrolment",
    response_model=EnrolmentUploadResponse,
    status_code=201,
)
async def upload_enrolment_roster(
    school_id: str,
    body: EnrolmentUploadRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> EnrolmentUploadResponse:
    """Upload a student email roster for the school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can upload rosters.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot manage enrolment for a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        # Seat limit check — only enforced if school has an active subscription
        sub_row = await conn.fetchrow(
            """
            SELECT max_students FROM school_subscriptions
            WHERE school_id = $1 AND status IN ('active', 'trialing')
            """,
            _uuid.UUID(school_id),
        )
        if sub_row is not None:
            usage = await get_seat_usage(conn, school_id)
            incoming = len(body.students)
            if usage["seats_used_students"] + incoming > sub_row["max_students"]:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "seat_limit_reached",
                        "detail": "Enrolling these students would exceed the plan seat limit.",
                        "limit": sub_row["max_students"],
                        "used": usage["seats_used_students"],
                        "correlation_id": _cid(request),
                    },
                )
        entries = [e.model_dump() for e in body.students]
        result = await upload_roster(conn, school_id, entries)
    return EnrolmentUploadResponse(**result)


# ── Enrolment roster read ─────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}/enrolment",
    response_model=EnrolmentRosterResponse,
)
async def get_enrolment_roster(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> EnrolmentRosterResponse:
    """Fetch the student enrolment roster for a school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can view rosters.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view enrolment for a different school.",
                "correlation_id": _cid(request),
            },
        )
    async with get_db(request) as conn:
        rows = await get_roster(conn, school_id)
    return EnrolmentRosterResponse(roster=[EnrolmentRosterItem(**r) for r in rows])


# ── Student-teacher assignment ────────────────────────────────────────────────


def _require_school_admin(teacher: dict, school_id: str, request: Request) -> None:
    """Raise 403 if caller is not school_admin for the given school."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can manage student assignments.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot manage assignments for a different school.",
                "correlation_id": _cid(request),
            },
        )


@router.get(
    "/schools/{school_id}/students/{student_id}/assignment",
    response_model=StudentAssignmentResponse,
)
async def get_student_assignment_endpoint(
    school_id: str,
    student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> StudentAssignmentResponse:
    """Return the current teacher assignment for a student (teacher-scoped)."""
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view assignments for a different school.",
                "correlation_id": _cid(request),
            },
        )
    async with get_db(request) as conn:
        row = await get_student_assignment(conn, school_id, student_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "No assignment found for this student.",
                "correlation_id": _cid(request),
            },
        )
    return StudentAssignmentResponse(**row)


@router.put(
    "/schools/{school_id}/students/{student_id}/assignment",
    response_model=StudentAssignmentResponse,
)
async def set_student_assignment_endpoint(
    school_id: str,
    student_id: str,
    body: StudentAssignmentRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> StudentAssignmentResponse:
    """
    Set or replace a student's grade+teacher assignment (school_admin only).

    The school is the sole authority on which grade and teacher a student belongs to.
    """
    _require_school_admin(teacher, school_id, request)
    async with get_db(request) as conn:
        try:
            row = await assign_student(
                conn,
                school_id,
                student_id,
                body.grade,
                body.teacher_id,
                assigned_by=teacher["teacher_id"],
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "assignment_invalid",
                    "detail": str(exc),
                    "correlation_id": _cid(request),
                },
            )
    return StudentAssignmentResponse(**row)


@router.post(
    "/schools/{school_id}/teachers/{from_teacher_id}/reassign",
    response_model=BulkReassignResponse,
)
async def bulk_reassign_students_endpoint(
    school_id: str,
    from_teacher_id: str,
    body: BulkReassignRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> BulkReassignResponse:
    """
    Move all students in a grade from one teacher to another (school_admin only).
    Used when a teacher leaves or a class is restructured.
    """
    _require_school_admin(teacher, school_id, request)
    async with get_db(request) as conn:
        try:
            count = await reassign_students_bulk(
                conn,
                school_id,
                from_teacher_id,
                body.to_teacher_id,
                body.grade,
                assigned_by=teacher["teacher_id"],
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "reassign_invalid",
                    "detail": str(exc),
                    "correlation_id": _cid(request),
                },
            )
    return BulkReassignResponse(reassigned=count)


# ── Teacher roster ────────────────────────────────────────────────────────────


@router.get("/schools/{school_id}/teachers", response_model=TeacherRosterResponse)
async def list_teachers(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherRosterResponse:
    """List all teachers in the school with their assigned grades."""
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view teachers for a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT t.teacher_id::text, t.name, t.email, t.role,
                   t.account_status::text,
                   COALESCE(
                       array_agg(DISTINCT tga.grade ORDER BY tga.grade)
                       FILTER (WHERE tga.grade IS NOT NULL), '{}'
                   ) AS assigned_grades,
                   COALESCE(
                       array_agg(DISTINCT tc.capability)
                       FILTER (WHERE tc.capability IS NOT NULL), '{}'
                   ) AS capabilities
            FROM teachers t
            LEFT JOIN teacher_grade_assignments tga
                ON tga.teacher_id = t.teacher_id
            LEFT JOIN teacher_capabilities tc
                ON tc.teacher_id = t.teacher_id
            WHERE t.school_id = $1
            GROUP BY t.teacher_id, t.name, t.email, t.role, t.account_status
            ORDER BY t.name
            """,
            _uuid.UUID(school_id),
        )
    return TeacherRosterResponse(
        teachers=[
            {
                "teacher_id": r["teacher_id"],
                "name": r["name"],
                "email": r["email"],
                "role": r["role"],
                "account_status": r["account_status"],
                "assigned_grades": list(r["assigned_grades"]),
                "capabilities": sorted(r["capabilities"]),
            }
            for r in rows
        ]
    )


# ── Teacher grade assignment ───────────────────────────────────────────────────


@router.put(
    "/schools/{school_id}/teachers/{teacher_id}/grades",
    response_model=TeacherGradeAssignResponse,
)
async def assign_teacher_grades(
    school_id: str,
    teacher_id: str,
    body: TeacherGradeAssignRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherGradeAssignResponse:
    """Replace the grade assignments for a teacher (any teacher in the school)."""
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot manage teachers for a different school.",
                "correlation_id": _cid(request),
            },
        )
    # Validate grades
    invalid = [g for g in body.grades if g < 5 or g > 12]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_grades",
                "detail": f"Grades must be between 5 and 12. Invalid: {invalid}",
                "correlation_id": _cid(request),
            },
        )

    import uuid as _uuid

    tid = _uuid.UUID(teacher_id)
    sid = _uuid.UUID(school_id)

    async with get_db(request) as conn:
        # Verify the teacher belongs to this school
        exists = await conn.fetchval(
            "SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $2",
            tid,
            sid,
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Teacher not found in this school.",
                    "correlation_id": _cid(request),
                },
            )
        async with conn.transaction():
            await conn.execute("DELETE FROM teacher_grade_assignments WHERE teacher_id = $1", tid)
            if body.grades:
                await conn.executemany(
                    """
                    INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (teacher_id, grade) DO NOTHING
                    """,
                    [(tid, sid, g) for g in body.grades],
                )

    log.info(
        "teacher_grades_assigned",
        teacher_id=teacher_id,
        school_id=school_id,
        grades=sorted(body.grades),
    )
    return TeacherGradeAssignResponse(
        teacher_id=teacher_id,
        school_id=school_id,
        assigned_grades=sorted(body.grades),
    )


# ── Curriculum-management capabilities (issue #358) ──────────────────────────


@router.put(
    "/schools/{school_id}/teachers/{teacher_id}/capabilities",
    response_model=TeacherCapabilitiesResponse,
)
async def set_teacher_capabilities(
    school_id: str,
    teacher_id: str,
    body: CapabilityGrantRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherCapabilitiesResponse:
    """Replace a teacher's curriculum capabilities (school_admin only).

    Full-replace set semantics: the request body is the complete desired set, so
    sending `[]` revokes all. Unknown capabilities are rejected (422) at the
    schema layer. school_admin is an implicit superset and never needs a grant.
    """
    _require_school_admin(teacher, school_id, request)

    import uuid as _uuid

    tid = _uuid.UUID(teacher_id)
    sid = _uuid.UUID(school_id)
    granted_by = _uuid.UUID(teacher["teacher_id"])

    async with get_db(request) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $2", tid, sid
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Teacher not found in this school.",
                    "correlation_id": _cid(request),
                },
            )
        async with conn.transaction():
            await conn.execute("DELETE FROM teacher_capabilities WHERE teacher_id = $1", tid)
            if body.capabilities:
                await conn.executemany(
                    """
                    INSERT INTO teacher_capabilities (teacher_id, school_id, capability, granted_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (teacher_id, capability) DO NOTHING
                    """,
                    [(tid, sid, cap, granted_by) for cap in body.capabilities],
                )

    emit_event(
        "school",
        "capabilities_changed",
        school_id=school_id,
        teacher_id=teacher_id,
        capabilities=body.capabilities,
    )
    write_audit_log(
        event_type="teacher.capabilities_changed",
        actor_type="teacher",
        actor_id=granted_by,
        target_type="teacher",
        target_id=tid,
        metadata={"capabilities": body.capabilities, "school_id": school_id},
    )
    return TeacherCapabilitiesResponse(teacher_id=teacher_id, capabilities=body.capabilities)


@router.get(
    "/schools/{school_id}/teachers/{teacher_id}/capabilities",
    response_model=TeacherCapabilitiesResponse,
)
async def get_teacher_capabilities(
    school_id: str,
    teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherCapabilitiesResponse:
    """Read a teacher's curriculum capabilities (school_admin only)."""
    _require_school_admin(teacher, school_id, request)

    import uuid as _uuid

    async with get_db(request) as conn:
        rows = await conn.fetch(
            "SELECT capability FROM teacher_capabilities WHERE teacher_id = $1",
            _uuid.UUID(teacher_id),
        )
    return TeacherCapabilitiesResponse(
        teacher_id=teacher_id, capabilities=sorted(r["capability"] for r in rows)
    )


# ── Phase A provisioning endpoints ───────────────────────────────────────────


async def _duplicate_email_detail(
    conn: asyncpg.Connection,
    school_id: str,
    email: str,
    table: str,
) -> str:
    """Explain a duplicate-email conflict in a way the admin can act on (#572).

    `students.email` and `teachers.email` are globally unique, so an address
    registered at ANY school blocks it everywhere. The old wording — "A student
    with that email already exists." — left a school admin with no idea the
    address was in use elsewhere, no way to find out (correctly: that is another
    school's data), and nothing to do next.

    Two cases, deliberately worded differently:
      - the clash is on THIS school's roster -> name it; the admin can fix it
      - the clash is elsewhere               -> say the address is taken across
                                                StudyBuddy and give a contact
                                                route, revealing nothing about
                                                the other school
    """
    owned_here = await conn.fetchval(
        f"SELECT EXISTS (SELECT 1 FROM {table} WHERE lower(email) = lower($1) AND school_id = $2)",
        email,
        uuid.UUID(school_id),
    )
    if owned_here:
        who = "student" if table == "students" else "teacher"
        return f"That email address is already used by a {who} at your school."

    return (
        "That email address is already registered on StudyBuddy, so it cannot be "
        "added again. It may belong to an account at another school, which we "
        "cannot show you. Use a different address for this person, or contact "
        "support@usestudybuddy.com to have the address released."
    )


@router.post(
    "/schools/{school_id}/teachers",
    response_model=ProvisionTeacherResponse,
    status_code=201,
)
async def provision_teacher_endpoint(
    school_id: str,
    body: ProvisionTeacherRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ProvisionTeacherResponse:
    """
    Create a teacher account with a system-generated default password (school_admin only).

    Sends a welcome email with temporary credentials.
    Teacher is set to first_login=True and must reset their password on first use.
    """
    _require_school_admin(teacher, school_id, request)

    from src.email.service import send_welcome_teacher_email

    async with get_db(request) as conn:
        try:
            result = await provision_teacher(
                conn, school_id, body.name, str(body.email), body.subject_specialisation
            )
        except asyncpg.UniqueViolationError as exc:
            # Branch on the constraint, never a substring of the error text:
            # teachers.email and students.email are separate constraints (#578),
            # so guessing which one fired produces a message that is simply wrong.
            if exc.constraint_name != "teachers_email_key":
                raise
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": await _duplicate_email_detail(
                        conn, school_id, str(body.email), "teachers"
                    ),
                    "correlation_id": _cid(request),
                },
            )

    try:
        await send_welcome_teacher_email(
            result["email"], result["name"], result["default_password"]
        )
    except Exception:
        log.warning("welcome_email_failed", teacher_id=result["teacher_id"])

    return ProvisionTeacherResponse(
        teacher_id=result["teacher_id"],
        school_id=result["school_id"],
        name=result["name"],
        email=result["email"],
        role=result["role"],
    )


@router.post(
    "/schools/{school_id}/students",
    response_model=ProvisionStudentResponse,
    status_code=201,
)
async def provision_student_endpoint(
    school_id: str,
    body: ProvisionStudentRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ProvisionStudentResponse:
    """
    Create a student account with a system-generated default password (school_admin only).

    Sends a welcome email with temporary credentials.
    Student is set to first_login=True and must reset their password on first use.
    """
    _require_school_admin(teacher, school_id, request)

    from src.email.service import send_welcome_student_email

    async with get_db(request) as conn:
        try:
            result = await provision_student(
                conn, school_id, body.name, str(body.email), body.grade
            )
        except AlreadyEnrolledError:
            # Already on THIS roster. Since #572 a student may hold enrolments
            # at several schools, so a duplicate is only a conflict within one
            # school — and here the admin can see and fix it themselves.
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": (
                        "That student is already on your roster. "
                        "Check your student list for their existing record."
                    ),
                    "correlation_id": _cid(request),
                },
            )
        except asyncpg.UniqueViolationError as exc:
            if exc.constraint_name != "students_email_key":
                raise
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": await _duplicate_email_detail(
                        conn, school_id, str(body.email), "students"
                    ),
                    "correlation_id": _cid(request),
                },
            )

    # Only a newly created account has credentials to send. Attaching an
    # existing person to an additional school must not mail them anything
    # credential-shaped: they already have a password, and this school neither
    # set it nor may reset it.
    if result.get("default_password"):
        try:
            await send_welcome_student_email(
                result["email"], result["name"], result["default_password"]
            )
        except Exception:
            log.warning("welcome_email_failed", student_id=result["student_id"])

    return ProvisionStudentResponse(
        student_id=result["student_id"],
        school_id=result["school_id"],
        name=result["name"],
        email=result["email"],
        grade=result["grade"],
    )


@router.post(
    "/schools/{school_id}/teachers/{target_teacher_id}/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_teacher_password_endpoint(
    school_id: str,
    target_teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ResetPasswordResponse:
    """
    Generate a new default password for a teacher and email it to them (school_admin only).

    Sets first_login=True — the teacher must reset again on next login.
    """
    _require_school_admin(teacher, school_id, request)

    from src.email.service import send_password_reset_email

    async with get_db(request) as conn:
        result = await reset_teacher_password(conn, school_id, target_teacher_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Teacher not found in this school.",
                "correlation_id": _cid(request),
            },
        )

    try:
        await send_password_reset_email(result["email"], result["name"], result["default_password"])
    except Exception:
        log.warning("reset_email_failed", teacher_id=target_teacher_id)

    return ResetPasswordResponse(
        detail="Password reset.",
        temp_password=result["default_password"],
    )


@router.post(
    "/schools/{school_id}/students/{target_student_id}/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_student_password_endpoint(
    school_id: str,
    target_student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ResetPasswordResponse:
    """
    Generate a new default password for a student and email it to them (school_admin only).

    Sets first_login=True — the student must reset again on next login.
    """
    _require_school_admin(teacher, school_id, request)

    from src.email.service import send_password_reset_email

    async with get_db(request) as conn:
        try:
            result = await reset_student_password(conn, school_id, target_student_id)
        except NotPrimarySchoolError as exc:
            # 409, not 404: the student IS on this roster, so a "not found" was
            # both wrong and unactionable — the UI rendered it as "Reset failed.
            # Please try again.", which invited retrying something that can
            # never succeed here (#665).
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "not_primary_school",
                    "detail": (
                        f"{exc} manages this student's sign-in details. "
                        "Ask them to reset the password."
                    ),
                    "correlation_id": _cid(request),
                },
            )

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Student not found in this school.",
                "correlation_id": _cid(request),
            },
        )

    try:
        await send_password_reset_email(result["email"], result["name"], result["default_password"])
    except Exception:
        log.warning("reset_email_failed", student_id=target_student_id)

    return ResetPasswordResponse(
        detail="Password reset.",
        temp_password=result["default_password"],
    )


@router.post(
    "/schools/{school_id}/teachers/{target_teacher_id}/promote",
    response_model=PromoteTeacherResponse,
)
async def promote_teacher_endpoint(
    school_id: str,
    target_teacher_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> PromoteTeacherResponse:
    """
    Promote a teacher to the school_admin role (school_admin only).

    Multiple people can hold school_admin per school for backup coverage (Q18).
    """
    _require_school_admin(teacher, school_id, request)

    async with get_db(request) as conn:
        result = await promote_to_school_admin(conn, school_id, target_teacher_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Teacher not found in this school.",
                "correlation_id": _cid(request),
            },
        )

    return PromoteTeacherResponse(**result)


# ── Phase B — Classroom endpoints ────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/classrooms",
    response_model=ClassroomItem,
    status_code=201,
)
async def create_classroom_endpoint(
    school_id: str,
    body: ClassroomCreateRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ClassroomItem:
    """
    Create a classroom (school_admin or teacher).

    Any teacher at the school may create a classroom; a school_admin can create
    one and assign it to any teacher.  The lead teacher_id is optional.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        result = await create_classroom(
            conn,
            school_id,
            body.name,
            body.grade,
            body.teacher_id,
        )

    return ClassroomItem(
        classroom_id=result["classroom_id"],
        school_id=result["school_id"],
        teacher_id=result.get("teacher_id"),
        teacher_name=None,
        name=result["name"],
        grade=result.get("grade"),
        status=result["status"],
        created_at=result.get("created_at") or __import__("datetime").datetime.utcnow(),
        student_count=0,
        package_count=0,
    )


@router.get("/schools/{school_id}/my-grade-scope", response_model=GradeScopeResponse)
async def my_grade_scope(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> GradeScopeResponse:
    """Which grades the caller may see (#647 follow-up).

    Served once rather than embedded in every list response, because scope is a
    property of the caller. Pages use it to explain an empty list instead of
    asserting something false about the school — see GradeScopeResponse.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        grades = await grade_filter(conn, teacher, school_id)

    return GradeScopeResponse(
        kind="school" if grades is None else "grades",
        grades=[] if grades is None else grades,
    )


@router.get(
    "/schools/{school_id}/classrooms",
    response_model=list[ClassroomItem],
)
async def list_classrooms_endpoint(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> list[ClassroomItem]:
    """
    List all classrooms for a school (school_admin sees all; teacher sees all too).

    Student counts and package counts are included for the roster display.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        # Scoped to the caller's grades (#647). Previously every grade's
        # classrooms were listed to every teacher.
        grades = await grade_filter(conn, teacher, school_id)
        rows = await list_classrooms(conn, school_id, grades)

    return [ClassroomItem(**r) for r in rows]


@router.get(
    "/schools/{school_id}/classrooms/{classroom_id}",
    response_model=ClassroomDetailResponse,
)
async def get_classroom_endpoint(
    school_id: str,
    classroom_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ClassroomDetailResponse:
    """Return a classroom with its full package and student lists."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        detail = await get_classroom_detail(conn, school_id, classroom_id)
        grades = await grade_filter(conn, teacher, school_id)

    if not detail:
        raise HTTPException(status_code=404, detail="Classroom not found")

    # The detail endpoint returns the classroom's STUDENTS, so an unscoped one
    # is a named-student disclosure — sharper than the list this issue was
    # filed for, and it would have survived fixing only what was reported.
    # 404, not 403: confirming "that classroom exists but is not yours" still
    # leaks which grades the school runs.
    if grades is not None and detail.get("grade") not in set(grades):
        raise HTTPException(status_code=404, detail="Classroom not found")

    return ClassroomDetailResponse(
        classroom_id=detail["classroom_id"],
        school_id=detail["school_id"],
        teacher_id=detail.get("teacher_id"),
        teacher_name=detail.get("teacher_name"),
        name=detail["name"],
        grade=detail.get("grade"),
        status=detail["status"],
        created_at=detail["created_at"],
        packages=[ClassroomPackageItem(**p) for p in detail["packages"]],
        students=[ClassroomStudentItem(**s) for s in detail["students"]],
    )


@router.patch(
    "/schools/{school_id}/classrooms/{classroom_id}",
    response_model=ClassroomItem,
)
async def update_classroom_endpoint(
    school_id: str,
    classroom_id: str,
    body: ClassroomUpdateRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ClassroomItem:
    """Update classroom name, grade, lead teacher, or status (active/archived)."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        result = await update_classroom(
            conn,
            school_id,
            classroom_id,
            body.name,
            body.grade,
            body.teacher_id,
            body.status,
        )

    if not result:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return ClassroomItem(
        classroom_id=result["classroom_id"],
        school_id=result["school_id"],
        teacher_id=result.get("teacher_id"),
        teacher_name=None,
        name=result["name"],
        grade=result.get("grade"),
        status=result["status"],
        created_at=result["created_at"],
    )


@router.post(
    "/schools/{school_id}/classrooms/{classroom_id}/packages",
    status_code=204,
)
async def assign_package_endpoint(
    school_id: str,
    classroom_id: str,
    body: AssignPackageRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """Assign a Curriculum Package to a classroom (idempotent — safe to call twice)."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        ok = await assign_package_to_classroom(
            conn,
            school_id,
            classroom_id,
            body.curriculum_id,
            teacher.get("teacher_id"),
            body.sort_order,
        )

    if not ok:
        raise HTTPException(status_code=404, detail="Classroom not found")


@router.patch(
    "/schools/{school_id}/classrooms/{classroom_id}/packages/{curriculum_id}",
    status_code=204,
)
async def reorder_package_endpoint(
    school_id: str,
    classroom_id: str,
    curriculum_id: str,
    body: ReorderPackageRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """Update the display sort_order of a package within a classroom."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        ok = await reorder_package_in_classroom(
            conn, school_id, classroom_id, curriculum_id, body.sort_order
        )

    if not ok:
        raise HTTPException(status_code=404, detail="Classroom or package not found")


@router.delete(
    "/schools/{school_id}/classrooms/{classroom_id}/packages/{curriculum_id}",
    status_code=204,
)
async def remove_package_endpoint(
    school_id: str,
    classroom_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """Remove a package from a classroom."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        ok = await remove_package_from_classroom(conn, school_id, classroom_id, curriculum_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Classroom not found")


@router.post(
    "/schools/{school_id}/classrooms/{classroom_id}/students",
    status_code=204,
)
async def assign_student_endpoint(
    school_id: str,
    classroom_id: str,
    body: AssignStudentRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """
    Add a student to a classroom.

    A student may be in multiple classrooms simultaneously (Q17 — temporal
    reassignment is valid).  Duplicate inserts are silently ignored.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        ok = await assign_student_to_classroom(conn, school_id, classroom_id, body.student_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Classroom or student not found")


@router.delete(
    "/schools/{school_id}/classrooms/{classroom_id}/students/{student_id}",
    status_code=204,
)
async def remove_student_endpoint(
    school_id: str,
    classroom_id: str,
    student_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """Remove a student from a classroom."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        ok = await remove_student_from_classroom(conn, school_id, classroom_id, student_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Classroom not found")


# ── Phase C — Curriculum Catalog ──────────────────────────────────────────────


@router.get(
    "/curricula/catalog",
    response_model=CatalogResponse,
)
async def get_curriculum_catalog(
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    grade: int | None = None,
) -> CatalogResponse:
    """
    List all platform curriculum packages available for classroom assignment.

    Optional ?grade=N filter returns only packages for that grade.
    Any authenticated teacher or school_admin may call this endpoint.
    """
    async with get_db(request) as conn:
        packages = await list_catalog(conn, grade=grade)

    return CatalogResponse(packages=packages, total=len(packages))


# ── Phase D — Curriculum Definitions ──────────────────────────────────────────


@router.post(
    "/schools/{school_id}/curriculum/definitions",
    response_model=CurriculumDefinitionResponse,
    status_code=201,
)
async def submit_definition_endpoint(
    school_id: str,
    body: CurriculumDefinitionRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumDefinitionResponse:
    """
    Submit a Curriculum Definition for school admin approval.

    Any teacher or school_admin in the school may submit.
    Status is set to 'pending_approval' automatically.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    subjects_payload = [
        {
            "subject_label": s.subject_label,
            "units": [{"title": u.title} for u in s.units],
        }
        for s in body.subjects
    ]

    async with get_db(request) as conn:
        result = await submit_definition(
            conn,
            school_id=school_id,
            teacher_id=teacher["teacher_id"],
            name=body.name,
            grade=body.grade,
            languages=body.languages,
            subjects=subjects_payload,
        )

    return CurriculumDefinitionResponse(**result)


@router.get(
    "/schools/{school_id}/curriculum/definitions",
    response_model=DefinitionListResponse,
)
async def list_definitions_endpoint(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    status: str | None = None,
) -> DefinitionListResponse:
    """
    List Curriculum Definitions for the school.

    - school_admin sees all definitions.
    - teacher sees only their own.

    Optional ?status= filter: pending_approval | approved | rejected
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Anyone with a curriculum capability (or school_admin) sees the whole
    # pending-approval queue; a plain proposing teacher sees only their own.
    can_view_all = teacher.get("role") == "school_admin" or has_any_curriculum_capability(teacher)
    teacher_filter = None if can_view_all else teacher["teacher_id"]

    async with get_db(request) as conn:
        definitions = await list_definitions(
            conn,
            school_id=school_id,
            status_filter=status,
            teacher_id=teacher_filter,
        )

    return DefinitionListResponse(definitions=definitions, total=len(definitions))


@router.get(
    "/schools/{school_id}/curriculum/definitions/{definition_id}",
    response_model=CurriculumDefinitionResponse,
)
async def get_definition_endpoint(
    school_id: str,
    definition_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumDefinitionResponse:
    """
    Fetch a single Curriculum Definition.

    school_admin can view any definition in the school.
    A regular teacher can only view their own.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        defn = await get_definition(conn, definition_id, school_id)

    if not defn:
        raise HTTPException(status_code=404, detail="Definition not found")

    can_view_all = teacher.get("role") == "school_admin" or has_any_curriculum_capability(teacher)
    if not can_view_all and defn["submitted_by"] != teacher["teacher_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    return CurriculumDefinitionResponse(**defn)


@router.post(
    "/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
    response_model=CurriculumDefinitionResponse,
)
async def approve_definition_endpoint(
    school_id: str,
    definition_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumDefinitionResponse:
    """
    Approve a pending Curriculum Definition (school_admin only).

    After approval the school admin can trigger the pipeline (Phase E).
    Returns 409 if the definition is not in 'pending_approval' state.
    """
    require_commission(teacher, school_id, request)

    async with get_db(request) as conn:
        result = await approve_definition(
            conn, definition_id, school_id, reviewed_by=teacher["teacher_id"]
        )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Definition not found or not in pending_approval state",
        )

    return CurriculumDefinitionResponse(**result)


@router.post(
    "/schools/{school_id}/curriculum/definitions/{definition_id}/reject",
    response_model=CurriculumDefinitionResponse,
)
async def reject_definition_endpoint(
    school_id: str,
    definition_id: str,
    body: RejectDefinitionRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumDefinitionResponse:
    """
    Reject a pending Curriculum Definition (school_admin only).

    The rejection reason is stored and surfaced to the submitting teacher.
    Returns 409 if the definition is not in 'pending_approval' state.
    """
    require_commission(teacher, school_id, request)

    async with get_db(request) as conn:
        result = await reject_definition(
            conn,
            definition_id,
            school_id,
            reviewed_by=teacher["teacher_id"],
            reason=body.reason,
        )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Definition not found or not in pending_approval state",
        )

    return CurriculumDefinitionResponse(**result)


# ── Epic 1 — LLM Provider Config ──────────────────────────────────────────────


@router.get(
    "/schools/{school_id}/llm-config",
    response_model=SchoolLLMConfigResponse,
)
async def get_school_llm_config(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolLLMConfigResponse:
    """
    Return the school's LLM provider configuration.

    school_admin only. Creates a default config row (anthropic) if none exists.
    """
    if teacher.get("role") != "school_admin":
        raise HTTPException(status_code=403, detail="Only school_admin can view LLM config")
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        config = await get_llm_config(conn, school_id)

    return SchoolLLMConfigResponse(**config)


@router.put(
    "/schools/{school_id}/llm-config",
    response_model=SchoolLLMConfigResponse,
)
async def update_school_llm_config(
    school_id: str,
    body: SchoolLLMConfigUpdateRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolLLMConfigResponse:
    """
    Update the school's LLM provider configuration.

    school_admin only. Validates that default_provider is in allowed_providers
    after the update. DPA acknowledgements are stamped with the current timestamp
    and are never removed.
    """
    if teacher.get("role") != "school_admin":
        raise HTTPException(status_code=403, detail="Only school_admin can update LLM config")
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        updated = await update_llm_config(
            conn,
            school_id,
            allowed_providers=body.allowed_providers,
            default_provider=body.default_provider,
            comparison_enabled=body.comparison_enabled,
            acknowledge_dpa=body.acknowledge_dpa,
        )

    # Validate that the default provider is in the allowed set after update
    if updated["default_provider"] not in updated["allowed_providers"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"default_provider '{updated['default_provider']}' is not in "
                f"allowed_providers {updated['allowed_providers']}"
            ),
        )

    return SchoolLLMConfigResponse(**updated)


# ── School curriculum library (TA-0) ─────────────────────────────────────────


@router.get(
    "/schools/{school_id}/library",
    response_model=LibraryResponse,
)
async def list_library(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> LibraryResponse:
    """
    List all OOB curricula adopted by this school.

    Accessible to all teachers in the school — admins and regular teachers
    both need to browse what has been adopted before importing content.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT
                sac.adoption_id,
                sac.curriculum_id,
                sac.forked_curriculum_id,
                c.name,
                c.grade,
                c.year,
                sac.status,
                sac.notes,
                sac.adopted_at,
                c.retention_status,
                EXISTS (
                    SELECT 1 FROM unit_content_overrides uco
                    WHERE uco.school_id = $1
                      AND uco.curriculum_id = sac.forked_curriculum_id
                ) AS has_overrides,
                al.metadata->>'reason' AS archive_reason
            FROM school_adopted_curricula sac
            JOIN curricula c ON c.curriculum_id = sac.curriculum_id
            LEFT JOIN LATERAL (
                SELECT metadata
                FROM audit_log
                WHERE target_type = 'curriculum'
                  AND target_id IS NULL
                  AND metadata->>'curriculum_id' = sac.curriculum_id::text
                  AND event_type LIKE 'curriculum.archive%'
                ORDER BY timestamp DESC
                LIMIT 1
            ) al ON true
            WHERE sac.school_id = $1
            ORDER BY c.retention_status = 'archived' ASC, c.grade, c.name
            """,
            school_id,
        )

    items = [
        AdoptionItem(
            adoption_id=str(row["adoption_id"]),
            curriculum_id=row["curriculum_id"],
            forked_curriculum_id=row["forked_curriculum_id"],
            name=row["name"],
            grade=row["grade"],
            year=row["year"],
            status=row["status"],
            notes=row["notes"],
            adopted_at=row["adopted_at"].isoformat(),
            has_overrides=row["has_overrides"],
            is_source_archived=row["retention_status"] == "archived",
            archive_reason=row["archive_reason"],
        )
        for row in rows
    ]
    return LibraryResponse(adoptions=items, total=len(items))


@router.post(
    "/schools/{school_id}/library",
    response_model=AdoptionItem,
    status_code=201,
)
async def adopt_curriculum(
    school_id: str,
    body: AdoptCurriculumRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AdoptionItem:
    """
    Adopt an OOB curriculum into the school's library.

    school_admin only. Creates a school_adopted_curricula row. The fork
    (school-owned curricula row) is NOT created here — it is created lazily
    on the first teacher import (TA-2). This endpoint is intentionally
    idempotent: if the curriculum is already adopted, it returns the existing
    adoption record.
    """
    require_commission(teacher, school_id, request)

    async with get_db(request) as conn:
        # Verify the curriculum exists and is a platform OOB curriculum.
        pkg = await conn.fetchrow(
            "SELECT curriculum_id, name, grade, year, is_default, owner_type "
            "FROM curricula WHERE curriculum_id = $1",
            body.curriculum_id,
        )
        if not pkg:
            raise HTTPException(status_code=404, detail="Curriculum not found")
        if not pkg["is_default"] or pkg["owner_type"] != "platform":
            raise HTTPException(
                status_code=422,
                detail="Only platform OOB curricula can be adopted via this endpoint",
            )

        # Idempotent insert — return existing row if already adopted.
        existing = await conn.fetchrow(
            "SELECT adoption_id, curriculum_id, forked_curriculum_id, status, "
            "notes, adopted_at FROM school_adopted_curricula "
            "WHERE school_id = $1 AND curriculum_id = $2",
            school_id,
            body.curriculum_id,
        )
        if existing:
            return AdoptionItem(
                adoption_id=str(existing["adoption_id"]),
                curriculum_id=existing["curriculum_id"],
                forked_curriculum_id=existing["forked_curriculum_id"],
                name=pkg["name"],
                grade=pkg["grade"],
                year=pkg["year"],
                status=existing["status"],
                notes=existing["notes"],
                adopted_at=existing["adopted_at"].isoformat(),
                has_overrides=False,
            )

        row = await conn.fetchrow(
            """
            INSERT INTO school_adopted_curricula
                (school_id, curriculum_id, grade, adopted_by, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING adoption_id, adopted_at, status
            """,
            school_id,
            body.curriculum_id,
            pkg["grade"],
            teacher["teacher_id"],
            body.notes,
        )

    log.info(
        "curriculum_adopted",
        school_id=school_id,
        curriculum_id=body.curriculum_id,
        adoption_id=str(row["adoption_id"]),
    )
    return AdoptionItem(
        adoption_id=str(row["adoption_id"]),
        curriculum_id=body.curriculum_id,
        forked_curriculum_id=None,
        name=pkg["name"],
        grade=pkg["grade"],
        year=pkg["year"],
        status=row["status"],
        notes=body.notes,
        adopted_at=row["adopted_at"].isoformat(),
        has_overrides=False,
    )


@router.patch(
    "/schools/{school_id}/library/{adoption_id}",
    response_model=AdoptionItem,
)
async def update_adoption(
    school_id: str,
    adoption_id: str,
    body: UpdateAdoptionRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> AdoptionItem:
    """
    Update an adoption record (deactivate / reactivate / update notes).

    school_admin only. Deactivating does NOT delete the fork or any overrides —
    it only hides the curriculum from the active library view.
    """
    require_commission(teacher, school_id, request)

    if body.status is None and body.notes is None:
        raise HTTPException(status_code=422, detail="Nothing to update")

    async with get_db(request) as conn:
        existing = await conn.fetchrow(
            "SELECT sac.adoption_id, sac.curriculum_id, sac.forked_curriculum_id, "
            "sac.status, sac.notes, sac.adopted_at, c.name, c.grade, c.year "
            "FROM school_adopted_curricula sac "
            "JOIN curricula c ON c.curriculum_id = sac.curriculum_id "
            "WHERE sac.school_id = $1 AND sac.adoption_id = $2",
            school_id,
            adoption_id,
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Adoption not found")

        new_status = body.status if body.status is not None else existing["status"]
        new_notes = body.notes if body.notes is not None else existing["notes"]

        await conn.execute(
            "UPDATE school_adopted_curricula SET status = $1, notes = $2 "
            "WHERE school_id = $3 AND adoption_id = $4",
            new_status,
            new_notes,
            school_id,
            adoption_id,
        )

        has_overrides = (
            await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM unit_content_overrides "
                "WHERE school_id = $1 AND curriculum_id = $2)",
                school_id,
                existing["forked_curriculum_id"],
            )
            if existing["forked_curriculum_id"]
            else False
        )

    return AdoptionItem(
        adoption_id=str(existing["adoption_id"]),
        curriculum_id=existing["curriculum_id"],
        forked_curriculum_id=existing["forked_curriculum_id"],
        name=existing["name"],
        grade=existing["grade"],
        year=existing["year"],
        status=new_status,
        notes=new_notes,
        adopted_at=existing["adopted_at"].isoformat(),
        has_overrides=has_overrides,
    )


# ── Adoption unit-status list (TA-6a pre-fork entry point) ───────────────────


@router.get(
    "/schools/{school_id}/library/{adoption_id}/units",
)
async def list_adoption_unit_status(
    school_id: str,
    adoption_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """
    List all OOB units for an adopted curriculum with their override status.

    Works before the school fork exists (forked_curriculum_id=null) — shows
    OOB units with empty override lists. Once the fork exists (after the first
    unit import), shows override status per unit alongside the fork curriculum ID.

    This is the primary entry point from the Library page. The fork-based
    endpoint (GET /schools/{id}/content/{curriculum_id}/units) requires a
    fork to already exist; this one does not.
    """
    from src.school.schemas import UnitOverrideStatus, UnitStatusItem, UnitStatusResponse

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        adoption = await conn.fetchrow(
            """
            SELECT sac.adoption_id, sac.curriculum_id, sac.forked_curriculum_id,
                   c.name, c.grade
            FROM school_adopted_curricula sac
            JOIN curricula c ON c.curriculum_id = sac.curriculum_id
            WHERE sac.school_id = $1 AND sac.adoption_id = $2
            """,
            school_id,
            adoption_id,
        )
        if not adoption:
            raise HTTPException(status_code=404, detail="Adoption not found")

        oob_curriculum_id = adoption["curriculum_id"]
        forked_curriculum_id = adoption["forked_curriculum_id"]

        units = await conn.fetch(
            """
            SELECT cu.unit_id, cu.title, cu.subject,
                   COALESCE(MAX(csv.subject_name), cu.subject) AS subject_name
            FROM curriculum_units cu
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = $1 AND csv.subject = cu.subject
            WHERE cu.curriculum_id = $1
            GROUP BY cu.unit_id, cu.title, cu.subject
            ORDER BY cu.subject, cu.unit_id
            """,
            oob_curriculum_id,
        )

        overrides = []
        active = []
        if forked_curriculum_id:
            overrides = await conn.fetch(
                """
                SELECT DISTINCT ON (uco.unit_id, uco.content_type)
                    uco.override_id, uco.unit_id, uco.content_type,
                    uco.review_status, uco.version_number, uco.edited_at,
                    uco.content_source, t.name AS last_edited_by_name
                FROM unit_content_overrides uco
                LEFT JOIN teachers t ON t.teacher_id = uco.last_edited_by
                WHERE uco.curriculum_id = $1 AND uco.lang = $2
                ORDER BY uco.unit_id, uco.content_type, uco.version_number DESC
                """,
                forked_curriculum_id,
                lang,
            )
            active = await conn.fetch(
                """
                SELECT unit_id, content_type, override_id
                FROM unit_content_active_versions
                WHERE curriculum_id = $1 AND lang = $2
                """,
                forked_curriculum_id,
                lang,
            )

    active_set = {(r["unit_id"], r["content_type"]): str(r["override_id"]) for r in active}
    override_map: dict[str, list] = {}
    for o in overrides:
        override_map.setdefault(o["unit_id"], []).append(o)

    items = [
        UnitStatusItem(
            unit_id=u["unit_id"],
            title=u["title"],
            subject=u["subject"],
            subject_name=u["subject_name"],
            overrides=[
                UnitOverrideStatus(
                    content_type=o["content_type"],
                    review_status=o["review_status"],
                    version_number=o["version_number"],
                    override_id=str(o["override_id"]),
                    edited_at=o["edited_at"].isoformat(),
                    is_active=active_set.get((u["unit_id"], o["content_type"]))
                    == str(o["override_id"]),
                    content_source=o["content_source"],
                    last_edited_by_name=o["last_edited_by_name"],
                )
                for o in override_map.get(u["unit_id"], [])
            ],
        )
        for u in units
    ]
    return UnitStatusResponse(
        units=items,
        total=len(items),
        curriculum_name=adoption["name"],
        grade=adoption["grade"],
        forked_curriculum_id=forked_curriculum_id,
    ).model_dump()


# ── School curriculum library — import (TA-2) ─────────────────────────────────

# Content types probed in order; tutorial package (tutorial + quiz sets) share
# a bundle_id so their review-status transitions are atomic.
_IMPORT_CONTENT_TYPES: list[tuple[str, str]] = [
    ("lesson", "lesson_{lang}.json"),
    ("tutorial", "tutorial_{lang}.json"),
    ("quiz_set_1", "quiz_set_1_{lang}.json"),
    ("quiz_set_2", "quiz_set_2_{lang}.json"),
    ("quiz_set_3", "quiz_set_3_{lang}.json"),
    ("experiment", "experiment_{lang}.json"),
]
_TUTORIAL_BUNDLE_TYPES = {"tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3"}


@router.post(
    "/schools/{school_id}/library/{adoption_id}/units/{unit_id}/import",
    status_code=201,
)
async def import_unit_content(
    school_id: str,
    adoption_id: str,
    unit_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """
    Import OOB content for one unit into the school's fork as draft overrides.

    Pre-flight (TA-2):
      1. Checks adoption gate — 403 if not adopted or deactivated.
      2. Creates the school's forked curricula row on first call (lazy fork).
      3. Probes the Content Store for available content types for this unit/lang.
      4. Inserts unit_content_overrides rows for each type not yet imported.
         Tutorial package rows (tutorial + quiz_set_*) share a bundle_id.
      5. Returns the full set of override rows for this unit (created + pre-existing).

    Idempotent: re-calling for a unit that is already imported returns the
    existing rows with skipped=True.
    """
    import uuid as _uuid

    from src.core.storage import get_storage
    from src.school.schemas import ImportUnitResponse, OverrideItem

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    storage = get_storage(request)

    async with get_db(request) as conn:
        # 1. Adoption gate ─────────────────────────────────────────────────────
        adoption = await conn.fetchrow(
            "SELECT sac.adoption_id, sac.curriculum_id, sac.forked_curriculum_id, "
            "sac.status, c.name, c.grade, c.year, c.owner_id "
            "FROM school_adopted_curricula sac "
            "JOIN curricula c ON c.curriculum_id = sac.curriculum_id "
            "WHERE sac.school_id = $1 AND sac.adoption_id = $2",
            school_id,
            adoption_id,
        )
        if not adoption:
            raise HTTPException(status_code=404, detail="Adoption not found")
        if adoption["status"] != "active":
            raise HTTPException(
                status_code=403,
                detail="This curriculum has been deactivated in your library",
            )

        oob_curriculum_id = adoption["curriculum_id"]
        forked_curriculum_id = adoption["forked_curriculum_id"]
        fork_created = False

        # 2. Lazy fork creation ────────────────────────────────────────────────
        if forked_curriculum_id is None:
            new_id = str(_uuid.uuid4())
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO curricula
                        (curriculum_id, name, grade, year, is_default,
                         owner_type, owner_id, school_id, source_curriculum_id)
                    VALUES ($1, $2, $3, $4, FALSE, 'school', $5, $5, $6)
                    """,
                    new_id,
                    adoption["name"],
                    adoption["grade"],
                    adoption["year"],
                    school_id,
                    oob_curriculum_id,
                )
                await conn.execute(
                    "UPDATE school_adopted_curricula "
                    "SET forked_curriculum_id = $1 "
                    "WHERE school_id = $2 AND adoption_id = $3",
                    new_id,
                    school_id,
                    adoption_id,
                )
                # Point this grade at the school fork (UPSERT — grade is PK per school)
                if adoption["grade"] is not None:
                    await conn.execute(
                        """
                        INSERT INTO grade_curriculum_assignments
                            (school_id, grade, curriculum_id, assigned_by)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (school_id, grade)
                        DO UPDATE SET curriculum_id = EXCLUDED.curriculum_id,
                                      assigned_by  = EXCLUDED.assigned_by
                        """,
                        school_id,
                        adoption["grade"],
                        new_id,
                        teacher["teacher_id"],
                    )
            forked_curriculum_id = new_id
            fork_created = True
            log.info(
                "curriculum_fork_created",
                school_id=school_id,
                oob_curriculum_id=oob_curriculum_id,
                forked_curriculum_id=forked_curriculum_id,
            )

        # 3. Probe Content Store for available types ───────────────────────────
        available: list[tuple[str, dict]] = []
        for content_type, filename_tpl in _IMPORT_CONTENT_TYPES:
            filename = filename_tpl.replace("{lang}", lang)
            path = f"curricula/{oob_curriculum_id}/{unit_id}/{filename}"
            try:
                body = await storage.read_json(path)
                available.append((content_type, body))
            except FileNotFoundError:
                pass

        if not available:
            raise HTTPException(
                status_code=404,
                detail=f"No content found for unit {unit_id!r} lang={lang!r}",
            )

        # 4. Insert override rows (skip already-imported types) ────────────────
        bundle_id = str(_uuid.uuid4())
        overrides: list[OverrideItem] = []

        for content_type, body in available:
            # Check if any version already exists (idempotent guard)
            existing_row = await conn.fetchrow(
                "SELECT override_id, review_status, version_number, "
                "bundle_id, edited_at "
                "FROM unit_content_overrides "
                "WHERE curriculum_id = $1 AND unit_id = $2 "
                "  AND lang = $3 AND content_type = $4 "
                "ORDER BY version_number DESC LIMIT 1",
                forked_curriculum_id,
                unit_id,
                lang,
                content_type,
            )
            if existing_row:
                overrides.append(
                    OverrideItem(
                        override_id=str(existing_row["override_id"]),
                        school_id=school_id,
                        curriculum_id=forked_curriculum_id,
                        unit_id=unit_id,
                        lang=lang,
                        content_type=content_type,
                        bundle_id=(
                            str(existing_row["bundle_id"]) if existing_row["bundle_id"] else None
                        ),
                        content_source="imported",
                        review_status=existing_row["review_status"],
                        version_number=existing_row["version_number"],
                        edited_at=existing_row["edited_at"].isoformat(),
                        skipped=True,
                    )
                )
                continue

            row_bundle_id = bundle_id if content_type in _TUTORIAL_BUNDLE_TYPES else None
            new_row = await conn.fetchrow(
                """
                INSERT INTO unit_content_overrides
                    (school_id, curriculum_id, unit_id, lang, content_type,
                     bundle_id, content_source, source_override_id, body,
                     last_edited_by, review_status, version_number)
                VALUES ($1, $2, $3, $4, $5,
                        $6, 'imported', NULL, $7,
                        $8, 'draft', 1)
                RETURNING override_id, review_status, version_number,
                          bundle_id, edited_at
                """,
                school_id,
                forked_curriculum_id,
                unit_id,
                lang,
                content_type,
                row_bundle_id,
                body,
                teacher["teacher_id"],
            )
            overrides.append(
                OverrideItem(
                    override_id=str(new_row["override_id"]),
                    school_id=school_id,
                    curriculum_id=forked_curriculum_id,
                    unit_id=unit_id,
                    lang=lang,
                    content_type=content_type,
                    bundle_id=(str(new_row["bundle_id"]) if new_row["bundle_id"] else None),
                    content_source="imported",
                    review_status=new_row["review_status"],
                    version_number=new_row["version_number"],
                    edited_at=new_row["edited_at"].isoformat(),
                    skipped=False,
                )
            )

    log.info(
        "unit_content_imported",
        school_id=school_id,
        unit_id=unit_id,
        lang=lang,
        created=sum(1 for o in overrides if not o.skipped),
        skipped=sum(1 for o in overrides if o.skipped),
    )
    return ImportUnitResponse(
        forked_curriculum_id=forked_curriculum_id,
        fork_created=fork_created,
        overrides=overrides,
    ).model_dump()


# ── TA-3 helpers ──────────────────────────────────────────────────────────────


async def _assert_school_owns_curriculum(conn, school_id: str, curriculum_id: str) -> None:
    """403 if curriculum_id is not a school-owned fork belonging to school_id."""
    row = await conn.fetchrow(
        "SELECT owner_type, school_id FROM curricula WHERE curriculum_id = $1",
        curriculum_id,
    )
    if not row or row["owner_type"] != "school" or str(row["school_id"]) != school_id:
        raise HTTPException(
            status_code=403,
            detail="Curriculum does not belong to this school",
        )


async def _latest_overrides_for_unit(
    conn,
    curriculum_id: str,
    unit_id: str,
    lang: str,
    content_type_filter: str | None,
) -> list:
    """
    Return the latest version row for each content_type in this unit.

    If content_type_filter is given, return only that content_type's latest
    row PLUS any bundle-mates that share the same bundle_id.
    """
    if content_type_filter:
        anchor = await conn.fetchrow(
            """
            SELECT override_id, content_type, review_status, version_number,
                   bundle_id, last_edited_by, edited_at, rejection_reason
            FROM unit_content_overrides
            WHERE curriculum_id = $1 AND unit_id = $2
              AND lang = $3 AND content_type = $4
            ORDER BY version_number DESC
            LIMIT 1
            """,
            curriculum_id,
            unit_id,
            lang,
            content_type_filter,
        )
        if not anchor:
            return []
        if not anchor["bundle_id"]:
            return [anchor]
        # Expand to full bundle
        return await conn.fetch(
            """
            SELECT DISTINCT ON (content_type)
                override_id, content_type, review_status, version_number,
                bundle_id, last_edited_by, edited_at, rejection_reason
            FROM unit_content_overrides
            WHERE bundle_id = $1
            ORDER BY content_type, version_number DESC
            """,
            anchor["bundle_id"],
        )

    # All content types — latest version each
    return await conn.fetch(
        """
        SELECT DISTINCT ON (content_type)
            override_id, content_type, review_status, version_number,
            bundle_id, last_edited_by, edited_at, rejection_reason
        FROM unit_content_overrides
        WHERE curriculum_id = $1 AND unit_id = $2 AND lang = $3
        ORDER BY content_type, version_number DESC
        """,
        curriculum_id,
        unit_id,
        lang,
    )


# ── Unit status list ──────────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}/content/review-queue",
)
async def get_review_queue(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """
    Return all pending-review unit content overrides for the school.

    Joins across all school-owned fork curricula so admins see the full queue
    in one place without navigating curriculum-by-curriculum.
    school_admin only.
    """
    from src.school.schemas import ReviewQueueItem, ReviewQueueResponse

    require_curriculum_view(teacher, school_id, request)

    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT
                uco.override_id,
                uco.curriculum_id          AS forked_curriculum_id,
                c.source_curriculum_id     AS oob_curriculum_id,
                c.name                     AS curriculum_name,
                c.grade,
                sac.adoption_id,
                uco.unit_id,
                cu.title                   AS unit_title,
                COALESCE(MAX(csv.subject_name), cu.subject) AS subject_name,
                uco.content_type,
                uco.version_number,
                uco.edited_at              AS submitted_at,
                uco.lang,
                t.name                     AS submitted_by_name
            FROM unit_content_overrides uco
            JOIN curricula c
                ON c.curriculum_id = uco.curriculum_id
            LEFT JOIN school_adopted_curricula sac
                ON sac.forked_curriculum_id = uco.curriculum_id
                AND sac.school_id = $1
            LEFT JOIN curriculum_units cu
                ON cu.curriculum_id = COALESCE(c.source_curriculum_id, uco.curriculum_id)
                AND cu.unit_id = uco.unit_id
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = COALESCE(c.source_curriculum_id, uco.curriculum_id)
                AND csv.subject = cu.subject
            LEFT JOIN teachers t
                ON t.teacher_id = uco.last_edited_by
            WHERE uco.school_id = $1
              AND uco.review_status = 'pending_review'
              AND uco.lang = $2
            GROUP BY
                uco.override_id, uco.curriculum_id,
                c.source_curriculum_id, c.name, c.grade,
                sac.adoption_id,
                uco.unit_id, cu.title, cu.subject,
                uco.content_type, uco.version_number, uco.edited_at, uco.lang,
                t.name
            ORDER BY uco.edited_at ASC
            """,
            school_id,
            lang,
        )

    items = [
        ReviewQueueItem(
            override_id=str(r["override_id"]),
            forked_curriculum_id=str(r["forked_curriculum_id"]),
            oob_curriculum_id=str(r["oob_curriculum_id"]) if r["oob_curriculum_id"] else None,
            curriculum_name=r["curriculum_name"],
            grade=r["grade"],
            adoption_id=str(r["adoption_id"]) if r["adoption_id"] else None,
            unit_id=r["unit_id"],
            unit_title=r["unit_title"],
            subject_name=r["subject_name"],
            content_type=r["content_type"],
            version_number=r["version_number"],
            submitted_at=r["submitted_at"].isoformat(),
            submitted_by_name=r["submitted_by_name"],
            lang=r["lang"],
        )
        for r in rows
    ]
    return ReviewQueueResponse(items=items, total=len(items)).model_dump()


@router.get(
    "/schools/{school_id}/content/{curriculum_id}/units",
)
async def list_unit_override_status(
    school_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """
    List all units in a school fork curriculum with their override status.

    Shows, per unit, which content types have overrides and at what review stage.
    Also flags whether each type is currently active (published to students).
    """
    from src.school.schemas import UnitOverrideStatus, UnitStatusItem, UnitStatusResponse

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        # Resolve source OOB curriculum_id — fork curricula have no curriculum_units rows;
        # those live under the source OOB curriculum_id.
        meta_row = await conn.fetchrow(
            "SELECT name, grade, source_curriculum_id FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
        source_id = meta_row["source_curriculum_id"] if meta_row else None
        units_curriculum_id = source_id or curriculum_id

        units = await conn.fetch(
            """
            SELECT cu.unit_id, cu.title, cu.subject,
                   COALESCE(MAX(csv.subject_name), cu.subject) AS subject_name
            FROM curriculum_units cu
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = $1 AND csv.subject = cu.subject
            WHERE cu.curriculum_id = $1
            GROUP BY cu.unit_id, cu.title, cu.subject
            ORDER BY cu.subject, cu.unit_id
            """,
            units_curriculum_id,
        )

        # DISTINCT ON (unit_id, content_type) — latest version per unit/type combination.
        # (Previous implementation had DISTINCT ON (content_type) which collapsed all
        # units to a single row per content type.)
        overrides = await conn.fetch(
            """
            SELECT DISTINCT ON (uco.unit_id, uco.content_type)
                uco.override_id, uco.unit_id, uco.content_type,
                uco.review_status, uco.version_number, uco.edited_at,
                uco.content_source, t.name AS last_edited_by_name
            FROM unit_content_overrides uco
            LEFT JOIN teachers t ON t.teacher_id = uco.last_edited_by
            WHERE uco.curriculum_id = $1 AND uco.lang = $2
            ORDER BY uco.unit_id, uco.content_type, uco.version_number DESC
            """,
            curriculum_id,
            lang,
        )

        active = await conn.fetch(
            """
            SELECT unit_id, content_type, override_id
            FROM unit_content_active_versions
            WHERE curriculum_id = $1 AND lang = $2
            """,
            curriculum_id,
            lang,
        )

        adoption_row = await conn.fetchrow(
            "SELECT adoption_id FROM school_adopted_curricula "
            "WHERE school_id = $1 AND forked_curriculum_id = $2 LIMIT 1",
            school_id,
            curriculum_id,
        )

    active_set = {(r["unit_id"], r["content_type"]): str(r["override_id"]) for r in active}
    override_map: dict[str, list] = {}
    for o in overrides:
        override_map.setdefault(o["unit_id"], []).append(o)

    # Check content availability concurrently — one storage probe per unit.
    # A unit has importable content when its lesson file exists in the OOB store.
    storage = get_storage(request)

    async def _has_content(unit_id: str) -> bool:
        path = f"curricula/{units_curriculum_id}/{unit_id}/lesson_{lang}.json"
        return await storage.exists(path)

    content_flags = await asyncio.gather(*(_has_content(u["unit_id"]) for u in units))
    content_map = {u["unit_id"]: flag for u, flag in zip(units, content_flags, strict=True)}

    items = [
        UnitStatusItem(
            unit_id=u["unit_id"],
            title=u["title"],
            subject=u["subject"],
            subject_name=u["subject_name"],
            has_content=content_map[u["unit_id"]],
            overrides=[
                UnitOverrideStatus(
                    content_type=o["content_type"],
                    review_status=o["review_status"],
                    version_number=o["version_number"],
                    override_id=str(o["override_id"]),
                    edited_at=o["edited_at"].isoformat(),
                    is_active=active_set.get((u["unit_id"], o["content_type"]))
                    == str(o["override_id"]),
                    content_source=o["content_source"],
                    last_edited_by_name=o["last_edited_by_name"],
                )
                for o in override_map.get(u["unit_id"], [])
            ],
        )
        for u in units
    ]
    return UnitStatusResponse(
        units=items,
        total=len(items),
        curriculum_name=meta_row["name"] if meta_row else None,
        grade=meta_row["grade"] if meta_row else None,
        adoption_id=str(adoption_row["adoption_id"]) if adoption_row else None,
    ).model_dump()


# ── Get override body ─────────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/overrides/{content_type}",
)
async def get_unit_override(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """Return the latest override row (including body) for one content type."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        row = await conn.fetchrow(
            """
            SELECT uco.override_id, uco.review_status, uco.version_number,
                   uco.content_source, uco.body, uco.edited_at, uco.lang,
                   uco.bundle_id, uco.rejection_reason,
                   t.name AS last_edited_by_name
            FROM unit_content_overrides uco
            LEFT JOIN teachers t ON t.teacher_id = uco.last_edited_by
            WHERE uco.curriculum_id = $1 AND uco.unit_id = $2
              AND uco.lang = $3 AND uco.content_type = $4
            ORDER BY uco.version_number DESC
            LIMIT 1
            """,
            curriculum_id,
            unit_id,
            lang,
            content_type,
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="No override found — import the unit first",
            )

        admin_row = await conn.fetchrow(
            "SELECT name FROM teachers WHERE school_id = $1 AND role = 'school_admin' "
            "ORDER BY teacher_id ASC LIMIT 1",
            school_id,
        )

        import json as _json

        body_raw = row["body"]
        body = _json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        return {
            "override_id": str(row["override_id"]),
            "school_id": school_id,
            "curriculum_id": curriculum_id,
            "unit_id": unit_id,
            "content_type": content_type,
            "lang": row["lang"],
            "review_status": row["review_status"],
            "version_number": row["version_number"],
            "content_source": row["content_source"],
            "bundle_id": str(row["bundle_id"]) if row["bundle_id"] else None,
            "edited_at": row["edited_at"].isoformat(),
            "last_edited_by_name": row["last_edited_by_name"],
            "rejection_reason": row["rejection_reason"],
            "school_admin_name": admin_row["name"] if admin_row else None,
            "body": body,
        }


# ── Override source (OOB snapshot for diff) ───────────────────────────────────


@router.get(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/overrides/{content_type}/source",
)
async def get_unit_override_source(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """Return the original imported body (version 1) used to diff against teacher edits."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        row = await conn.fetchrow(
            """
            SELECT body
            FROM unit_content_overrides
            WHERE curriculum_id = $1 AND unit_id = $2
              AND lang = $3 AND content_type = $4
              AND content_source = 'imported'
            ORDER BY version_number ASC
            LIMIT 1
            """,
            curriculum_id,
            unit_id,
            lang,
            content_type,
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="No imported source found for this content type",
            )

        body_raw = row["body"]
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        return {"body": body}


# ── Revert to original ────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/overrides/{content_type}/revert",
)
async def revert_unit_override(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
) -> dict:
    """
    Revert teacher edits to the original imported (OOB) content.

    - draft / rejected: inserts a new draft version with the imported body.
    - approved: repoints unit_content_active_versions to the imported snapshot
      and marks the current override as draft (admin only).
    - pending_review: 409 — must be approved or rejected first.
    """
    from src.school.schemas import OverrideItem

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        async with conn.transaction():
            source_row = await conn.fetchrow(
                """
                SELECT override_id, body, bundle_id
                FROM unit_content_overrides
                WHERE curriculum_id = $1 AND unit_id = $2
                  AND lang = $3 AND content_type = $4
                  AND content_source = 'imported'
                ORDER BY version_number ASC LIMIT 1
                """,
                curriculum_id,
                unit_id,
                lang,
                content_type,
            )

            if not source_row:
                raise HTTPException(
                    status_code=404,
                    detail="No imported source to revert to",
                )

            latest = await conn.fetchrow(
                """
                SELECT override_id, review_status, version_number
                FROM unit_content_overrides
                WHERE curriculum_id = $1 AND unit_id = $2
                  AND lang = $3 AND content_type = $4
                ORDER BY version_number DESC LIMIT 1
                FOR UPDATE
                """,
                curriculum_id,
                unit_id,
                lang,
                content_type,
            )

            if not latest:
                raise HTTPException(status_code=404, detail="No content to revert")

            status = latest["review_status"]

            if status == "pending_review":
                raise HTTPException(
                    status_code=409,
                    detail="Cannot revert content that is pending review — approve or reject first",
                )

            if status == "approved":
                if teacher["role"] != "school_admin":
                    raise HTTPException(
                        status_code=403,
                        detail="Only a school admin can revert published content",
                    )
                # Repoint the active version to the original imported snapshot
                await conn.execute(
                    """
                    INSERT INTO unit_content_active_versions
                        (curriculum_id, unit_id, lang, content_type, override_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (curriculum_id, unit_id, lang, content_type)
                    DO UPDATE SET override_id = EXCLUDED.override_id
                    """,
                    curriculum_id,
                    unit_id,
                    lang,
                    content_type,
                    source_row["override_id"],
                )
                row = await conn.fetchrow(
                    """
                    UPDATE unit_content_overrides
                    SET review_status = 'draft', last_edited_by = $1, edited_at = now()
                    WHERE override_id = $2
                    RETURNING override_id, review_status, version_number,
                              bundle_id, edited_at, content_source
                    """,
                    teacher["teacher_id"],
                    latest["override_id"],
                )
            else:
                # draft / rejected — insert a new draft version with the imported body
                new_version = latest["version_number"] + 1
                row = await conn.fetchrow(
                    """
                    INSERT INTO unit_content_overrides
                        (school_id, curriculum_id, unit_id, lang, content_type,
                         bundle_id, content_source, source_override_id, body,
                         last_edited_by, review_status, version_number)
                    VALUES ($1, $2, $3, $4, $5,
                            $6, 'teacher_edit', $7, $8,
                            $9, 'draft', $10)
                    RETURNING override_id, review_status, version_number,
                              bundle_id, edited_at, content_source
                    """,
                    school_id,
                    curriculum_id,
                    unit_id,
                    lang,
                    content_type,
                    source_row["bundle_id"],
                    str(source_row["override_id"]),
                    source_row["body"],
                    teacher["teacher_id"],
                    new_version,
                )

    return OverrideItem(
        override_id=str(row["override_id"]),
        school_id=school_id,
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        lang=lang,
        content_type=content_type,
        bundle_id=str(row["bundle_id"]) if row["bundle_id"] else None,
        content_source=row["content_source"],
        review_status=row["review_status"],
        version_number=row["version_number"],
        edited_at=row["edited_at"].isoformat(),
    ).model_dump()


# ── Save draft ────────────────────────────────────────────────────────────────


@router.put(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/overrides/{content_type}",
)
async def save_draft(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    body: SaveDraftRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """
    Save an edited draft for one content type in a unit.

    - While review_status = 'draft': updates body in place (same row).
    - While review_status = 'rejected': inserts a new version (MAX+1).
      Uses SELECT FOR UPDATE to prevent version_number races.
    - While 'pending_review' or 'approved': returns 409 — must be
      rejected or published before re-editing.
    - No existing override (not yet imported): returns 404.
    """
    from src.school.schemas import OverrideItem, SaveDraftRequest

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not isinstance(body, SaveDraftRequest):
        raise HTTPException(status_code=422, detail="Invalid body")

    lang = body.lang

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        async with conn.transaction():
            latest = await conn.fetchrow(
                """
                SELECT override_id, review_status, version_number, bundle_id, edited_at
                FROM unit_content_overrides
                WHERE curriculum_id = $1 AND unit_id = $2
                  AND lang = $3 AND content_type = $4
                ORDER BY version_number DESC
                LIMIT 1
                FOR UPDATE
                """,
                curriculum_id,
                unit_id,
                lang,
                content_type,
            )

            if not latest:
                raise HTTPException(
                    status_code=404,
                    detail="No imported content found — import the unit first",
                )

            status = latest["review_status"]

            if status in ("pending_review", "approved"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot edit content in '{status}' state — reject it first",
                )

            if status == "draft":
                # Update body in place
                row = await conn.fetchrow(
                    """
                    UPDATE unit_content_overrides
                    SET body = $1, last_edited_by = $2, edited_at = now()
                    WHERE override_id = $3
                    RETURNING override_id, review_status, version_number,
                              bundle_id, edited_at, content_source
                    """,
                    body.body,
                    teacher["teacher_id"],
                    latest["override_id"],
                )
            else:
                # 'rejected' — insert new version
                import uuid as _uuid

                new_version = latest["version_number"] + 1
                row_bundle_id = (
                    str(_uuid.uuid4()) if content_type in _TUTORIAL_BUNDLE_TYPES else None
                )
                row = await conn.fetchrow(
                    """
                    INSERT INTO unit_content_overrides
                        (school_id, curriculum_id, unit_id, lang, content_type,
                         bundle_id, content_source, source_override_id, body,
                         last_edited_by, review_status, version_number)
                    VALUES ($1, $2, $3, $4, $5,
                            $6, 'teacher_authored', $7, $8,
                            $9, 'draft', $10)
                    RETURNING override_id, review_status, version_number,
                              bundle_id, edited_at, content_source
                    """,
                    school_id,
                    curriculum_id,
                    unit_id,
                    lang,
                    content_type,
                    row_bundle_id,
                    latest["override_id"],
                    body.body,
                    teacher["teacher_id"],
                    new_version,
                )

    return OverrideItem(
        override_id=str(row["override_id"]),
        school_id=school_id,
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        lang=lang,
        content_type=content_type,
        bundle_id=str(row["bundle_id"]) if row["bundle_id"] else None,
        content_source=row["content_source"],
        review_status=row["review_status"],
        version_number=row["version_number"],
        edited_at=row["edited_at"].isoformat(),
    ).model_dump()


# ── Submit for review ─────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/review",
)
async def submit_for_review(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    body: ReviewActionRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """
    Submit draft overrides for admin review.

    Transitions review_status: draft → pending_review.
    If content_type targets a bundle member, all bundle rows transition atomically.
    If content_type is None, all draft rows for this unit+lang are submitted.
    """
    from src.school.schemas import ReviewActionRequest

    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not isinstance(body, ReviewActionRequest):
        raise HTTPException(status_code=422, detail="Invalid body")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        rows = await _latest_overrides_for_unit(
            conn, curriculum_id, unit_id, body.lang, body.content_type
        )
        draft_ids = [r["override_id"] for r in rows if r["review_status"] == "draft"]

        if not draft_ids:
            raise HTTPException(
                status_code=409,
                detail="No draft content found to submit for review",
            )

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE unit_content_overrides
                SET review_status = 'pending_review'
                WHERE override_id = ANY($1::uuid[])
                """,
                draft_ids,
            )

    return {"submitted": len(draft_ids), "override_ids": [str(i) for i in draft_ids]}


# ── Approve ───────────────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/approve",
)
async def approve_unit_content(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    body: ApproveRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """
    Approve pending-review overrides. school_admin only.

    If body.publish=True, also publishes (upserts into unit_content_active_versions)
    in the same transaction — the combined "Approve and publish" action.
    """
    from src.school.schemas import ApproveRequest

    require_review(teacher, school_id, request)

    if not isinstance(body, ApproveRequest):
        raise HTTPException(status_code=422, detail="Invalid body")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        rows = await _latest_overrides_for_unit(
            conn, curriculum_id, unit_id, body.lang, body.content_type
        )
        pending_rows = [r for r in rows if r["review_status"] == "pending_review"]
        pending_ids = [r["override_id"] for r in pending_rows]

        if not pending_ids:
            raise HTTPException(
                status_code=409,
                detail="No pending-review content found to approve",
            )

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE unit_content_overrides
                SET review_status = 'approved'
                WHERE override_id = ANY($1::uuid[])
                """,
                pending_ids,
            )

            if body.publish:
                for row in pending_rows:
                    await conn.execute(
                        """
                        INSERT INTO unit_content_active_versions
                            (school_id, curriculum_id, unit_id, lang,
                             content_type, override_id, activated_by)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (school_id, curriculum_id, unit_id, lang, content_type)
                        DO UPDATE SET override_id   = EXCLUDED.override_id,
                                      activated_by  = EXCLUDED.activated_by,
                                      activated_at  = now()
                        """,
                        school_id,
                        curriculum_id,
                        unit_id,
                        body.lang,
                        row["content_type"],
                        row["override_id"],
                        teacher["teacher_id"],
                    )

    return {
        "approved": len(pending_ids),
        "published": len(pending_ids) if body.publish else 0,
        "override_ids": [str(i) for i in pending_ids],
    }


# ── Reject ────────────────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/reject",
)
async def reject_unit_content(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    body: RejectRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """
    Reject pending-review overrides with a reason. school_admin only.

    Transitions review_status: pending_review → rejected.
    Teacher can then re-edit: the next save on a rejected row creates a new version.
    """
    from src.school.schemas import RejectRequest

    require_review(teacher, school_id, request)

    if not isinstance(body, RejectRequest):
        raise HTTPException(status_code=422, detail="Invalid body")

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        rows = await _latest_overrides_for_unit(
            conn, curriculum_id, unit_id, body.lang, body.content_type
        )
        pending_ids = [r["override_id"] for r in rows if r["review_status"] == "pending_review"]

        if not pending_ids:
            raise HTTPException(
                status_code=409,
                detail="No pending-review content found to reject",
            )

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE unit_content_overrides
                SET review_status = 'rejected', rejection_reason = $2
                WHERE override_id = ANY($1::uuid[])
                """,
                pending_ids,
                body.reason,
            )

    return {"rejected": len(pending_ids), "override_ids": [str(i) for i in pending_ids]}


# ── Publish approved ──────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/content/{curriculum_id}/units/{unit_id}/publish",
)
async def publish_unit_content(
    school_id: str,
    curriculum_id: str,
    unit_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = "en",
    content_type: str | None = None,
) -> dict:
    """
    Publish all approved overrides for a unit to students. school_admin only.

    Upserts into unit_content_active_versions. Separate from approve() so the
    admin can batch-approve many units and then publish in one sweep.
    """
    require_review(teacher, school_id, request)

    async with get_db(request) as conn:
        await _assert_school_owns_curriculum(conn, school_id, curriculum_id)

        rows = await _latest_overrides_for_unit(conn, curriculum_id, unit_id, lang, content_type)
        approved_rows = [r for r in rows if r["review_status"] == "approved"]

        if not approved_rows:
            raise HTTPException(
                status_code=409,
                detail="No approved content found to publish",
            )

        async with conn.transaction():
            for row in approved_rows:
                await conn.execute(
                    """
                    INSERT INTO unit_content_active_versions
                        (school_id, curriculum_id, unit_id, lang,
                         content_type, override_id, activated_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (school_id, curriculum_id, unit_id, lang, content_type)
                    DO UPDATE SET override_id   = EXCLUDED.override_id,
                                  activated_by  = EXCLUDED.activated_by,
                                  activated_at  = now()
                    """,
                    school_id,
                    curriculum_id,
                    unit_id,
                    lang,
                    row["content_type"],
                    row["override_id"],
                    teacher["teacher_id"],
                )

    # Invalidate L2 override cache for each published content type so students
    # see the new content on the next request without waiting for TTL expiry.
    from src.core.cache_keys import override_key as _override_key
    from src.core.redis_client import get_redis as _get_redis

    redis = _get_redis(request)
    for row in approved_rows:
        await redis.delete(
            _override_key(school_id, curriculum_id, unit_id, lang, row["content_type"])
        )

    return {
        "published": len(approved_rows),
        "override_ids": [str(r["override_id"]) for r in approved_rows],
    }


# ── Per-school theming (Epic 13) ──────────────────────────────────────────────


@router.get("/schools/{school_id}/theme", response_model=SchoolThemeResponse)
async def get_theme_endpoint(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolThemeResponse:
    """Return the school's stored theme. Falls back to null when not set (clients use defaults)."""
    async with get_db(request) as conn:
        theme = await get_school_theme(conn, school_id, teacher["school_id"])
    if theme is None and school_id != teacher["school_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return SchoolThemeResponse(theme=theme)


@router.put("/schools/{school_id}/theme", response_model=SchoolThemeResponse)
async def put_theme_endpoint(
    school_id: str,
    body: SchoolThemeUpdateRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolThemeResponse:
    """Persist the school's theme. school_admin only."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(status_code=403, detail="school_admin role required")
    if school_id != teacher["school_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    theme_dict = body.theme.model_dump()
    async with get_db(request) as conn:
        await update_school_theme(conn, school_id, teacher["school_id"], theme_dict)
    log.info("school_theme_updated school_id=%s actor=%s", school_id, teacher.get("teacher_id"))
    return SchoolThemeResponse(theme=theme_dict)


@router.get("/student/school-theme", response_model=SchoolThemeResponse)
async def get_student_theme_endpoint(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> SchoolThemeResponse:
    """Return the theme for the student's enrolled school. Returns null theme if not enrolled."""
    pool = request.app.state.pool
    theme = await get_student_school_theme(pool, student["student_id"])
    return SchoolThemeResponse(theme=theme)


# ── POST /school/enrol/confirm (student) ──────────────────────────────────────


@router.post("/school/enrol/confirm", response_model=EnrolConfirmResponse)
async def confirm_enrolment(
    body: EnrolConfirmRequest,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> EnrolConfirmResponse:
    """Join a school using the code from an invite link (#609).

    The school portal has always offered admins a copy-able `/enrol/{code}`
    link; this is the endpoint behind it, which never existed.

    Runs with RLS bypassed on purpose: `schools` and `school_enrolments` are
    RLS-protected and the student is by definition not yet scoped to the school
    they are joining. The enrolment code is the secret that authorises this, and
    nothing about a school is returned unless the code matches.
    """
    student_id = str(student["student_id"])

    async with request.app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        result = await enrol_student_by_code(conn, student_id, body.token)

    if result["ok"]:
        return EnrolConfirmResponse(school_name=result["school_name"])

    reason = result["reason"]
    if reason == "invalid_code":
        raise HTTPException(
            status_code=404,
            detail={
                "error": "invalid_code",
                # Deliberately says nothing about whether a school exists.
                "detail": "That enrolment link is not valid. Check with your school for a new one.",
                "correlation_id": _cid(request),
            },
        )
    if reason == "already_enrolled_elsewhere":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_enrolled",
                "detail": (
                    "You are already enrolled at a school. Ask your school to move "
                    "your account before joining a different one."
                ),
                "correlation_id": _cid(request),
            },
        )
    raise HTTPException(
        status_code=402,
        detail={
            "error": "seat_limit_reached",
            "detail": (
                "This school has no places left on its plan. Let your school know "
                "so they can add more."
            ),
            "correlation_id": _cid(request),
        },
    )
