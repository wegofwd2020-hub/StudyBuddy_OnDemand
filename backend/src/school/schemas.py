"""
backend/src/school/schemas.py

Pydantic request/response models for Phase 8 school endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

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
    enrolment_code: Optional[str] = None
    status: str
    created_at: datetime


class TeacherInviteRequest(BaseModel):
    name: str
    email: EmailStr


class TeacherInviteResponse(BaseModel):
    teacher_id: str
    email: str
    role: str
