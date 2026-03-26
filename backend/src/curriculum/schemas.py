"""
backend/src/curriculum/schemas.py

Pydantic models for curriculum endpoints.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Existing grade-tree schemas ───────────────────────────────────────────────

class Unit(BaseModel):
    unit_id: str
    title: str
    description: str
    has_lab: bool


class Subject(BaseModel):
    subject_id: str
    name: str
    units: List[Unit]


class GradeCurriculum(BaseModel):
    grade: int
    subjects: List[Subject]


class GradeSummary(BaseModel):
    grade: int
    subject_count: int
    unit_count: int


# ── Phase 8: curriculum upload ────────────────────────────────────────────────

class CurriculumUnitInput(BaseModel):
    subject: str
    unit_name: str
    unit_id: Optional[str] = None
    objectives: List[str]
    has_lab: bool = False
    lab_description: Optional[str] = None


class CurriculumUploadRequest(BaseModel):
    grade: int = Field(..., ge=5, le=12)
    year: int = Field(..., ge=2020, le=2099)
    name: str
    units: List[CurriculumUnitInput]


class UploadError(BaseModel):
    row: int
    field: str
    message: str


class CurriculumUploadResponse(BaseModel):
    curriculum_id: Optional[str] = None
    unit_count: int
    errors: List[UploadError] = []


# ── Phase 8: pipeline trigger + job status ────────────────────────────────────

class PipelineTriggerRequest(BaseModel):
    curriculum_id: str
    langs: str = "en"
    force: bool = False


class PipelineTriggerResponse(BaseModel):
    job_id: str
    status: str


class PipelineJobStatusResponse(BaseModel):
    job_id: str
    status: str
    built: int
    failed: int
    total: int
    progress_pct: float
