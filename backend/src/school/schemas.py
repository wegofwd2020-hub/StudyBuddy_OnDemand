"""
backend/src/school/schemas.py

Pydantic request/response models for Phase 8–9 school endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class SchoolRegisterRequest(BaseModel):
    school_name: str
    contact_email: EmailStr
    country: str = "CA"


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
