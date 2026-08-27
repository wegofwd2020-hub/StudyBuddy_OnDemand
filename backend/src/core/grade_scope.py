"""
backend/src/core/grade_scope.py

Which grades a teacher may see — one definition, for every router (#647).

#576 established the rule: a teacher sees THEIR grades, `school_admin` sees the
school (a teacher superset, ADR-005). #628 applied it to the six report
endpoints that draw their cohort from `_enrolled_ids()`.

It was then missed twice, because the rule lived as a private helper inside
`reports/router.py`:

  - **Alerts** has its own query rather than going through `_enrolled_ids()`,
    so it was not in the swept set — *and it is in the same file*.
  - **Classrooms** lives in the school router, which could not reach the helper
    at all without importing across routers.

That is the #625 lesson again: scope the CONCEPT, not the endpoints that
happened to be listed in the issue. A rule that only exists inside one module
gets re-missed by every module that cannot import it, so it lives in core.

`None` means unrestricted. A sorted list otherwise, INCLUDING the empty list —
a teacher with no assignments has no cohort and must see nothing rather than
everything. `[]` and `None` must never be collapsed into one another; that
collapse IS the original bug.
"""

from __future__ import annotations

import uuid

import asyncpg


async def permitted_grades(
    conn: asyncpg.Connection, teacher: dict, school_id: str
) -> set[int] | None:
    """Grades this teacher may see, or None meaning "no restriction"."""
    if teacher.get("role") == "school_admin":
        return None

    rows = await conn.fetch(
        """
        SELECT grade FROM teacher_grade_assignments
        WHERE teacher_id = $1 AND school_id = $2
        """,
        uuid.UUID(str(teacher["teacher_id"])),
        uuid.UUID(school_id),
    )
    return {r["grade"] for r in rows}


async def grade_filter(conn: asyncpg.Connection, teacher: dict, school_id: str) -> list[int] | None:
    """`permitted_grades` as the sorted list form query helpers take."""
    permitted = await permitted_grades(conn, teacher, school_id)
    return None if permitted is None else sorted(permitted)
