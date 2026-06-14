"""
backend/src/core/subjects.py

Subject-label resolution shared across the read paths (progress history, student
metrics, student stats, teacher student-report).

Why this exists — feedback issue #462 ("Subject shows 'Unknown' everywhere"):
`progress_sessions.subject` stores a subject *code* (e.g. "G8-SCI"), or the
literal "unknown" when the unit could not be resolved at session-create time.
The human-readable name (e.g. "Natural Sciences") lives in
`content_subject_versions.subject_name` (CLAUDE.md pitfall #32). Reporting
queries that surface `progress_sessions.subject` directly therefore show codes
or "unknown" instead of real names.

`resolve_subject_labels()` maps a set of unit_ids → display name by joining
`curriculum_units` (the authoritative code per unit) to
`content_subject_versions` (the display name), independent of whatever is stored
on the session row. Callers fall back to their stored value / "Unknown" for any
unit_id the map doesn't cover.
"""

from __future__ import annotations

from collections.abc import Iterable

import asyncpg


async def resolve_subject_labels(
    conn: asyncpg.Connection,
    unit_ids: Iterable[str],
) -> dict[str, str]:
    """
    Return {unit_id: subject_display_name} for the given unit_ids.

    Prefers `content_subject_versions.subject_name`; falls back to the raw
    `curriculum_units.subject` code. unit_ids with no curriculum_units row are
    omitted (the caller decides the fallback). The DISTINCT ON keeps one label
    per unit_id even when multiple content versions exist, so this never fans
    out a caller's aggregate counts.
    """
    ids = [u for u in dict.fromkeys(unit_ids) if u]  # dedupe, drop falsy
    if not ids:
        return {}

    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (cu.unit_id)
               cu.unit_id,
               COALESCE(csv.subject_name, cu.subject) AS subject_label
        FROM curriculum_units cu
        LEFT JOIN content_subject_versions csv
            ON  csv.curriculum_id = cu.curriculum_id
            AND csv.subject       = cu.subject
            AND csv.subject_name IS NOT NULL
        WHERE cu.unit_id = ANY($1::text[])
        ORDER BY cu.unit_id, csv.version_number DESC NULLS LAST
        """,
        ids,
    )
    return {r["unit_id"]: r["subject_label"] for r in rows if r["subject_label"]}


def display_subject(
    label_map: dict[str, str],
    unit_id: str,
    stored_subject: str | None,
) -> str:
    """
    Resolve the best display name for one row: the curriculum-derived label,
    else the stored subject (unless it's the "unknown" sentinel), else "Unknown".
    """
    label = label_map.get(unit_id)
    if label:
        return label
    if stored_subject and stored_subject.lower() != "unknown":
        return stored_subject
    return "Unknown"
