"""
backend/src/analytics/schemas.py

Pydantic schemas for lesson analytics endpoints.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class LessonStartRequest(BaseModel):
    unit_id: str
    curriculum_id: str


class LessonStartResponse(BaseModel):
    view_id: str


class LessonEndRequest(BaseModel):
    view_id: str
    duration_s: int
    audio_played: bool = False
    experiment_viewed: bool = False


class LessonEndResponse(BaseModel):
    view_id: str
    duration_s: int
