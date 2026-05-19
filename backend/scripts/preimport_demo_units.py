"""
backend/scripts/preimport_demo_units.py

Pre-import + auto-approve + publish ALL Grade 11 Science units into the
MilfordWaterford demo school's library fork, so a fresh demo signup lands
on a fully-populated Content Library — every unit accessible, no
import/approve clicks required to use the demo.

Companion to seed_demo_milfordwaterford.py — the seed creates the school +
teachers + students + classrooms; this script populates:
  - the school's forked Grade 11 Science curriculum
  - one unit_content_overrides row per (unit × content_type) discovered in
    the Content Store, with review_status='approved' (skips the draft →
    pending_review → approved review workflow, since this is a demo)
  - one unit_content_active_versions row per override, making the content
    "published" (visible in Content Library + student-facing endpoints)

Run order on a freshly-provisioned demo VPS:
    python scripts/seed_demo_milfordwaterford.py
    python scripts/preimport_demo_units.py

Mirrors the SQL of
  POST /schools/{id}/library/{adoption_id}/units/{unit_id}/import
  POST /schools/{id}/content/{curriculum_id}/units/{unit_id}/approve (publish=True)
but skips HTTP auth so it can run as a one-shot setup task. Idempotent —
re-running upgrades existing draft rows in-place and is safe to re-run
after content store changes.

Requires the OOB curriculum content to be present in the Content Store
at /data/content/curricula/default-2026-g11-science/<unit_id>/<file>.json,
rsync'd by scripts/demo/sync-content.sh.
"""
import asyncio, json, sys, uuid
from pathlib import Path

sys.path.insert(0, "/app")
import asyncpg
from config import settings


SCHOOL_CONTACT = "admin@milfordwaterford.edu"
OOB_CURR = "default-2026-g11-science"
LANG = "en"

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

        # Pick a teacher for last_edited_by / assigned_by / activated_by.
        # Falls back to NULL (the FK is ON DELETE SET NULL).
        teacher_id = await conn.fetchval(
            "SELECT teacher_id FROM teachers WHERE school_id = $1 ORDER BY created_at LIMIT 1",
            school_id,
        )

        # Discover all unit_ids for the OOB curriculum.
        units = await conn.fetch(
            """
            SELECT unit_id, subject
            FROM curriculum_units
            WHERE curriculum_id = $1
            ORDER BY subject, unit_id
            """,
            OOB_CURR,
        )
        print(f"Discovered {len(units)} units across {len({u['subject'] for u in units})} subjects")

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

            inserts = 0
            approves = 0
            publishes = 0
            for u in units:
                unit_id = u["unit_id"]
                bundle_id = str(uuid.uuid4())   # one bundle per unit for the tutorial-bundle types
                for content_type, filename_tpl in CONTENT_TYPES:
                    filename = filename_tpl.replace("{lang}", LANG)
                    path = Path(f"/data/content/curricula/{OOB_CURR}/{unit_id}/{filename}")
                    if not path.exists():
                        continue

                    body = json.loads(path.read_text())

                    existing = await conn.fetchrow(
                        """
                        SELECT override_id, review_status
                        FROM unit_content_overrides
                        WHERE curriculum_id = $1 AND unit_id = $2
                          AND lang = $3 AND content_type = $4
                        ORDER BY version_number DESC LIMIT 1
                        """,
                        fork_id, unit_id, LANG, content_type,
                    )

                    if existing is None:
                        # No row yet — insert directly as approved.
                        row_bundle_id = bundle_id if content_type in TUTORIAL_BUNDLE_TYPES else None
                        override_id = await conn.fetchval(
                            """
                            INSERT INTO unit_content_overrides
                                (school_id, curriculum_id, unit_id, lang, content_type,
                                 bundle_id, content_source, source_override_id, body,
                                 last_edited_by, review_status, version_number)
                            VALUES ($1, $2, $3, $4, $5, $6, 'imported', NULL, $7, $8, 'approved', 1)
                            RETURNING override_id
                            """,
                            school_id, fork_id, unit_id, LANG, content_type,
                            row_bundle_id, json.dumps(body), teacher_id,
                        )
                        inserts += 1
                    else:
                        override_id = existing["override_id"]
                        # Promote any pre-existing draft/pending_review rows to approved.
                        if existing["review_status"] != "approved":
                            await conn.execute(
                                "UPDATE unit_content_overrides SET review_status='approved' WHERE override_id=$1",
                                override_id,
                            )
                            approves += 1

                    # Upsert the active version pointer so the override is "published".
                    await conn.execute(
                        """
                        INSERT INTO unit_content_active_versions
                            (school_id, curriculum_id, unit_id, lang,
                             content_type, override_id, activated_by)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (school_id, curriculum_id, unit_id, lang, content_type)
                        DO UPDATE SET override_id   = EXCLUDED.override_id,
                                      activated_by  = EXCLUDED.activated_by,
                                      activated_at  = now()
                        """,
                        school_id, fork_id, unit_id, LANG, content_type,
                        override_id, teacher_id,
                    )
                    publishes += 1

                print(f"  {u['subject']:12s} {unit_id}")

            print(f"\nDONE  inserts={inserts}  approves={approves}  publishes={publishes}")

            # Verify
            counts = await conn.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM unit_content_overrides
                       WHERE curriculum_id = $1) AS overrides_total,
                    (SELECT count(*) FROM unit_content_overrides
                       WHERE curriculum_id = $1 AND review_status = 'approved') AS approved,
                    (SELECT count(*) FROM unit_content_active_versions
                       WHERE curriculum_id = $1) AS active_versions
                """,
                fork_id,
            )
            print(f"Final  overrides={counts['overrides_total']}  approved={counts['approved']}  active={counts['active_versions']}")
    finally:
        await conn.close()


asyncio.run(main())
