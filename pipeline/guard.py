"""
pipeline/guard.py

Pre-write guard: detects when a pipeline regeneration of OOB content
would affect schools that have already imported and customised that unit.

Usage (called from build_grade.py and build_unit.py before writing files):

    from pipeline.guard import check_school_overrides

    schools = await check_school_overrides(conn, curriculum_id, unit_id, lang)
    if schools:
        log.warning(
            "school_overrides_exist curriculum_id=%s unit_id=%s lang=%s schools=%s",
            curriculum_id, unit_id, lang, schools,
        )
        # Pipeline proceeds — OOB files are updated. School customisations live
        # in unit_content_overrides (DB) and are unaffected. The warning lets
        # the operator know that the "base" content these schools imported from
        # has changed, in case they want to notify affected schools.

The guard does NOT block generation. It surfaces information only.
"""

from __future__ import annotations

import logging

log = logging.getLogger("pipeline.guard")


async def check_school_overrides(
    conn,
    oob_curriculum_id: str,
    unit_id: str,
    lang: str,
) -> list[str]:
    """
    Return the distinct school_ids that have unit_content_overrides rows
    derived (via curricula.source_curriculum_id) from oob_curriculum_id
    for the given unit_id and lang.

    An empty list means no school has imported this unit — safe to regenerate
    without any downstream impact on school customisations.

    Requires the connection to have app.current_school_id = 'bypass' already
    set (standard for all pipeline DB connections since migration 0046).
    """
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT uco.school_id::TEXT AS school_id
            FROM unit_content_overrides uco
            JOIN curricula c ON c.curriculum_id = uco.curriculum_id
            WHERE c.source_curriculum_id = $1
              AND uco.unit_id = $2
              AND uco.lang = $3
            """,
            oob_curriculum_id,
            unit_id,
            lang,
        )
        return [r["school_id"] for r in rows]
    except Exception as exc:
        # Guard is advisory — never let a DB error abort the pipeline.
        log.warning("guard_check_failed curriculum_id=%s unit_id=%s: %s", oob_curriculum_id, unit_id, exc)
        return []
