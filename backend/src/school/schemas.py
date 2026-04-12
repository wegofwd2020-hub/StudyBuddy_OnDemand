"""
backend/src/school/schemas.py

Pydantic request/response models for Phase 8–9 school endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class SchoolRegisterRequest(BaseModel):
    school_name: str
    contact_email: EmailStr
    country: str = "CA"
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters.")
        if len(v.encode()) > 72:
            raise ValueError("Password must be 72 bytes or fewer.")
        return v


class SchoolRegisterResponse(BaseModel):
    school_id: str
    teacher_id: str
    access_token: str
    role: str


class SchoolProfileResponse(BaseModel):
    school_id: str
    name: str
    contact_email: str
    country: str
    enrolment_code: str | None = None
    status: str
    created_at: datetime


class TeacherInviteRequest(BaseModel):
    name: str
    email: EmailStr


class TeacherInviteResponse(BaseModel):
    teacher_id: str
    email: str
    role: str


# ── Teacher roster + grade assignments ───────────────────────────────────────


class TeacherRosterItem(BaseModel):
    teacher_id: str
    name: str
    email: str
    role: str
    account_status: str
    assigned_grades: list[int]


class TeacherRosterResponse(BaseModel):
    teachers: list[TeacherRosterItem]


class TeacherGradeAssignRequest(BaseModel):
    grades: list[int]


class TeacherGradeAssignResponse(BaseModel):
    teacher_id: str
    school_id: str
    assigned_grades: list[int]


# ── Phase 9 — Enrolment ────────────────────────────────────────────────────────


class StudentEnrolmentEntry(BaseModel):
    """One row in a roster upload. Only email is required."""

    email: EmailStr
    grade: int | None = None
    teacher_id: str | None = None


class EnrolmentUploadRequest(BaseModel):
    students: list[StudentEnrolmentEntry]


class EnrolmentUploadResponse(BaseModel):
    enrolled: int
    already_enrolled: int
    errors: list[dict] = []


class EnrolmentRosterItem(BaseModel):
    student_email: str
    student_id: str | None = None
    status: str
    enrolled_grade: int | None = None
    assigned_teacher_id: str | None = None
    assigned_teacher_name: str | None = None
    assigned_grade: int | None = None
    added_at: datetime


class EnrolmentRosterResponse(BaseModel):
    roster: list[EnrolmentRosterItem]


# ── Student-teacher assignment ────────────────────────────────────────────────


class StudentAssignmentRequest(BaseModel):
    """PUT /schools/{school_id}/students/{student_id}/assignment"""

    teacher_id: str
    grade: int


class StudentAssignmentResponse(BaseModel):
    assignment_id: str
    student_id: str
    teacher_id: str
    teacher_name: str | None = None
    teacher_email: str | None = None
    school_id: str
    grade: int
    assigned_at: datetime
    assigned_by_name: str | None = None


class BulkReassignRequest(BaseModel):
    """POST /schools/{school_id}/teachers/{from_id}/reassign"""

    to_teacher_id: str
    grade: int


class BulkReassignResponse(BaseModel):
    reassigned: int


# ── Phase A provisioning schemas ──────────────────────────────────────────────


class ProvisionTeacherRequest(BaseModel):
    """POST /schools/{school_id}/teachers"""

    name: str
    email: EmailStr
    subject_specialisation: str | None = None


class ProvisionTeacherResponse(BaseModel):
    teacher_id: str
    school_id: str
    name: str
    email: str
    role: str


class ProvisionStudentRequest(BaseModel):
    """POST /schools/{school_id}/students"""

    name: str
    email: EmailStr
    grade: int

    @field_validator("grade")
    @classmethod
    def grade_range(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("grade must be between 1 and 12")
        return v


class ProvisionStudentResponse(BaseModel):
    student_id: str
    school_id: str
    name: str
    email: str
    grade: int


class ResetPasswordResponse(BaseModel):
    detail: str


class PromoteTeacherResponse(BaseModel):
    teacher_id: str
    name: str
    email: str
    role: str


# ── Phase C — Curriculum Catalog schemas ─────────────────────────────────────


class CatalogSubjectSummary(BaseModel):
    subject: str
    subject_name: str | None
    unit_count: int
    has_content: bool


class CatalogEntry(BaseModel):
    """One pre-built platform Curriculum Package available for classroom assignment."""

    curriculum_id: str
    name: str
    grade: int
    year: int
    is_default: bool
    owner_type: str
    subject_count: int
    unit_count: int
    subjects: list[CatalogSubjectSummary]
    created_at: datetime


class CatalogResponse(BaseModel):
    packages: list[CatalogEntry]
    total: int


# ── Phase B — Classroom schemas ───────────────────────────────────────────────


class ClassroomCreateRequest(BaseModel):
    """POST /schools/{school_id}/classrooms"""

    name: str
    grade: int | None = None
    teacher_id: str | None = None

    @field_validator("grade")
    @classmethod
    def grade_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("grade must be between 1 and 12")
        return v


class ClassroomUpdateRequest(BaseModel):
    """PATCH /schools/{school_id}/classrooms/{classroom_id}"""

    name: str | None = None
    grade: int | None = None
    teacher_id: str | None = None
    status: str | None = None

    @field_validator("grade")
    @classmethod
    def grade_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("grade must be between 1 and 12")
        return v

    @field_validator("status")
    @classmethod
    def status_values(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "archived"):
            raise ValueError("status must be 'active' or 'archived'")
        return v


class ClassroomItem(BaseModel):
    classroom_id: str
    school_id: str
    teacher_id: str | None
    teacher_name: str | None
    name: str
    grade: int | None
    status: str
    created_at: datetime
    student_count: int = 0
    package_count: int = 0


class ClassroomPackageItem(BaseModel):
    curriculum_id: str
    curriculum_name: str | None
    assigned_at: datetime
    sort_order: int


class ClassroomStudentItem(BaseModel):
    student_id: str
    name: str
    email: str
    grade: int | None
    joined_at: datetime


class AssignPackageRequest(BaseModel):
    """POST /schools/{school_id}/classrooms/{classroom_id}/packages"""

    curriculum_id: str
    sort_order: int = 0


class ReorderPackageRequest(BaseModel):
    """PATCH /schools/{school_id}/classrooms/{classroom_id}/packages/{curriculum_id}"""

    sort_order: int


class AssignStudentRequest(BaseModel):
    """POST /schools/{school_id}/classrooms/{classroom_id}/students"""

    student_id: str


class ClassroomDetailResponse(BaseModel):
    classroom_id: str
    school_id: str
    teacher_id: str | None
    teacher_name: str | None
    name: str
    grade: int | None
    status: str
    created_at: datetime
    packages: list[ClassroomPackageItem]
    students: list[ClassroomStudentItem]
