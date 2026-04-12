"""
backend/src/demo_leads/schemas.py

Pydantic models for the demo lead request / admin management API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Public request form (L-2) ─────────────────────────────────────────────────


class DemoLeadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    school_org: str = Field(..., min_length=1, max_length=200, alias="school_org")

    model_config = {"populate_by_name": True}


class DemoLeadResponse(BaseModel):
    status: str  # "pending"
    message: str


# ── Admin list / detail (L-3) ─────────────────────────────────────────────────


class DemoLeadItem(BaseModel):
    lead_id: str
    name: str
    email: str
    school_org: str
    ip_country: str | None
    status: str
    token_expires_at: datetime | None
    approved_at: datetime | None
    created_at: datetime


class DemoLeadListResponse(BaseModel):
    leads: list[DemoLeadItem]
    total: int


class DemoLeadApproveRequest(BaseModel):
    ttl_hours: int = Field(default=24, ge=1, le=168)  # 1h – 7 days


class DemoLeadApproveResponse(BaseModel):
    lead_id: str
    demo_url_admin: str
    demo_url_teacher: str
    demo_url_student: str
    token_expires_at: datetime


class DemoLeadRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DemoLeadRejectResponse(BaseModel):
    lead_id: str
    status: str  # "rejected"


# ── Geo-block (L-3) ───────────────────────────────────────────────────────────


class GeoBlockItem(BaseModel):
    country_code: str
    country_name: str | None
    added_at: datetime


class GeoBlockListResponse(BaseModel):
    blocks: list[GeoBlockItem]


class GeoBlockAddRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    country_name: str | None = Field(default=None, max_length=100)


class GeoBlockAddResponse(BaseModel):
    country_code: str
    added: bool  # False if already present
