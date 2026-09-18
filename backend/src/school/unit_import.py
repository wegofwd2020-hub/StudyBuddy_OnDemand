"""
backend/src/school/unit_import.py

Importing one unit's OOB content into a school's own fork (Epic 12, TA-2).

Extracted verbatim from `school/router.py::import_unit_content` so a second
caller can REUSE it rather than re-derive its SQL. Correcting a quiz answer
(#762) has to take the school's own copy of a unit before it can change
anything in it, and "take your own copy" is precisely this operation: adoption
gate, lazy fork, grade repoint, probe the content store, insert the draft
override rows. Two copies of that would drift, and the half that drifted would
be the one nobody reads.

`grade_repointed` is returned alongside `fork_created` because creating the fork
UPSERTS `grade_curriculum_assignments` for the whole grade — every student of
that grade now resolves to the school's copy. The import endpoint has always
done this; it has never said so. #762's confirmation copy has to.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import HTTPException

from src.core.storage import StorageBackend
from src.utils.logger import get_logger

log = get_logger("school")

# Content types probed in order; tutorial package (tutorial + quiz sets) share
# a bundle_id so their review-status transitions are atomic.
IMPORT_CONTENT_TYPES: list[tuple[str, str]] = [
    ("lesson", "lesson_{lang}.json"),
    ("tutorial", "tutorial_{lang}.json"),
    ("quiz_set_1", "quiz_set_1_{lang}.json"),
    ("quiz_set_2", "quiz_set_2_{lang}.json"),
    ("quiz_set_3", "quiz_set_3_{lang}.json"),
    ("experiment", "experiment_{lang}.json"),
]
TUTORIAL_BUNDLE_TYPES = {"tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3"}


async def import_unit_overrides(
    conn,
    storage: StorageBackend,
    *,
    school_id: str,
    adoption_id: str,
    unit_id: str,
    teacher_id: str,
    lang: str = "en",
) -> dict:
    """Import OOB content for one unit into the school's fork as draft overrides.

    1. Adoption gate — 403 if not adopted or deactivated, 404 if unknown.
    2. Creates the school's forked `curricula` row on first call (lazy fork),
       and repoints `grade_curriculum_assignments` for that grade.
    3. Probes the Content Store for available content types for this unit/lang.
    4. Inserts `unit_content_overrides` rows for each type not yet imported.
       Tutorial package rows (tutorial + quiz_set_*) share a bundle_id.

    Idempotent: re-calling for an already-imported unit returns the existing
    rows with `skipped=True` and creates nothing.

    Returns {forked_curriculum_id, fork_created, grade_repointed, overrides}.
    Raises HTTPException — it is called from request handlers only, and the
    404/403 it raises are the caller's answer either way.
    """
    from src.school.schemas import OverrideItem

    # 1. Adoption gate ────────────────────────────────────────────────────────
    adoption = await conn.fetchrow(
        "SELECT sac.adoption_id, sac.curriculum_id, sac.forked_curriculum_id, "
        "sac.status, c.name, c.grade, c.year, c.owner_id "
        "FROM school_adopted_curricula sac "
        "JOIN curricula c ON c.curriculum_id = sac.curriculum_id "
        "WHERE sac.school_id = $1 AND sac.adoption_id = $2",
        school_id,
        adoption_id,
    )
    if not adoption:
        raise HTTPException(status_code=404, detail="Adoption not found")
    if adoption["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail="This curriculum has been deactivated in your library",
        )

    oob_curriculum_id = adoption["curriculum_id"]
    forked_curriculum_id = adoption["forked_curriculum_id"]
    fork_created = False
    grade_repointed = False

    # 2. Lazy fork creation ───────────────────────────────────────────────────
    if forked_curriculum_id is None:
        new_id = str(_uuid.uuid4())
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO curricula
                    (curriculum_id, name, grade, year, is_default,
                     owner_type, owner_id, school_id, source_curriculum_id)
                VALUES ($1, $2, $3, $4, FALSE, 'school', $5, $5, $6)
                """,
                new_id,
                adoption["name"],
                adoption["grade"],
                adoption["year"],
                school_id,
                oob_curriculum_id,
            )
            await conn.execute(
                "UPDATE school_adopted_curricula "
                "SET forked_curriculum_id = $1 "
                "WHERE school_id = $2 AND adoption_id = $3",
                new_id,
                school_id,
                adoption_id,
            )
            # Point this grade at the school fork (UPSERT — grade is PK per school)
            if adoption["grade"] is not None:
                await conn.execute(
                    """
                    INSERT INTO grade_curriculum_assignments
                        (school_id, grade, curriculum_id, assigned_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (school_id, grade)
                    DO UPDATE SET curriculum_id = EXCLUDED.curriculum_id,
                                  assigned_by  = EXCLUDED.assigned_by
                    """,
                    school_id,
                    adoption["grade"],
                    new_id,
                    teacher_id,
                )
                grade_repointed = True
        forked_curriculum_id = new_id
        fork_created = True
        log.info(
            "curriculum_fork_created",
            school_id=school_id,
            oob_curriculum_id=oob_curriculum_id,
            forked_curriculum_id=forked_curriculum_id,
            grade_repointed=grade_repointed,
        )

    # 3. Probe Content Store for available types ──────────────────────────────
    available: list[tuple[str, dict]] = []
    for content_type, filename_tpl in IMPORT_CONTENT_TYPES:
        filename = filename_tpl.replace("{lang}", lang)
        path = f"curricula/{oob_curriculum_id}/{unit_id}/{filename}"
        try:
            body = await storage.read_json(path)
            available.append((content_type, body))
        except FileNotFoundError:
            pass

    if not available:
        raise HTTPException(
            status_code=404,
            detail=f"No content found for unit {unit_id!r} lang={lang!r}",
        )

    # 4. Insert override rows (skip already-imported types) ────────────────────
    bundle_id = str(_uuid.uuid4())
    overrides: list[OverrideItem] = []

    for content_type, body in available:
        # Check if any version already exists (idempotent guard)
        existing_row = await conn.fetchrow(
            "SELECT override_id, review_status, version_number, "
            "bundle_id, edited_at "
            "FROM unit_content_overrides "
            "WHERE curriculum_id = $1 AND unit_id = $2 "
            "  AND lang = $3 AND content_type = $4 "
            "ORDER BY version_number DESC LIMIT 1",
            forked_curriculum_id,
            unit_id,
            lang,
            content_type,
        )
        if existing_row:
            overrides.append(
                OverrideItem(
                    override_id=str(existing_row["override_id"]),
                    school_id=school_id,
                    curriculum_id=forked_curriculum_id,
                    unit_id=unit_id,
                    lang=lang,
                    content_type=content_type,
                    bundle_id=(
                        str(existing_row["bundle_id"]) if existing_row["bundle_id"] else None
                    ),
                    content_source="imported",
                    review_status=existing_row["review_status"],
                    version_number=existing_row["version_number"],
                    edited_at=existing_row["edited_at"].isoformat(),
                    skipped=True,
                )
            )
            continue

        row_bundle_id = bundle_id if content_type in TUTORIAL_BUNDLE_TYPES else None
        new_row = await conn.fetchrow(
            """
            INSERT INTO unit_content_overrides
                (school_id, curriculum_id, unit_id, lang, content_type,
                 bundle_id, content_source, source_override_id, body,
                 last_edited_by, review_status, version_number)
            VALUES ($1, $2, $3, $4, $5,
                    $6, 'imported', NULL, $7,
                    $8, 'draft', 1)
            RETURNING override_id, review_status, version_number,
                      bundle_id, edited_at
            """,
            school_id,
            forked_curriculum_id,
            unit_id,
            lang,
            content_type,
            row_bundle_id,
            body,
            teacher_id,
        )
        overrides.append(
            OverrideItem(
                override_id=str(new_row["override_id"]),
                school_id=school_id,
                curriculum_id=forked_curriculum_id,
                unit_id=unit_id,
                lang=lang,
                content_type=content_type,
                bundle_id=(str(new_row["bundle_id"]) if new_row["bundle_id"] else None),
                content_source="imported",
                review_status=new_row["review_status"],
                version_number=new_row["version_number"],
                edited_at=new_row["edited_at"].isoformat(),
                skipped=False,
            )
        )

    log.info(
        "unit_content_imported",
        school_id=school_id,
        unit_id=unit_id,
        lang=lang,
        created=sum(1 for o in overrides if not o.skipped),
        skipped=sum(1 for o in overrides if o.skipped),
    )
    return {
        "forked_curriculum_id": forked_curriculum_id,
        "fork_created": fork_created,
        "grade_repointed": grade_repointed,
        "overrides": overrides,
    }
