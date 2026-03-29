"""
backend/src/account/schemas.py

Pydantic models for account management endpoints.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AccountStatusUpdate(BaseModel):
    """
    PATCH /account/students/{id}/status
    PATCH /account/teachers/{id}/status
    PATCH /account/schools/{id}/status
    """

    status: Literal["active", "suspended"]


class StudentStatusResponse(BaseModel):
    student_id: UUID
    name: str
    email: str
    account_status: str


class TeacherStatusResponse(BaseModel):
    teacher_id: UUID
    school_id: UUID
    name: str
    email: str
    account_status: str


class SchoolStatusResponse(BaseModel):
    school_id: UUID
    name: str
    status: str
