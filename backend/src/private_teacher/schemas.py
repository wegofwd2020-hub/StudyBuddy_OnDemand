"""
backend/src/private_teacher/schemas.py

Pydantic request/response models for the private teacher endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


# ── Auth schemas ──────────────────────────────────────────────────────────────


class PrivateTeacherRegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class PrivateTeacherLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PrivateTeacherAuthResponse(BaseModel):
    token: str
    teacher_id: str


# ── Profile / subscription schemas ────────────────────────────────────────────


class PrivateTeacherProfile(BaseModel):
    teacher_id: str
    email: str
    name: str
    account_status: str
    created_at: str


class TeacherSubscriptionStatus(BaseModel):
    plan: str | None
    status: str | None
    pipeline_quota_monthly: int
    pipeline_runs_this_month: int
    pipeline_resets_at: str | None
    max_students: int
    current_period_end: str | None


class TeacherCheckoutRequest(BaseModel):
    plan: str  # validated in handler: 'basic' | 'pro'
    success_url: str
    cancel_url: str


class TeacherCheckoutResponse(BaseModel):
    checkout_url: str


class TeacherCancelResponse(BaseModel):
    status: str


# ── Student-facing teacher access schemas ─────────────────────────────────────


class AvailableTeacherItem(BaseModel):
    teacher_id: str
    teacher_name: str
    curricula_count: int


class AvailableTeachersResponse(BaseModel):
    teachers: list[AvailableTeacherItem]


class TeacherAccessCheckoutRequest(BaseModel):
    teacher_id: str
    success_url: str
    cancel_url: str


class TeacherAccessCheckoutResponse(BaseModel):
    checkout_url: str


class TeacherAccessStatus(BaseModel):
    teacher_id: str
    status: str
    valid_until: str | None
