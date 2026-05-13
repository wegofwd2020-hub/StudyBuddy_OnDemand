"""
backend/src/demo/schemas.py

Pydantic models for the demo student system.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class DemoRequestInput(BaseModel):
    email: EmailStr


class DemoLoginInput(BaseModel):
    email: EmailStr
    password: str


class DemoResendInput(BaseModel):
    email: EmailStr


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    demo_expires_at: datetime


class DemoTestRunRequestInput(BaseModel):
    """
    POST /demo/test-run/request — captures name + email so a single request can
    provision both a demo teacher and a demo student account and email the
    combined credentials to the visitor.
    """

    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        if len(v) > 120:
            raise ValueError("Name must be 120 characters or fewer.")
        return v
