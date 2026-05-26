"""
backend/src/admin/authoring_service.py

Service layer for the Curriculum Authoring Studio (super-admin).

PR-A scope: project CRUD, TOC analysis (structure + advisory flow), structure
editing, and materialisation into a *staged* platform curriculum.

Design notes
------------
- All DB access takes an asyncpg connection acquired by the router via
  get_db(request), which stamps app.current_school_id='bypass' for admin
  requests. That bypass is what lets materialize() write owner_type='platform'
  rows past the migration-0046 write-guard (pitfall #28).
- The authoring_* tables are not tenant-scoped (no RLS policy), consistent
  with pipeline_jobs.
- The expensive analyze step (LLM calls) runs in a Celery task; run_analysis()
  is the pure worker body so it is directly unit-testable with a fake provider.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.utils.logger import get_logger

log = get_logger("authoring")


# ── Provider factory (patched in tests) ───────────────────────────────────────


def _build_authoring_provider():
    """Build the default LLM provider for authoring analysis/generation.

    Isolated so tests can patch it with a fake provider instead of reaching
    for a real Anthropic key. Imports are deferred: pipeline.config requires
    ANTHROPIC_API_KEY at import time, which we don't want at module load.
    """
    from pipeline.config import settings as pipeline_settings
    from pipeline.providers import get_provider

    return get_provider(pipeline_settings.DEFAULT_PROVIDER, pipeline_settings)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _row_to_summary(row: asyncpg.Record) -> dict:
    return {
        "project_id": str(row["project_id"]),
        "title": row["title"],
        "grade": row["grade"],
        "languages": list(row["languages"]),
        "status": row["status"],
        "curriculum_id": row["curriculum_id"],
        "visibility": row["visibility"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _coerce_json(value: Any) -> dict | None:
    """asyncpg jsonb codec returns dicts already, but be defensive."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _row_to_detail(row: asyncpg.Record) -> dict:
    detail = _row_to_summary(row)
    detail.update(
        {
            "raw_toc": row["raw_toc"],
            "structured_toc": _coerce_json(row["structured_toc"]),
            "flow_report": _coerce_json(row["flow_report"]),
            "analyze_error": row["analyze_error"],
        }
    )
    return detail


# ── CRUD ───────────────────────────────────────────────────────────────────────


async def create_project(
    conn: asyncpg.Connection,
    *,
    title: str,
    grade: int | None,
    languages: list[str],
    raw_toc: str,
    created_by: uuid.UUID | None,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO authoring_projects (title, grade, languages, raw_toc, created_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        title,
        grade,
        languages,
        raw_toc,
        created_by,
    )
    return _row_to_detail(row)


async def list_projects(conn: asyncpg.Connection) -> tuple[list[dict], int]:
    rows = await conn.fetch("SELECT * FROM authoring_projects ORDER BY created_at DESC")
    return [_row_to_summary(r) for r in rows], len(rows)


async def get_project(conn: asyncpg.Connection, project_id: str) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM authoring_projects WHERE project_id = $1", project_id)
    return _row_to_detail(row) if row else None


async def mark_analyzing(conn: asyncpg.Connection, project_id: str) -> bool:
    """Transition draft → analyzing. Returns False if not in an analyzable state."""
    row = await conn.fetchrow(
        """
        UPDATE authoring_projects
           SET status = 'analyzing', analyze_error = NULL, updated_at = now()
         WHERE project_id = $1
           AND status IN ('draft', 'analyzed', 'structured')
        RETURNING project_id
        """,
        project_id,
    )
    return row is not None


async def save_structure(
    conn: asyncpg.Connection,
    project_id: str,
    structured_toc: dict,
) -> dict | None:
    """Persist operator edits to the structured TOC.

    Allowed once the project has been analysed (status analyzed | structured).
    Returns the updated detail dict, or None if the project is missing / in a
    wrong state.
    """
    row = await conn.fetchrow(
        """
        UPDATE authoring_projects
           SET structured_toc = $2, updated_at = now()
         WHERE project_id = $1
           AND status IN ('analyzed', 'structured')
        RETURNING *
        """,
        project_id,
        structured_toc,
    )
    return _row_to_detail(row) if row else None


# ── Analyze (Celery worker body) ───────────────────────────────────────────────


async def run_analysis(
    conn: asyncpg.Connection,
    project_id: str,
    provider=None,
) -> None:
    """Structure the raw TOC and run advisory flow analysis.

    Idempotent-ish: reads raw_toc, writes structured_toc + flow_report and
    flips status → 'analyzed'. On any structuring failure, records
    analyze_error and reverts status → 'draft' so the operator can retry.

    Never raises — failures are persisted on the row.
    """
    from pipeline.flow_analyzer import analyze_toc_flow
    from pipeline.toc_structurer import StructureError, structure_toc

    row = await conn.fetchrow(
        "SELECT raw_toc, grade FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if row is None:
        log.warning("authoring_analyze_missing_project project_id=%s", project_id)
        return

    if provider is None:
        provider = _build_authoring_provider()

    raw_toc = row["raw_toc"] or ""
    grade = row["grade"]

    try:
        structured = await asyncio.to_thread(structure_toc, raw_toc, grade, provider)
    except StructureError as exc:
        log.warning("authoring_structure_failed project_id=%s error=%s", project_id, exc)
        await conn.execute(
            """
            UPDATE authoring_projects
               SET status = 'draft', analyze_error = $2, updated_at = now()
             WHERE project_id = $1
            """,
            project_id,
            str(exc),
        )
        return

    # Flow analysis is advisory and never raises.
    report = await asyncio.to_thread(analyze_toc_flow, structured, provider)

    await conn.execute(
        """
        UPDATE authoring_projects
           SET structured_toc = $2, flow_report = $3,
               status = 'analyzed', analyze_error = NULL, updated_at = now()
         WHERE project_id = $1
        """,
        project_id,
        structured.model_dump(),
        report.model_dump(),
    )
    log.info(
        "authoring_analyzed project_id=%s subjects=%d flow_warnings=%d",
        project_id,
        len(structured.subjects),
        len(report.warnings),
    )


# ── Materialize ────────────────────────────────────────────────────────────────


_SUBJECT_CODE_RE = re.compile(r"[^A-Z0-9]")


def _subject_code(label: str, index: int) -> str:
    """Derive a short uppercase subject code from a label.

    Falls back to S{index} when the label has no usable alphanumerics, so
    unit_ids stay unique across subjects.
    """
    code = _SUBJECT_CODE_RE.sub("", label.upper())[:6]
    return code or f"S{index + 1}"


class MaterializeError(RuntimeError):
    """Raised when a project cannot be materialised (wrong state / no TOC)."""


async def materialize(
    conn: asyncpg.Connection,
    project_id: str,
    created_by: uuid.UUID | None,
) -> dict:
    """Create a staged platform curriculum + units from the structured TOC.

    The curriculum is owner_type='platform', source_type='admin_authored',
    is_default=FALSE (staged, not in the school catalog yet) and carries no
    school_id — keeping it out of the school namespace (requirement d).

    Idempotent: if the project already has a curriculum_id, returns it without
    creating duplicates.
    """
    row = await conn.fetchrow(
        "SELECT title, grade, structured_toc, curriculum_id, status "
        "FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if row is None:
        raise MaterializeError("project not found")

    structured = _coerce_json(row["structured_toc"])
    if not structured or not structured.get("subjects"):
        raise MaterializeError("project has no structured TOC; analyze and edit first")

    # Idempotent re-call.
    if row["curriculum_id"]:
        units = await conn.fetchval(
            "SELECT COUNT(*) FROM curriculum_units WHERE curriculum_id = $1",
            row["curriculum_id"],
        )
        return {
            "curriculum_id": row["curriculum_id"],
            "status": row["status"],
            "units_created": int(units or 0),
        }

    curriculum_id = f"authored-{project_id}"
    proj8 = str(project_id).replace("-", "")[:8]
    year = _now().year
    grade = row["grade"]

    units_created = 0
    async with conn.transaction():
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, is_default,
                 owner_type, owner_id, school_id, source_type, status)
            VALUES ($1, $2, $3, $4, FALSE,
                    'platform', NULL, NULL, 'admin_authored', 'active')
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id,
            row["title"],
            grade,
            year,
        )

        for s_idx, subject in enumerate(structured["subjects"]):
            subj_code = _subject_code(subject.get("subject_label", ""), s_idx)
            for u_idx, unit in enumerate(subject.get("units", []) or []):
                title = unit.get("title", "")
                unit_id = f"AUTH-{proj8}-{subj_code}-{u_idx + 1:03d}"
                subtopics = unit.get("subtopics", []) or []
                description = "; ".join(subtopics)
                await conn.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, unit_name,
                         description, has_lab, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, FALSE, $7)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    unit_id,
                    curriculum_id,
                    subject.get("subject_label", subj_code),
                    title,
                    title,  # unit_name mirrors title (pitfall #20)
                    description,
                    units_created,
                )
                units_created += 1

        await conn.execute(
            """
            UPDATE authoring_projects
               SET curriculum_id = $2, status = 'structured', updated_at = now()
             WHERE project_id = $1
            """,
            project_id,
            curriculum_id,
        )

    log.info(
        "authoring_materialized project_id=%s curriculum_id=%s units=%d",
        project_id,
        curriculum_id,
        units_created,
    )
    return {
        "curriculum_id": curriculum_id,
        "status": "structured",
        "units_created": units_created,
    }
