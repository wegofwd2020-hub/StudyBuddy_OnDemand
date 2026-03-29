"""
backend/src/curriculum/schemas.py

Pydantic models for curriculum endpoints.
"""

from __future__ import annotations

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
    units: list[Unit]


class GradeCurriculum(BaseModel):
    grade: int
    subjects: list[Subject]


class GradeSummary(BaseModel):
    grade: int
    subject_count: int
    unit_count: int


# ── Phase 8: curriculum upload ────────────────────────────────────────────────


class CurriculumUnitInput(BaseModel):
    subject: str
    unit_name: str
    unit_id: str | None = None
    objectives: list[str]
    has_lab: bool = False
    lab_description: str | None = None


class CurriculumUploadRequest(BaseModel):
    grade: int = Field(..., ge=5, le=12)
    year: int = Field(..., ge=2020, le=2099)
    name: str
    units: list[CurriculumUnitInput]


class UploadError(BaseModel):
    row: int
    field: str
    message: str


class CurriculumUploadResponse(BaseModel):
    curriculum_id: str | None = None
    unit_count: int
    errors: list[UploadError] = []


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


# ── Phase 9: curriculum activation ────────────────────────────────────────────


class CurriculumActivateResponse(BaseModel):
    curriculum_id: str
    status: str
    archived_count: int
