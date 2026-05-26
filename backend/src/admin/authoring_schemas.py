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


# ── PR-B: generate / review / regenerate / snapshot / publish ─────────────────

_CONTENT_TYPES = {
    "lesson", "tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3", "experiment",
}


class GenerateRequest(BaseModel):
    langs: str = "en"  # comma-separated, e.g. "en,fr"
    force: bool = False


class GenerateResponse(BaseModel):
    job_id: str
    status: str  # 'generating'


class TopicVersion(BaseModel):
    topic_version_id: str
    unit_id: str
    lang: str
    content_type: str
    version_number: int
    body: dict | None = None
    regen_reason: str | None = None
    flow_recheck: list | None = None
    review_status: str
    created_at: datetime
    is_active: bool = False


class TopicHistoryResponse(BaseModel):
    versions: list[TopicVersion]


class RegenerateRequest(BaseModel):
    content_type: str
    reason: str = Field(min_length=1, max_length=1000)
    lang: str = "en"

    @field_validator("content_type")
    @classmethod
    def _valid_content_type(cls, v: str) -> str:
        if v not in _CONTENT_TYPES:
            raise ValueError(f"content_type must be one of {sorted(_CONTENT_TYPES)}")
        return v


class RegenerateResponse(BaseModel):
    topic_version_id: str
    version_number: int
    review_status: str
    flow_recheck: list


class AcceptRequest(BaseModel):
    content_type: str
    lang: str = "en"

    @field_validator("content_type")
    @classmethod
    def _valid_content_type(cls, v: str) -> str:
        if v not in _CONTENT_TYPES:
            raise ValueError(f"content_type must be one of {sorted(_CONTENT_TYPES)}")
        return v


class AcceptResponse(BaseModel):
    review_status: str


class SnapshotCreateRequest(BaseModel):
    label: str | None = None


class SnapshotItem(BaseModel):
    snapshot_id: str
    snapshot_number: int
    label: str | None = None
    created_at: datetime


class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotItem]


class RestoreResponse(BaseModel):
    restored: bool


class FlowRecheckResponse(BaseModel):
    job_id: str
    status: str


class PublishRequest(BaseModel):
    visibility: str = "private"

    @field_validator("visibility")
    @classmethod
    def _valid_visibility(cls, v: str) -> str:
        if v not in ("private", "catalog"):
            raise ValueError("visibility must be 'private' or 'catalog'")
        return v


class PublishResponse(BaseModel):
    curriculum_id: str
    visibility: str
    files_written: int
