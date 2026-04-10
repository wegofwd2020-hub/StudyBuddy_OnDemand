"""
Recover missing curriculum DB records from on-disk content store.

Usage (inside API container):
    python /app/scripts/recover_curriculum.py --grade 12 [--year 2026] [--dry-run]
    python /app/scripts/recover_curriculum.py --grade 10 [--year 2026] [--dry-run]

What it does:
  1. Reads /app/data/grade{N}_stem.json for the curriculum/unit metadata
  2. Scans the content store for existing meta.json files per unit
  3. INSERTs into curricula, curriculum_units, content_subject_versions
     (all ON CONFLICT DO NOTHING — safe to re-run)
  4. For content_subject_versions: only creates a row for subjects where
     ALL units in that subject have built content on disk
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

CONTENT_STORE = os.environ.get("CONTENT_STORE_PATH", "/data/content")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@pgbouncer:5432/studybuddy",
)
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


def pg_dsn(url: str) -> str:
    """Convert postgresql:// URL to psycopg2 dsn."""
    return url.replace("postgresql://", "postgres://", 1)


def load_grade_json(grade: int) -> dict:
    path = os.path.join(DATA_DIR, f"grade{grade}_stem.json")
    if not os.path.exists(path):
        sys.exit(f"ERROR: Grade JSON not found at {path}")
    with open(path) as f:
        return json.load(f)


def read_meta(curriculum_id: str, unit_id: str) -> dict | None:
    meta_path = os.path.join(CONTENT_STORE, "curricula", curriculum_id, unit_id, "meta.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path) as f:
            return json.load(f)
    except Exception:
        return None


def run(grade: int, year: int, dry_run: bool) -> None:
    curriculum_id = f"default-{year}-g{grade}"
    grade_data = load_grade_json(grade)
    subjects = grade_data["subjects"]

    print(f"\nRecovering curriculum: {curriculum_id}")
    print(f"  Subjects: {[s['name'] for s in subjects]}")
    print(f"  Dry-run: {dry_run}\n")

    # Collect unit meta from disk
    unit_meta: dict[str, dict | None] = {}
    for subj in subjects:
        for unit in subj["units"]:
            uid = unit["unit_id"]
            unit_meta[uid] = read_meta(curriculum_id, uid)

    built = [uid for uid, m in unit_meta.items() if m is not None]
    missing = [uid for uid, m in unit_meta.items() if m is None]
    print(f"  Units with content on disk: {len(built)}")
    if missing:
        print(f"  Units missing from disk   : {missing}")

    # Determine which subjects are fully built
    fully_built_subjects: list[dict] = []
    for subj in subjects:
        all_built = all(unit_meta.get(u["unit_id"]) is not None for u in subj["units"])
        if all_built:
            fully_built_subjects.append(subj)
        else:
            built_units = [u["unit_id"] for u in subj["units"] if unit_meta.get(u["unit_id"])]
            print(
                f"  Subject '{subj['name']}' partially built "
                f"({len(built_units)}/{len(subj['units'])} units) — skipping CSV row"
            )

    print(f"\n  Fully-built subjects for review queue: {[s['name'] for s in fully_built_subjects]}")

    if dry_run:
        print("\nDry-run complete — no DB changes made.")
        return

    conn = psycopg2.connect(pg_dsn(DATABASE_URL))
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1 — Insert curricula row
        curriculum_name = f"Grade {grade} STEM Default {year}"
        cur.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type, status)
            VALUES (%s, %s, %s, %s, true, 'default', 'active')
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            (curriculum_id, grade, year, curriculum_name),
        )
        print(f"\n[1] curricula: inserted (or already existed) — {curriculum_id}")

        # 2 — Insert curriculum_units
        inserted_units = 0
        for subj in subjects:
            subj_name = subj["name"]
            for i, unit in enumerate(subj["units"]):
                uid = unit["unit_id"]
                meta = unit_meta.get(uid)
                content_status = "built" if meta is not None else "pending"
                cur.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, description,
                         has_lab, sort_order, unit_name, objectives, sequence, content_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::text[], %s, %s)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    (
                        uid,
                        curriculum_id,
                        subj_name,
                        unit["title"],
                        unit.get("description", ""),
                        unit.get("has_lab", False),
                        i,           # sort_order
                        unit["title"],  # unit_name (NOT NULL)
                        "{}",        # objectives empty array
                        1,           # sequence
                        content_status,
                    ),
                )
                if cur.rowcount:
                    inserted_units += 1
        print(f"[2] curriculum_units: inserted {inserted_units} rows")

        # 3 — Insert content_subject_versions for fully-built subjects
        inserted_csv = 0
        for subj in fully_built_subjects:
            subj_name = subj["name"]
            # Collect alex_warnings_count and generated_at from unit metas
            unit_metas = [unit_meta[u["unit_id"]] for u in subj["units"]]
            total_warnings = sum(m.get("alex_warnings_count", 0) for m in unit_metas if m)
            # Use the earliest generated_at across units as the subject generated_at
            generated_ats = [
                datetime.fromisoformat(m["generated_at"])
                for m in unit_metas
                if m and m.get("generated_at")
            ]
            generated_at = min(generated_ats) if generated_ats else datetime.now(timezone.utc)

            cur.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, subject_name, version_number,
                     status, alex_warnings_count, generated_at)
                VALUES (%s, %s, %s, 1, 'pending', %s, %s)
                ON CONFLICT (curriculum_id, subject, version_number) DO NOTHING
                """,
                (curriculum_id, subj_name, subj_name, total_warnings, generated_at),
            )
            if cur.rowcount:
                inserted_csv += 1
                print(
                    f"     CSV: {curriculum_id}/{subj_name} — "
                    f"warnings={total_warnings}, generated={generated_at.isoformat()}"
                )

        print(f"[3] content_subject_versions: inserted {inserted_csv} rows")

        conn.commit()
        print("\nDone — all changes committed.")

    except Exception as exc:
        conn.rollback()
        print(f"\nERROR: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recover curriculum DB records from disk content")
    parser.add_argument("--grade", type=int, required=True, help="Grade number (e.g. 12)")
    parser.add_argument("--year", type=int, default=2026, help="Curriculum year (default: 2026)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without DB changes")
    args = parser.parse_args()
    run(args.grade, args.year, args.dry_run)
