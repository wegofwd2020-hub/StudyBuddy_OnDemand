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

import re
from collections.abc import Iterable

import asyncpg

# Subject-code → display name, keyed by the code embedded in a unit_id prefix
# (e.g. "G8-SCI-001" → "SCI" → "Science"). Derived from the canonical names in
# data/grade*_stem.json. Used as a last-resort fallback so progress reports show
# a real subject instead of "Unknown" when a unit has no curriculum_units row.
_SUBJECT_CODE_NAMES: dict[str, str] = {
    "MATH": "Mathematics",
    "SCI": "Science",
    "PHYS": "Physics",
    "CHEM": "Chemistry",
    "BIO": "Biology",
    "TECH": "Technology",
    "ENG": "English",
    "CS": "Computer Science",
    "ACC": "Accountancy",
    "BUS": "Business Studies",
    "ECON": "Economics",
    "COMM": "Commerce",
    "HIST": "History",
    "GEO": "Geography",
    "POL": "Political Science",
    "PSY": "Psychology",
    "SOC": "Sociology",
}

_UNIT_ID_SUBJECT_RE = re.compile(r"^G\d+-([A-Z]+)-")


def subject_from_unit_id(unit_id: str | None) -> str | None:
    """
    Derive a friendly subject name from a unit_id prefix ("G8-SCI-001" →
    "Science"), or None if the code is unrecognised / the id doesn't match the
    G{grade}-{CODE}-{n} shape. Pure helper — no DB.
    """
    if not unit_id:
        return None
    m = _UNIT_ID_SUBJECT_RE.match(unit_id)
    if not m:
        return None
    return _SUBJECT_CODE_NAMES.get(m.group(1))


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
    # Last resort: derive the subject from the unit_id prefix so the chart shows
    # a real subject (and groups into separate bars) instead of collapsing every
    # unresolved unit into a single "Unknown" bar (#473).
    return subject_from_unit_id(unit_id) or "Unknown"
