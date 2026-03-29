"""
backend/src/auth/schemas.py

Pydantic request and response models for auth endpoints.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

# ── Request schemas ───────────────────────────────────────────────────────────


class TokenExchangeRequest(BaseModel):
    """POST /auth/exchange  and  POST /auth/teacher/exchange"""

    id_token: str


class RefreshRequest(BaseModel):
    """POST /auth/refresh"""

    refresh_token: str


class LogoutRequest(BaseModel):
    """POST /auth/logout"""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """
    POST /auth/forgot-password

    Accepts any string containing '@' — strict EmailStr validation is intentionally
    avoided here so that the endpoint always returns 200 regardless of input format,
    preventing enumeration of valid email addresses or formats.
    """

    email: str

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Must be a valid email address.")
        return v.strip().lower()


class StudentProfileUpdate(BaseModel):
    """PATCH /student/profile"""

    name: str | None = None
    locale: Literal["en", "fr", "es"] | None = None
    grade: int | None = None

    @field_validator("grade")
    @classmethod
    def grade_range(cls, v: int | None) -> int | None:
        if v is not None and not (5 <= v <= 12):
            raise ValueError("grade must be between 5 and 12")
        return v


class AdminLoginRequest(BaseModel):
    """POST /admin/auth/login"""

    email: EmailStr
    password: str


class AdminForgotPasswordRequest(BaseModel):
    """POST /admin/auth/forgot-password"""

    email: EmailStr


class AdminResetPasswordRequest(BaseModel):
    """POST /admin/auth/reset-password"""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters.")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────


class StudentPublic(BaseModel):
    """Safe public view of a student record."""

    student_id: UUID
    name: str
    grade: int
    locale: str
    account_status: str


class TeacherPublic(BaseModel):
    """Safe public view of a teacher record."""

    teacher_id: UUID
    school_id: UUID
    name: str
    email: str
    role: str
    account_status: str


class TokenExchangeResponse(BaseModel):
    """Response for POST /auth/exchange"""

    token: str
    refresh_token: str
    student_id: UUID
    student: StudentPublic


class TeacherTokenExchangeResponse(BaseModel):
    """Response for POST /auth/teacher/exchange"""

    token: str
    refresh_token: str
    teacher_id: UUID
    teacher: TeacherPublic


class RefreshResponse(BaseModel):
    """Response for POST /auth/refresh"""

    token: str


class AdminLoginResponse(BaseModel):
    """Response for POST /admin/auth/login"""

    token: str
    admin_id: UUID
