"""
backend/src/subscription/schemas.py

Pydantic schemas for subscription endpoints.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in ("monthly", "annual"):
            raise ValueError("plan must be 'monthly' or 'annual'")
        return v


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionStatusResponse(BaseModel):
    plan: str                       # free | monthly | annual
    status: Optional[str] = None    # active | cancelled | past_due | None (free tier)
    valid_until: Optional[str] = None
    lessons_accessed: int = 0
    stripe_subscription_id: Optional[str] = None


class CancelResponse(BaseModel):
    status: str  # "cancelled_at_period_end"
    current_period_end: Optional[str] = None
