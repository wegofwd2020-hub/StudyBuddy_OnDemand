from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class GenerateClipsRequest(BaseModel):
    scenario: dict[str, Any]


class ClipStatus(BaseModel):
    turn_index: int
    status: str          # pending | generating | ready | error
    error: str | None = None


class GenerateClipsResponse(BaseModel):
    job_id: str
    scenario_id: str


class ClipsStatusResponse(BaseModel):
    job_id: str
    scenario_id: str
    status: str          # pending | running | done | failed
    total_clips: int
    completed_clips: int
    clips: list[ClipStatus]
    error: str | None = None
