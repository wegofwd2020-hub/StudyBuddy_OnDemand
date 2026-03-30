"""
backend/src/demo/schemas.py

Pydantic models for the demo student system.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


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
