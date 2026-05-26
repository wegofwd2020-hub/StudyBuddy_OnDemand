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
    detail.update({
        "raw_toc": row["raw_toc"],
        "structured_toc": _coerce_json(row["structured_toc"]),
        "flow_report": _coerce_json(row["flow_report"]),
        "analyze_error": row["analyze_error"],
    })
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
    rows = await conn.fetch(
        "SELECT * FROM authoring_projects ORDER BY created_at DESC"
    )
    return [_row_to_summary(r) for r in rows], len(rows)


async def get_project(conn: asyncpg.Connection, project_id: str) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM authoring_projects WHERE project_id = $1", project_id
    )
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


# ── Snapshots (whole-curriculum manifest) ─────────────────────────────────────


def _manifest_key(unit_id: str, content_type: str, lang: str) -> str:
    return f"{unit_id}::{content_type}::{lang}"


async def create_snapshot(
    conn: asyncpg.Connection,
    project_id: str,
    *,
    label: str | None,
    created_by: uuid.UUID | None,
) -> dict:
    """Capture the current active-version pointers + structured TOC as a snapshot.

    The manifest references topic_version_ids (no content copy) so a restore is
    a cheap pointer rewrite — the chosen per-topic-history + manifest model
    (requirement g).
    """
    actives = await conn.fetch(
        "SELECT unit_id, content_type, lang, topic_version_id "
        "FROM authoring_active_versions WHERE project_id = $1",
        project_id,
    )
    manifest = {
        "versions": {
            _manifest_key(r["unit_id"], r["content_type"], r["lang"]): str(r["topic_version_id"])
            for r in actives
        },
        "structured_toc": _coerce_json(
            await conn.fetchval(
                "SELECT structured_toc FROM authoring_projects WHERE project_id = $1",
                project_id,
            )
        ),
    }
    snapshot_number = int(
        await conn.fetchval(
            "SELECT COALESCE(MAX(snapshot_number), 0) FROM authoring_snapshots "
            "WHERE project_id = $1",
            project_id,
        ) or 0
    ) + 1

    row = await conn.fetchrow(
        """
        INSERT INTO authoring_snapshots (project_id, snapshot_number, manifest, label, created_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING snapshot_id, snapshot_number, created_at
        """,
        project_id, snapshot_number, manifest, label, created_by,
    )
    await conn.execute(
        "UPDATE authoring_projects SET current_snapshot_id = $2, updated_at = now() "
        "WHERE project_id = $1",
        project_id, row["snapshot_id"],
    )
    return {
        "snapshot_id": str(row["snapshot_id"]),
        "snapshot_number": row["snapshot_number"],
        "label": label,
        "created_at": row["created_at"],
    }


async def list_snapshots(conn: asyncpg.Connection, project_id: str) -> list[dict]:
    rows = await conn.fetch(
        "SELECT snapshot_id, snapshot_number, label, created_at FROM authoring_snapshots "
        "WHERE project_id = $1 ORDER BY snapshot_number DESC",
        project_id,
    )
    return [
        {
            "snapshot_id": str(r["snapshot_id"]),
            "snapshot_number": r["snapshot_number"],
            "label": r["label"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


async def restore_snapshot(conn: asyncpg.Connection, project_id: str, snapshot_id: str) -> bool:
    """Rewrite active-version pointers from a snapshot's manifest.

    Returns False if the snapshot doesn't belong to the project. Restores the
    whole curriculum to the snapshot's point in time without copying content.
    """
    manifest = _coerce_json(
        await conn.fetchval(
            "SELECT manifest FROM authoring_snapshots "
            "WHERE snapshot_id = $1 AND project_id = $2",
            snapshot_id, project_id,
        )
    )
    if manifest is None:
        return False

    versions = (manifest or {}).get("versions", {})
    async with conn.transaction():
        for key, topic_version_id in versions.items():
            unit_id, content_type, lang = key.split("::")
            await conn.execute(
                """
                INSERT INTO authoring_active_versions
                    (project_id, unit_id, lang, content_type, topic_version_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (project_id, unit_id, lang, content_type)
                DO UPDATE SET topic_version_id = EXCLUDED.topic_version_id,
                              activated_at = now()
                """,
                project_id, unit_id, lang, content_type, uuid.UUID(topic_version_id),
            )
        await conn.execute(
            "UPDATE authoring_projects SET current_snapshot_id = $2, updated_at = now() "
            "WHERE project_id = $1",
            project_id, uuid.UUID(snapshot_id),
        )
    return True


# ── Publish ────────────────────────────────────────────────────────────────────


class PublishError(RuntimeError):
    """Raised when a project cannot be published (wrong state / unaccepted topics)."""


# content_type → content-store filename stem (filename = f"{stem}_{lang}.json").
_CONTENT_FILENAMES = {
    "lesson": "lesson",
    "tutorial": "tutorial",
    "quiz_set_1": "quiz_set_1",
    "quiz_set_2": "quiz_set_2",
    "quiz_set_3": "quiz_set_3",
    "experiment": "experiment",
}


async def publish(
    conn: asyncpg.Connection,
    storage,
    project_id: str,
    *,
    visibility: str,
) -> dict:
    """Publish an authored curriculum.

    Requires status='generated' and every active topic version accepted. Writes
    accepted bodies to the content store, creates content_subject_versions rows
    (status='published') per subject, sets curricula.is_default = (visibility ==
    'catalog'), and flips the project to status='published'.
    """
    proj = await conn.fetchrow(
        "SELECT curriculum_id, status FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if proj is None:
        raise PublishError("project not found")
    if not proj["curriculum_id"]:
        raise PublishError("project has not been materialized")
    if proj["status"] not in ("generated", "published"):
        raise PublishError(
            f"project is in status {proj['status']!r}; generate content before publishing"
        )

    curriculum_id = proj["curriculum_id"]

    # Gate: every active topic version must be accepted.
    actives = await conn.fetch(
        """
        SELECT tv.unit_id, tv.lang, tv.content_type, tv.body, tv.review_status
          FROM authoring_active_versions av
          JOIN authoring_topic_versions tv ON tv.topic_version_id = av.topic_version_id
         WHERE av.project_id = $1
        """,
        project_id,
    )
    if not actives:
        raise PublishError("nothing to publish — generate content first")
    unaccepted = [a for a in actives if a["review_status"] != "accepted"]
    if unaccepted:
        raise PublishError(
            f"{len(unaccepted)} topic version(s) are not accepted; accept all before publishing"
        )

    # Write accepted bodies to the content store.
    for a in actives:
        stem = _CONTENT_FILENAMES.get(a["content_type"])
        if not stem:
            continue
        path = f"curricula/{curriculum_id}/{a['unit_id']}/{stem}_{a['lang']}.json"
        body = _coerce_json(a["body"]) or {}
        await storage.write(path, json.dumps(body, ensure_ascii=False).encode("utf-8"))

    # content_subject_versions per distinct subject (status published).
    subjects = await conn.fetch(
        "SELECT DISTINCT subject FROM curriculum_units WHERE curriculum_id = $1",
        curriculum_id,
    )
    pipeline_run_id = f"authoring-{project_id}"
    for s in subjects:
        subject = s["subject"]
        next_version = int(
            await conn.fetchval(
                "SELECT COALESCE(MAX(version_number), 0) FROM content_subject_versions "
                "WHERE curriculum_id = $1 AND subject = $2",
                curriculum_id, subject,
            ) or 0
        ) + 1
        await conn.execute(
            """
            INSERT INTO content_subject_versions
                (curriculum_id, subject, subject_name, version_number, status,
                 alex_warnings_count, provider, generated_at, published_at, pipeline_run_id)
            VALUES ($1, $2, $3, $4, 'published', 0, 'anthropic', NOW(), NOW(), $5)
            ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE
                SET status = 'published', published_at = NOW()
            """,
            curriculum_id, subject, subject, next_version, pipeline_run_id,
        )

    is_catalog = visibility == "catalog"
    await conn.execute(
        "UPDATE curricula SET is_default = $2 WHERE curriculum_id = $1",
        curriculum_id, is_catalog,
    )
    await conn.execute(
        "UPDATE authoring_projects SET visibility = $2, status = 'published', updated_at = now() "
        "WHERE project_id = $1",
        project_id, visibility,
    )

    log.info(
        "authoring_published project_id=%s curriculum_id=%s visibility=%s files=%d",
        project_id, curriculum_id, visibility, len(actives),
    )
    return {
        "curriculum_id": curriculum_id,
        "visibility": visibility,
        "files_written": len(actives),
    }


# ── On-demand full flow re-analysis (Celery worker body) ──────────────────────


async def run_flow_recheck(conn: asyncpg.Connection, project_id: str, provider=None) -> None:
    """Re-run the advisory LLM flow analysis over the CURRENT structured TOC.

    Unlike run_analysis (which re-structures raw_toc), this preserves operator
    edits and only refreshes flow_report. Never raises.
    """
    from pipeline.flow_analyzer import analyze_toc_flow

    structured = _coerce_json(
        await conn.fetchval(
            "SELECT structured_toc FROM authoring_projects WHERE project_id = $1",
            project_id,
        )
    )
    if not structured:
        return
    if provider is None:
        provider = _build_authoring_provider()
    report = await asyncio.to_thread(analyze_toc_flow, structured, provider)
    await conn.execute(
        "UPDATE authoring_projects SET flow_report = $2, updated_at = now() "
        "WHERE project_id = $1",
        project_id,
        report.model_dump(),
    )
