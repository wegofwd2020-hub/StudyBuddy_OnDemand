"""
Pre-import the first 2 units of each Grade 11 Science subject into the
MilfordWaterford demo school's library fork.

Mirrors the logic of POST /schools/{id}/library/{adoption_id}/units/{unit_id}/import
but skips HTTP auth so it can run as a one-shot setup task. Idempotent —
re-running for already-imported (unit_id, content_type) pairs is a no-op.
"""
import asyncio, json, sys, uuid
from pathlib import Path

sys.path.insert(0, "/app")
import asyncpg
from config import settings


SCHOOL_CONTACT = "admin@milfordwaterford.edu"
OOB_CURR = "default-2026-g11-science"
LANG = "en"

# Curated demo set — 2 units per subject. Controlled-flow demo: teacher
# sees these as already-imported, can manually import the rest.
DEMO_UNITS = [
    ("Biology",     ["G11-BIO-001",  "G11-BIO-002"]),
    ("Chemistry",   ["G11-CHEM-001", "G11-CHEM-002"]),
    ("Mathematics", ["G11-MATH-001", "G11-MATH-002"]),
    ("Physics",     ["G11-PHYS-001", "G11-PHYS-002"]),
]

CONTENT_TYPES = [
    ("lesson",     "lesson_{lang}.json"),
    ("tutorial",   "tutorial_{lang}.json"),
    ("quiz_set_1", "quiz_set_1_{lang}.json"),
    ("quiz_set_2", "quiz_set_2_{lang}.json"),
    ("quiz_set_3", "quiz_set_3_{lang}.json"),
    ("experiment", "experiment_{lang}.json"),
]
TUTORIAL_BUNDLE_TYPES = {"tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3"}


async def main():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

        school_id = await conn.fetchval(
            "SELECT school_id FROM schools WHERE contact_email = $1", SCHOOL_CONTACT
        )
        if not school_id:
            print(f"No school for {SCHOOL_CONTACT}")
            return

        adoption = await conn.fetchrow(
            """
            SELECT adoption_id, forked_curriculum_id, c.name, c.grade, c.year
            FROM school_adopted_curricula sac
            JOIN curricula c ON c.curriculum_id = sac.curriculum_id
            WHERE sac.school_id = $1 AND sac.curriculum_id = $2
            """,
            school_id, OOB_CURR,
        )
        if not adoption:
            print(f"No adoption for {OOB_CURR}")
            return

        fork_id = adoption["forked_curriculum_id"]

        # Pick a teacher for last_edited_by / assigned_by. Falls back to NULL.
        teacher_id = await conn.fetchval(
            "SELECT teacher_id FROM teachers WHERE school_id = $1 ORDER BY created_at LIMIT 1",
            school_id,
        )

        async with conn.transaction():
            # Lazy fork creation (matches the HTTP endpoint).
            if fork_id is None:
                fork_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO curricula
                        (curriculum_id, name, grade, year, is_default,
                         owner_type, owner_id, school_id, source_curriculum_id)
                    VALUES ($1, $2, $3, $4, FALSE, 'school', $5, $5, $6)
                    """,
                    fork_id, adoption["name"], adoption["grade"], adoption["year"],
                    school_id, OOB_CURR,
                )
                await conn.execute(
                    "UPDATE school_adopted_curricula SET forked_curriculum_id = $1 WHERE adoption_id = $2",
                    fork_id, adoption["adoption_id"],
                )
                if adoption["grade"] is not None:
                    await conn.execute(
                        """
                        INSERT INTO grade_curriculum_assignments
                            (school_id, grade, curriculum_id, assigned_by)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (school_id, grade) DO UPDATE
                            SET curriculum_id = EXCLUDED.curriculum_id,
                                assigned_by  = EXCLUDED.assigned_by
                        """,
                        school_id, adoption["grade"], fork_id, teacher_id,
                    )
                print(f"fork created: {fork_id}")
            else:
                print(f"fork already exists: {fork_id}")

            created = 0
            skipped = 0
            for subject, unit_ids in DEMO_UNITS:
                for unit_id in unit_ids:
                    bundle_id = str(uuid.uuid4())   # one bundle per unit
                    for content_type, filename_tpl in CONTENT_TYPES:
                        filename = filename_tpl.replace("{lang}", LANG)
                        path = Path(f"/data/content/curricula/{OOB_CURR}/{unit_id}/{filename}")
                        if not path.exists():
                            continue

                        # Idempotency: skip if any version exists for this (unit, content_type).
                        existing = await conn.fetchval(
                            """
                            SELECT 1 FROM unit_content_overrides
                            WHERE curriculum_id = $1 AND unit_id = $2
                              AND lang = $3 AND content_type = $4
                            LIMIT 1
                            """,
                            fork_id, unit_id, LANG, content_type,
                        )
                        if existing:
                            skipped += 1
                            continue

                        body = json.loads(path.read_text())
                        row_bundle_id = bundle_id if content_type in TUTORIAL_BUNDLE_TYPES else None
                        await conn.execute(
                            """
                            INSERT INTO unit_content_overrides
                                (school_id, curriculum_id, unit_id, lang, content_type,
                                 bundle_id, content_source, source_override_id, body,
                                 last_edited_by, review_status, version_number)
                            VALUES ($1, $2, $3, $4, $5, $6, 'imported', NULL, $7, $8, 'draft', 1)
                            """,
                            school_id, fork_id, unit_id, LANG, content_type,
                            row_bundle_id, json.dumps(body), teacher_id,
                        )
                        created += 1
                    print(f"  {subject:12s} {unit_id}  imported")

            print(f"\nDONE  created={created} skipped={skipped}")

            # Verify
            count = await conn.fetchval(
                "SELECT count(*) FROM unit_content_overrides WHERE curriculum_id = $1",
                fork_id,
            )
            print(f"Total overrides for fork {fork_id}: {count}")
    finally:
        await conn.close()


asyncio.run(main())
