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

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.school.enrolment_service import (
    assign_student,
    get_roster,
    get_student_assignment,
    reassign_students_bulk,
    upload_roster,
)
from src.school.schemas import (
    BulkReassignRequest,
    BulkReassignResponse,
    EnrolmentRosterItem,
    EnrolmentRosterResponse,
    EnrolmentUploadRequest,
    EnrolmentUploadResponse,
    PromoteTeacherResponse,
    ProvisionStudentRequest,
    ProvisionStudentResponse,
    AssignPackageRequest,
    AssignStudentRequest,
    ClassroomCreateRequest,
    ClassroomDetailResponse,
    ClassroomItem,
    ClassroomPackageItem,
    ClassroomStudentItem,
    ClassroomUpdateRequest,
    ProvisionStudentRequest,
    ProvisionStudentResponse,
    ProvisionTeacherRequest,
    ProvisionTeacherResponse,
    ReorderPackageRequest,
    ResetPasswordResponse,
    SchoolProfileResponse,
    SchoolRegisterRequest,
    SchoolRegisterResponse,
    StudentAssignmentRequest,
    StudentAssignmentResponse,
    TeacherGradeAssignRequest,
    TeacherGradeAssignResponse,
    TeacherInviteRequest,
    TeacherInviteResponse,
    TeacherRosterResponse,
)
from src.school.service import (
    assign_package_to_classroom,
    assign_student_to_classroom,
    create_classroom,
    fetch_school,
    get_classroom_detail,
    invite_teacher,
    list_classrooms,
    promote_to_school_admin,
    provision_student,
    provision_teacher,
    remove_package_from_classroom,
    remove_student_from_classroom,
    reorder_package_in_classroom,
    update_classroom,
    register_school,
    reset_student_password,
    reset_teacher_password,
)
from src.school.subscription_service import get_seat_usage
from src.utils.logger import get_logger

log = get_logger("school")
router = APIRouter(tags=["school"])


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
            result = await register_school(conn, body.school_name, body.contact_email, body.country, body.password)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "A school or account with that email already exists.",
                        "correlation_id": _cid(request),
                    },
                )
            raise
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
            detail={"error": "forbidden", "detail": "Cannot view assignments for a different school.", "correlation_id": _cid(request)},
        )
    async with get_db(request) as conn:
        row = await get_student_assignment(conn, school_id, student_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "No assignment found for this student.", "correlation_id": _cid(request)},
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
                conn, school_id, student_id, body.grade, body.teacher_id,
                assigned_by=teacher["teacher_id"],
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "assignment_invalid", "detail": str(exc), "correlation_id": _cid(request)},
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
                conn, school_id, from_teacher_id, body.to_teacher_id, body.grade,
                assigned_by=teacher["teacher_id"],
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "reassign_invalid", "detail": str(exc), "correlation_id": _cid(request)},
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
                       array_agg(tga.grade ORDER BY tga.grade)
                       FILTER (WHERE tga.grade IS NOT NULL), '{}'
                   ) AS assigned_grades
            FROM teachers t
            LEFT JOIN teacher_grade_assignments tga
                ON tga.teacher_id = t.teacher_id
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
            tid, sid,
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
            await conn.execute(
                "DELETE FROM teacher_grade_assignments WHERE teacher_id = $1", tid
            )
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


# ── Phase A provisioning endpoints ───────────────────────────────────────────


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
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "A teacher with that email already exists.",
                        "correlation_id": _cid(request),
                    },
                )
            raise

    try:
        await send_welcome_teacher_email(result["email"], result["name"], result["default_password"])
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
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "A student with that email already exists.",
                        "correlation_id": _cid(request),
                    },
                )
            raise

    try:
        await send_welcome_student_email(result["email"], result["name"], result["default_password"])
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
            detail={"error": "not_found", "detail": "Teacher not found in this school.", "correlation_id": _cid(request)},
        )

    try:
        await send_password_reset_email(result["email"], result["name"], result["default_password"])
    except Exception:
        log.warning("reset_email_failed", teacher_id=target_teacher_id)

    return ResetPasswordResponse(detail="Password reset. New credentials emailed to the teacher.")


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
        result = await reset_student_password(conn, school_id, target_student_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Student not found in this school.", "correlation_id": _cid(request)},
        )

    try:
        await send_password_reset_email(result["email"], result["name"], result["default_password"])
    except Exception:
        log.warning("reset_email_failed", student_id=target_student_id)

    return ResetPasswordResponse(detail="Password reset. New credentials emailed to the student.")


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
            detail={"error": "not_found", "detail": "Teacher not found in this school.", "correlation_id": _cid(request)},
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
        rows = await list_classrooms(conn, school_id)

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

    if not detail:
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
        ok = await assign_student_to_classroom(
            conn, school_id, classroom_id, body.student_id
        )

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
