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


# ── Phase 9 — Enrolment ────────────────────────────────────────────────────────

class EnrolmentUploadRequest(BaseModel):
    student_emails: list[EmailStr]


class EnrolmentUploadResponse(BaseModel):
    enrolled: int
    already_enrolled: int


class EnrolmentRosterItem(BaseModel):
    student_email: str
    student_id: str | None = None
    status: str
    added_at: datetime


class EnrolmentRosterResponse(BaseModel):
    roster: list[EnrolmentRosterItem]
