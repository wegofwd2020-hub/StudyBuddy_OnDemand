"""
backend/src/notifications/schemas.py

Pydantic schemas for push notification endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class RegisterTokenRequest(BaseModel):
    device_token: str
    platform: str

    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v: str) -> str:
        if v not in ("ios", "android"):
            raise ValueError("platform must be 'ios' or 'android'")
        return v

    @field_validator("device_token")
    @classmethod
    def non_empty_token(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device_token must not be empty")
        return v.strip()


class RegisterTokenResponse(BaseModel):
    token_id: str
    platform: str


class NotificationPreferences(BaseModel):
    streak_reminders: bool = True
    weekly_summary: bool = True
    quiz_nudges: bool = True


class NotificationPreferencesResponse(NotificationPreferences):
    pass
