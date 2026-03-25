"""
pipeline/seed_default.py

Seeds the curricula and curriculum_units tables with default content for
grades 5–12 from data/grade{N}_stem.json files.

Usage:
  python pipeline/seed_default.py --year 2026

Idempotent — uses ON CONFLICT DO NOTHING for all inserts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

# Allow running from repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

log = logging.getLogger("pipeline.seed_default")


async def seed_grade(conn: object, grade: int, year: int) -> None:
    """Seed one grade's curriculum and units."""
    data_path = os.path.join(_REPO_ROOT, "data", f"grade{grade}_stem.json")
    if not os.path.exists(data_path):
        log.warning("seed_skip: %s not found", data_path)
        return

    with open(data_path, "r", encoding="utf-8") as f:
        grade_data = json.load(f)

    curriculum_id = f"default-{year}-g{grade}"

    # Upsert curricula row
    await conn.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
        VALUES ($1, $2, $3, $4, true)
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        curriculum_id,
        grade,
        year,
        f"Default Grade {grade} STEM Curriculum ({year})",
    )
    log.info("seeded curriculum: %s", curriculum_id)

    # Upsert units
    for subject in grade_data.get("subjects", []):
        subject_id = subject.get("subject_id", "unknown")
        for sort_order, unit in enumerate(subject.get("units", [])):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, description, has_lab, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                """,
                unit["unit_id"],
                curriculum_id,
                subject_id,
                unit.get("title", unit["unit_id"]),
                unit.get("description", ""),
                unit.get("has_lab", False),
                sort_order,
            )
        log.info(
            "seeded %d units for %s/%s",
            len(subject.get("units", [])),
            curriculum_id,
            subject_id,
        )


async def seed_all(year: int) -> None:
    """Seed grades 5–12."""
    from pipeline.config import settings as config

    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set to seed the database")

    import asyncpg  # type: ignore

    conn = await asyncpg.connect(config.DATABASE_URL)
    try:
        for grade in range(5, 13):
            await seed_grade(conn, grade, year)
        log.info("seed_complete year=%d", year)
    finally:
        await conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Seed default curricula (grades 5–12) into DB.")
    parser.add_argument("--year", type=int, default=2026, help="Curriculum year (default: 2026)")
    args = parser.parse_args()

    asyncio.run(seed_all(year=args.year))


if __name__ == "__main__":
    main()
