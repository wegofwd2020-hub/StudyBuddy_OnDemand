"""
backend/src/admin/authoring_generation.py

Per-topic content generation, append-only versioning, and regenerate-with-reason
for the Curriculum Authoring Studio (PR-B).

Content model
-------------
Generated content lives in authoring_topic_versions (append-only) with
authoring_active_versions pointing at the live version per
(project_id, unit_id, lang, content_type). This is the studio working copy;
publish() (authoring_service) writes the *accepted* versions out to the content
store + content_subject_versions so students/admin-review can see them.

Generation uses the shared pipeline prompt builders with diagram_emphasis=True
for lessons + tutorials (Mermaid diagrams, richer prose — counters the "too
terse" feedback). Each response is schema-validated before it is stored.

The expensive full-curriculum generate() runs in a Celery task; regenerate of a
single topic runs synchronously on the request (one LLM call) so the operator
gets the new version + flow recheck back immediately.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

import asyncpg

from src.admin.authoring_flow import check_topic_ordering
from src.admin.authoring_service import (
    _build_authoring_provider,
    _coerce_json,
    ensure_pipeline_path,
)
from src.utils.logger import get_logger

log = get_logger("authoring")

# Quiz sets generated per unit; lesson + tutorial always; experiment only when
# the unit is flagged has_lab.
QUIZ_SETS = 3
BASE_CONTENT_TYPES = ("lesson", "tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3")

# Mirror build_unit's resilience: the LLM occasionally returns malformed JSON
# (e.g. an unescaped LaTeX/markdown backslash) or content that fails schema
# validation. Retry the generate→parse→validate cycle a few times before
# giving up, instead of failing the whole topic on a single bad response.
MAX_GENERATION_ATTEMPTS = 3


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class GenerationError(RuntimeError):
    """Raised when a single content_type cannot be generated/validated."""


def _build_prompt(
    content_type: str, *, unit_id: str, subject: str, topic: str, grade: int, lang: str
) -> str:
    """Build the prompt for a content_type, with diagram emphasis on prose types."""
    from pipeline.prompts import (
        build_experiment_prompt,
        build_lesson_prompt,
        build_quiz_prompt,
        build_tutorial_prompt,
    )

    g = grade or 8
    if content_type == "lesson":
        return build_lesson_prompt(unit_id, subject, topic, g, lang, diagram_emphasis=True)
    if content_type == "tutorial":
        return build_tutorial_prompt(unit_id, subject, topic, g, lang, diagram_emphasis=True)
    if content_type.startswith("quiz_set_"):
        set_number = int(content_type.rsplit("_", 1)[1])
        return build_quiz_prompt(unit_id, subject, topic, g, lang, set_number, QUIZ_SETS)
    if content_type == "experiment":
        return build_experiment_prompt(unit_id, subject, topic, g, lang)
    raise GenerationError(f"unknown content_type {content_type!r}")


def _validate(content_type: str, body: dict) -> None:
    from pipeline.schemas import (
        validate_experiment,
        validate_lesson,
        validate_quiz,
        validate_tutorial,
    )

    if content_type == "lesson":
        validate_lesson(body)
    elif content_type == "tutorial":
        validate_tutorial(body)
    elif content_type.startswith("quiz_set_"):
        validate_quiz(body)
    elif content_type == "experiment":
        validate_experiment(body)


def generate_one(
    provider,
    *,
    content_type: str,
    unit_id: str,
    subject: str,
    topic: str,
    grade: int,
    lang: str,
) -> tuple[dict, int]:
    """Generate + validate one content_type. Returns (body, total_tokens).

    Retries the generate→parse→validate cycle up to MAX_GENERATION_ATTEMPTS
    times — the LLM intermittently returns malformed JSON or schema-invalid
    content, and a fresh attempt usually succeeds. Tokens are summed across all
    attempts (failed attempts still cost). Raises GenerationError only after all
    attempts are exhausted; the caller decides whether to skip or surface it.
    """
    ensure_pipeline_path()  # API (sync regenerate) needs pipeline on sys.path
    prompt = _build_prompt(
        content_type, unit_id=unit_id, subject=subject, topic=topic, grade=grade, lang=lang
    )

    total_tokens = 0
    last_error = "unknown error"
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            text, in_tok, out_tok = provider.generate(prompt)
            total_tokens += int(in_tok) + int(out_tok)
        except Exception as exc:  # provider SDKs raise their own error types
            last_error = f"provider error: {exc}"
        else:
            try:
                body = json.loads(_strip_code_fences(text))
                _validate(content_type, body)
            except json.JSONDecodeError as exc:
                last_error = f"bad JSON: {exc}"
            except Exception as exc:  # jsonschema.ValidationError
                last_error = f"schema validation failed: {exc}"
            else:
                return body, total_tokens

        if attempt < MAX_GENERATION_ATTEMPTS:
            log.warning(
                "authoring_generate_retry content_type=%s attempt=%d/%d error=%s",
                content_type,
                attempt,
                MAX_GENERATION_ATTEMPTS,
                last_error,
            )

    raise GenerationError(
        f"{content_type} failed after {MAX_GENERATION_ATTEMPTS} attempts: {last_error}"
    )


# ── Append-only version + active pointer helpers ──────────────────────────────


async def next_version_number(
    conn: asyncpg.Connection, project_id: str, unit_id: str, lang: str, content_type: str
) -> int:
    row = await conn.fetchval(
        """
        SELECT COALESCE(MAX(version_number), 0)
          FROM authoring_topic_versions
         WHERE project_id = $1 AND unit_id = $2 AND lang = $3 AND content_type = $4
        """,
        project_id,
        unit_id,
        lang,
        content_type,
    )
    return int(row or 0) + 1


async def append_topic_version(
    conn: asyncpg.Connection,
    *,
    project_id: str,
    unit_id: str,
    lang: str,
    content_type: str,
    body: dict,
    regen_reason: str | None = None,
    flow_recheck: list | None = None,
    ai_model: str | None = None,
    tokens_used: int | None = None,
    created_by: uuid.UUID | None = None,
    set_active: bool = True,
) -> dict:
    """Insert a new append-only version and (optionally) point active at it."""
    version_number = await next_version_number(conn, project_id, unit_id, lang, content_type)
    row = await conn.fetchrow(
        """
        INSERT INTO authoring_topic_versions
            (project_id, unit_id, lang, content_type, body, version_number,
             regen_reason, flow_recheck, ai_model, tokens_used, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING topic_version_id, version_number, review_status, created_at
        """,
        project_id,
        unit_id,
        lang,
        content_type,
        body,
        version_number,
        regen_reason,
        flow_recheck,
        ai_model,
        tokens_used,
        created_by,
    )
    topic_version_id = row["topic_version_id"]
    if set_active:
        await set_active_version(conn, project_id, unit_id, lang, content_type, topic_version_id)
    return {
        "topic_version_id": str(topic_version_id),
        "version_number": row["version_number"],
        "review_status": row["review_status"],
        "created_at": row["created_at"],
    }


async def set_active_version(
    conn: asyncpg.Connection,
    project_id: str,
    unit_id: str,
    lang: str,
    content_type: str,
    topic_version_id,
) -> None:
    await conn.execute(
        """
        INSERT INTO authoring_active_versions
            (project_id, unit_id, lang, content_type, topic_version_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (project_id, unit_id, lang, content_type)
        DO UPDATE SET topic_version_id = EXCLUDED.topic_version_id,
                      activated_at = now()
        """,
        project_id,
        unit_id,
        lang,
        content_type,
        topic_version_id,
    )


def _version_row_to_dict(row: asyncpg.Record) -> dict:
    return {
        "topic_version_id": str(row["topic_version_id"]),
        "unit_id": row["unit_id"],
        "lang": row["lang"],
        "content_type": row["content_type"],
        "version_number": row["version_number"],
        "body": _coerce_json(row["body"]),
        "regen_reason": row["regen_reason"],
        "flow_recheck": _coerce_json(row["flow_recheck"]),
        "review_status": row["review_status"],
        "created_at": row["created_at"],
        "is_active": row["is_active"],
    }


async def get_active_topic(
    conn: asyncpg.Connection, project_id: str, unit_id: str, content_type: str, lang: str
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT tv.*, (av.topic_version_id = tv.topic_version_id) AS is_active
          FROM authoring_active_versions av
          JOIN authoring_topic_versions tv ON tv.topic_version_id = av.topic_version_id
         WHERE av.project_id = $1 AND av.unit_id = $2
           AND av.content_type = $3 AND av.lang = $4
        """,
        project_id,
        unit_id,
        content_type,
        lang,
    )
    return _version_row_to_dict(row) if row else None


async def get_topic_history(
    conn: asyncpg.Connection, project_id: str, unit_id: str, content_type: str, lang: str
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT tv.*,
               (av.topic_version_id = tv.topic_version_id) AS is_active
          FROM authoring_topic_versions tv
          LEFT JOIN authoring_active_versions av
                 ON av.project_id = tv.project_id AND av.unit_id = tv.unit_id
                AND av.lang = tv.lang AND av.content_type = tv.content_type
         WHERE tv.project_id = $1 AND tv.unit_id = $2
           AND tv.content_type = $3 AND tv.lang = $4
         ORDER BY tv.version_number DESC
        """,
        project_id,
        unit_id,
        content_type,
        lang,
    )
    return [_version_row_to_dict(r) for r in rows]


# ── Generation worker bodies ──────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def generate_topics(
    conn: asyncpg.Connection,
    project_id: str,
    *,
    langs: list[str] | None = None,
    force: bool = False,
    provider=None,
) -> dict:
    """Generate content for every unit in a materialised project.

    For each unit × lang × content_type, generates + validates content and
    stores it as version 1 (or skips if a version already exists and not
    force). Flips status generating → generated. Returns a summary count.
    Never raises on a single-topic failure — failures are counted.
    """
    proj = await conn.fetchrow(
        "SELECT grade, curriculum_id, status FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if proj is None or not proj["curriculum_id"]:
        log.warning("authoring_generate_not_materialized project_id=%s", project_id)
        return {"generated": 0, "failed": 0, "skipped": 0}

    langs = langs or ["en"]
    if provider is None:
        provider = _build_authoring_provider()
    model = getattr(provider, "model", None)

    units = await conn.fetch(
        "SELECT unit_id, subject, title, has_lab FROM curriculum_units "
        "WHERE curriculum_id = $1 ORDER BY sort_order",
        proj["curriculum_id"],
    )

    await conn.execute(
        "UPDATE authoring_projects SET status = 'generating', updated_at = now() "
        "WHERE project_id = $1",
        project_id,
    )

    generated = failed = skipped = 0
    for unit in units:
        content_types = list(BASE_CONTENT_TYPES)
        if unit["has_lab"]:
            content_types.append("experiment")
        for lang in langs:
            for content_type in content_types:
                if not force:
                    existing = await conn.fetchval(
                        "SELECT 1 FROM authoring_active_versions "
                        "WHERE project_id=$1 AND unit_id=$2 AND lang=$3 AND content_type=$4",
                        project_id,
                        unit["unit_id"],
                        lang,
                        content_type,
                    )
                    if existing:
                        skipped += 1
                        continue
                try:
                    body, tokens = await asyncio.to_thread(
                        generate_one,
                        provider,
                        content_type=content_type,
                        unit_id=unit["unit_id"],
                        subject=unit["subject"],
                        topic=unit["title"],
                        grade=proj["grade"],
                        lang=lang,
                    )
                except GenerationError as exc:
                    failed += 1
                    log.warning(
                        "authoring_generate_topic_failed project_id=%s unit=%s type=%s err=%s",
                        project_id,
                        unit["unit_id"],
                        content_type,
                        exc,
                    )
                    continue
                await append_topic_version(
                    conn,
                    project_id=project_id,
                    unit_id=unit["unit_id"],
                    lang=lang,
                    content_type=content_type,
                    body=body,
                    ai_model=model,
                    tokens_used=tokens,
                )
                generated += 1

    await conn.execute(
        "UPDATE authoring_projects SET status = 'generated', updated_at = now() "
        "WHERE project_id = $1",
        project_id,
    )
    log.info(
        "authoring_generated project_id=%s generated=%d failed=%d skipped=%d",
        project_id,
        generated,
        failed,
        skipped,
    )
    return {"generated": generated, "failed": failed, "skipped": skipped}


async def regenerate_topic(
    conn: asyncpg.Connection,
    project_id: str,
    unit_id: str,
    *,
    content_type: str,
    reason: str,
    lang: str = "en",
    provider=None,
    created_by: uuid.UUID | None = None,
) -> dict:
    """Regenerate a single topic's content with a reason (unlimited).

    Appends a new version, runs the cheap deterministic flow recheck over the
    current structured TOC (requirement f), stores it on the version, and points
    active at the new version. Returns the new version summary + flow_recheck.
    """
    proj = await conn.fetchrow(
        "SELECT grade, structured_toc FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if proj is None:
        raise GenerationError("project not found")
    unit = await conn.fetchrow(
        "SELECT cu.subject, cu.title FROM authoring_projects ap "
        "JOIN curriculum_units cu ON cu.curriculum_id = ap.curriculum_id "
        "WHERE ap.project_id = $1 AND cu.unit_id = $2",
        project_id,
        unit_id,
    )
    if unit is None:
        raise GenerationError("unit not found for project")

    if provider is None:
        provider = _build_authoring_provider()
    model = getattr(provider, "model", None)

    body, tokens = await asyncio.to_thread(
        generate_one,
        provider,
        content_type=content_type,
        unit_id=unit_id,
        subject=unit["subject"],
        topic=unit["title"],
        grade=proj["grade"],
        lang=lang,
    )

    # Cheap, deterministic flow recheck on the current structured TOC.
    flow_warnings = check_topic_ordering(_coerce_json(proj["structured_toc"]) or {})

    result = await append_topic_version(
        conn,
        project_id=project_id,
        unit_id=unit_id,
        lang=lang,
        content_type=content_type,
        body=body,
        regen_reason=reason,
        flow_recheck=flow_warnings,
        ai_model=model,
        tokens_used=tokens,
        created_by=created_by,
    )
    result["flow_recheck"] = flow_warnings
    return result


async def accept_topic(
    conn: asyncpg.Connection, project_id: str, unit_id: str, content_type: str, lang: str
) -> bool:
    """Mark the active version of a topic as accepted. False if no active version."""
    row = await conn.fetchrow(
        """
        UPDATE authoring_topic_versions tv
           SET review_status = 'accepted'
          FROM authoring_active_versions av
         WHERE av.topic_version_id = tv.topic_version_id
           AND av.project_id = $1 AND av.unit_id = $2
           AND av.content_type = $3 AND av.lang = $4
        RETURNING tv.topic_version_id
        """,
        project_id,
        unit_id,
        content_type,
        lang,
    )
    return row is not None


async def list_topics(conn: asyncpg.Connection, project_id: str) -> dict | None:
    """List the materialised units of a project with per-content-type status.

    The UI needs to enumerate topics (PR-B only exposed single-topic GET).
    Returns None if the project doesn't exist; an empty topics list if it
    hasn't been materialised yet.
    """
    proj = await conn.fetchrow(
        "SELECT grade, curriculum_id, status FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if proj is None:
        return None
    if not proj["curriculum_id"]:
        return {"curriculum_id": None, "status": proj["status"], "topics": [], "total": 0}

    units = await conn.fetch(
        "SELECT unit_id, subject, title FROM curriculum_units "
        "WHERE curriculum_id = $1 ORDER BY sort_order",
        proj["curriculum_id"],
    )
    actives = await conn.fetch(
        """
        SELECT av.unit_id, av.content_type, av.lang,
               tv.version_number, tv.review_status
          FROM authoring_active_versions av
          JOIN authoring_topic_versions tv ON tv.topic_version_id = av.topic_version_id
         WHERE av.project_id = $1
        """,
        project_id,
    )
    by_unit: dict[str, list[dict]] = {}
    for a in actives:
        by_unit.setdefault(a["unit_id"], []).append(
            {
                "content_type": a["content_type"],
                "lang": a["lang"],
                "version_number": a["version_number"],
                "review_status": a["review_status"],
            }
        )

    topics = []
    for u in units:
        contents = sorted(by_unit.get(u["unit_id"], []), key=lambda c: c["content_type"])
        topics.append(
            {
                "unit_id": u["unit_id"],
                "title": u["title"],
                "subject": u["subject"],
                "contents": contents,
                "content_count": len(contents),
                "accepted_count": sum(1 for c in contents if c["review_status"] == "accepted"),
            }
        )
    return {
        "curriculum_id": proj["curriculum_id"],
        "status": proj["status"],
        "topics": topics,
        "total": len(topics),
    }
