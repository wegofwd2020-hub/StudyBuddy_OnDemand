"""
backend/src/admin/authoring_schemas.py

Pydantic request/response schemas for the Curriculum Authoring Studio
(super-admin TOC-driven content authoring).

PR-A scope: intake → analyze → structure → materialize (endpoints 1-6).
PR-B will add topic generation / regenerate / snapshot / publish schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_LANGS = {"en", "fr", "es"}


# ── Structured TOC tree (mirrors pipeline/toc_structurer.py shapes) ───────────


class TopicNode(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    subtopics: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class SubjectNode(BaseModel):
    subject_label: str = Field(min_length=1, max_length=200)
    units: list[TopicNode] = Field(default_factory=list)

    @field_validator("units")
    @classmethod
    def _at_least_one_unit(cls, v: list[TopicNode]) -> list[TopicNode]:
        if not v:
            raise ValueError("each subject must have at least one unit")
        return v


class StructuredTOC(BaseModel):
    subjects: list[SubjectNode] = Field(default_factory=list)

    @field_validator("subjects")
    @classmethod
    def _at_least_one_subject(cls, v: list[SubjectNode]) -> list[SubjectNode]:
        if not v:
            raise ValueError("structured_toc must have at least one subject")
        return v


# ── Requests ──────────────────────────────────────────────────────────────────


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    grade: int | None = Field(default=None, ge=1, le=12)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    raw_toc: str = Field(min_length=1, max_length=20000)

    @field_validator("languages")
    @classmethod
    def _valid_langs(cls, v: list[str]) -> list[str]:
        if not v:
            return ["en"]
        bad = [lang for lang in v if lang not in _LANGS]
        if bad:
            raise ValueError(f"unsupported languages: {bad}; allowed: {sorted(_LANGS)}")
        return v


class EditStructureRequest(BaseModel):
    structured_toc: StructuredTOC


# ── Responses ──────────────────────────────────────────────────────────────────


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    grade: int | None = None
    languages: list[str]
    status: str
    curriculum_id: str | None = None
    visibility: str
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectSummary):
    raw_toc: str | None = None
    structured_toc: dict | None = None
    flow_report: dict | None = None
    analyze_error: str | None = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]
    total: int


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str  # 'analyzing'


class MaterializeResponse(BaseModel):
    curriculum_id: str
    status: str  # 'structured'
    units_created: int
