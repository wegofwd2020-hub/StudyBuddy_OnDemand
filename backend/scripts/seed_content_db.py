#!/usr/bin/env python3
"""
backend/scripts/seed_content_db.py

Syncs the curricula and curriculum_units DB rows for every curriculum that
already has generated content in the content store.

Run this whenever content has been built via build_grade.py but the matching
DB rows are missing (e.g. the pipeline ran without a DB connection, or the
container was rebuilt).

Idempotent — uses ON CONFLICT DO UPDATE.  Safe to re-run at any time.

Usage:
    docker compose exec api python scripts/seed_content_db.py
    docker compose exec api python scripts/seed_content_db.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
).replace("@pgbouncer:", "@db:")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)

# ── Map: curriculum_id → (data filename, grade, display name) ─────────────────
# Only curricula that have been built (content files exist in content store).
# Add a new entry here whenever a new stream/grade is built.
CURRICULA: list[tuple[str, str, int, str]] = [
    # (curriculum_id,           data_file,               grade, display_name)
    ("default-2026-g8",          "grade8_stem.json",        8,  "Grade 8 STEM 2026"),
    ("default-2026-g10",         "grade10_stem.json",       10, "Grade 10 STEM 2026"),
    ("default-2026-g11",         "grade11_stem.json",       11, "Grade 11 STEM 2026"),
    ("default-2026-g11-commerce","grade11_commerce.json",   11, "Grade 11 Commerce 2026"),
    ("default-2026-g11-science", "grade11_science.json",    11, "Grade 11 Science 2026"),
    ("default-2026-g12-commerce","grade12_commerce.json",   12, "Grade 12 Commerce 2026"),
    ("default-2026-g12-science", "grade12_science.json",    12, "Grade 12 Science 2026"),
]


def _load_units(data_file: str) -> list[dict]:
    path = os.path.join(DATA_DIR, data_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    units = []
    seq = 0
    for subject_block in data.get("subjects", []):
        subject = subject_block.get("name", "Unknown")
        for unit in subject_block.get("units", []):
            seq += 1
            desc = unit.get("description", "")
            units.append({
                "unit_id":       unit["unit_id"],
                "subject":       subject,
                "unit_name":     unit.get("title", unit["unit_id"]),
                "objectives":    [desc] if desc else ["To be defined."],
                "has_lab":       bool(unit.get("has_lab", False)),
                "lab_description": unit.get("lab_description") or None,
                "sequence":      seq,
            })
    return units


async def _upsert_curriculum(
    conn: asyncpg.Connection,
    curriculum_id: str,
    grade: int,
    name: str,
    units: list[dict],
    dry_run: bool,
) -> int:
    if dry_run:
        print(f"  [dry-run] would upsert {curriculum_id}  ({len(units)} units)")
        return len(units)

    await conn.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, name, source_type, status)
        VALUES ($1, $2, 2026, $3, 'default', 'active')
        ON CONFLICT (curriculum_id) DO UPDATE
            SET name = EXCLUDED.name, status = 'active'
        """,
        curriculum_id, grade, name,
    )

    for u in units:
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, unit_name, objectives,
                 has_lab, lab_description, sequence)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (unit_id, curriculum_id) DO UPDATE
                SET unit_name        = EXCLUDED.unit_name,
                    objectives       = EXCLUDED.objectives,
                    has_lab          = EXCLUDED.has_lab,
                    lab_description  = EXCLUDED.lab_description,
                    sequence         = EXCLUDED.sequence
            """,
            u["unit_id"], curriculum_id, u["subject"], u["unit_name"],
            u["objectives"], u["has_lab"], u["lab_description"], u["sequence"],
        )
    return len(units)


async def run(dry_run: bool) -> None:
    conn = await asyncpg.connect(DB_URL)
    # Epic 10 L-1: pipeline/admin scripts must bypass RLS for platform-owned rows.
    await conn.execute("SET app.current_school_id = 'bypass'")

    try:
        total_units = 0
        for curriculum_id, data_file, grade, name in CURRICULA:
            units = _load_units(data_file)
            n = await _upsert_curriculum(conn, curriculum_id, grade, name, units, dry_run)
            total_units += n
            tag = "[dry-run]" if dry_run else "upserted"
            print(f"  {tag}  {curriculum_id:<35}  {n:>3} units  ({name})")
    finally:
        await conn.close()

    print()
    print(f"{'[dry-run] ' if dry_run else ''}Done — {len(CURRICULA)} curricula, {total_units} units total.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync content-store curricula into DB.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run))


if __name__ == "__main__":
    main()
