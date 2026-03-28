"""
backend/scripts/seed_dev_content.py

Seeds placeholder lesson/quiz/tutorial content for the default Grade 8
curriculum so the student portal is fully testable without running the pipeline.

What this script does:
  1. Inserts a `curricula` row for default-2026-g8
  2. Inserts `curriculum_units` rows for all Grade 8 units
  3. Inserts `content_subject_versions` rows (status=published) for each subject
  4. Writes placeholder lesson_en.json, quiz_set_1_en.json, tutorial_en.json,
     and meta.json into the content store for every unit

Usage (inside the api container):
    python scripts/seed_dev_content.py

Or from the host:
    docker compose exec api python scripts/seed_dev_content.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import asyncpg

# ── Config ────────────────────────────────────────────────────────────────────

# Connect directly to PostgreSQL, not PgBouncer.
# PgBouncer in transaction-pooling mode drops asyncpg prepared statements silently.
_raw_url = os.environ.get("DATABASE_URL", "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy")
DATABASE_URL = _raw_url.replace("@pgbouncer:", "@db:")
CONTENT_STORE_PATH = os.environ.get("CONTENT_STORE_PATH", "/data/content")

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
)

CURRICULUM_ID = "default-2026-g8"
GRADE = 8
YEAR = 2026
NOW = datetime.now(timezone.utc).isoformat()
MODEL = "dev-placeholder"
CONTENT_VERSION = 1


# ── Placeholder content builders ──────────────────────────────────────────────

def make_lesson(unit_id: str, title: str, subject: str, description: str) -> dict:
    return {
        "unit_id": unit_id,
        "title": title,
        "grade": GRADE,
        "subject": subject,
        "lang": "en",
        "sections": [
            {
                "heading": "Overview",
                "body": description or f"This lesson covers {title}.",
            },
            {
                "heading": "Core Concepts",
                "body": (
                    f"In this section we explore the key ideas behind {title}. "
                    "Work through the examples carefully and take notes on the main principles."
                ),
            },
            {
                "heading": "Worked Examples",
                "body": (
                    f"Let's look at step-by-step examples that apply the concepts from {title}. "
                    "Pay attention to the method used at each step."
                ),
            },
            {
                "heading": "Practice",
                "body": (
                    "Try the quiz for this unit to test your understanding. "
                    "Review any sections you found difficult before moving on."
                ),
            },
        ],
        "key_points": [
            f"Understand the definition and scope of {title}",
            f"Identify the key techniques used in {title}",
            f"Apply {title} concepts to solve problems",
        ],
        "has_audio": False,
        "generated_at": NOW,
        "model": MODEL,
        "content_version": CONTENT_VERSION,
    }


def make_quiz(unit_id: str, title: str) -> dict:
    def q(n: int) -> dict:
        return {
            "question_id": f"{unit_id}-Q{n}",
            "question_text": f"Sample question {n} about {title}?",
            "question_type": "multiple_choice",
            "options": [
                {"option_id": "A", "text": "Option A"},
                {"option_id": "B", "text": "Option B"},
                {"option_id": "C", "text": "Option C"},
                {"option_id": "D", "text": "Option D"},
            ],
            "correct_option": "A",
            "explanation": f"Option A is correct because it best describes {title}.",
            "difficulty": "medium",
        }

    return {
        "unit_id": unit_id,
        "set_number": 1,
        "language": "en",
        "questions": [q(i) for i in range(1, 6)],
        "total_questions": 5,
        "estimated_duration_minutes": 10,
        "passing_score": 3,
        "generated_at": NOW,
        "model": MODEL,
        "content_version": CONTENT_VERSION,
    }


def make_tutorial(unit_id: str, title: str) -> dict:
    return {
        "unit_id": unit_id,
        "language": "en",
        "title": f"Tutorial: {title}",
        "sections": [
            {
                "section_id": f"{unit_id}-S1",
                "title": "Introduction",
                "content": f"This tutorial covers the basics of {title}.",
                "examples": [f"Example 1 for {title}", f"Example 2 for {title}"],
                "practice_question": f"Try solving a basic problem involving {title}.",
            }
        ],
        "common_mistakes": [
            f"Confusing key terms in {title}",
            "Skipping steps when solving problems",
        ],
        "generated_at": NOW,
        "model": MODEL,
        "content_version": CONTENT_VERSION,
    }


def make_meta(langs: list[str] = None) -> dict:
    return {
        "generated_at": NOW,
        "model": MODEL,
        "content_version": CONTENT_VERSION,
        "langs_built": langs or ["en"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    # Load grade 8 JSON
    grade_path = os.path.join(DATA_DIR, "grade8_stem.json")
    if not os.path.exists(grade_path):
        print(f"ERROR: {grade_path} not found. Is the data/ directory accessible?")
        sys.exit(1)

    with open(grade_path, "r") as f:
        grade_data = json.load(f)

    subjects = grade_data["subjects"]  # [{subject_id, name, units: [...]}]

    # Connect to DB
    conn = await asyncpg.connect(DATABASE_URL)
    print(f"Connected to DB.")

    try:
        # 1. Upsert curricula row
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            CURRICULUM_ID, GRADE, YEAR, "Default Grade 8 Curriculum 2026",
        )
        print(f"  curricula: {CURRICULUM_ID}")

        # 2. Upsert curriculum_units
        for subj in subjects:
            subject_name = subj["name"]
            for idx, unit in enumerate(subj["units"]):
                await conn.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, unit_name, description, has_lab, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    unit["unit_id"],
                    CURRICULUM_ID,
                    subject_name,
                    unit["title"],
                    unit["title"],          # unit_name mirrors title for default curricula
                    unit.get("description", ""),
                    unit.get("has_lab", False),
                    idx,
                )
            print(f"  curriculum_units: {subject_name} ({len(subj['units'])} units)")

        # 3. Upsert content_subject_versions (published)
        for subj in subjects:
            subject_name = subj["name"]
            existing = await conn.fetchrow(
                """
                SELECT version_id FROM content_subject_versions
                WHERE curriculum_id = $1 AND subject = $2 AND status = 'published'
                """,
                CURRICULUM_ID, subject_name,
            )
            if not existing:
                await conn.execute(
                    """
                    INSERT INTO content_subject_versions
                        (version_id, curriculum_id, subject, version_number, status, published_at)
                    VALUES ($1, $2, $3, 1, 'published', NOW())
                    ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE
                        SET status = 'published', published_at = NOW()
                    """,
                    uuid.uuid4(),
                    CURRICULUM_ID,
                    subject_name,
                )
            print(f"  content_subject_versions: {subject_name} → published")

    finally:
        await conn.close()

    # 4. Write content files to the content store
    for subj in subjects:
        subject_name = subj["name"]
        for unit in subj["units"]:
            unit_id = unit["unit_id"]
            title = unit["title"]
            unit_dir = os.path.join(
                CONTENT_STORE_PATH, "curricula", CURRICULUM_ID, unit_id
            )
            os.makedirs(unit_dir, exist_ok=True)

            # lesson_en.json
            lesson_path = os.path.join(unit_dir, "lesson_en.json")
            if not os.path.exists(lesson_path):
                with open(lesson_path, "w") as f:
                    json.dump(make_lesson(unit_id, title, subject_name, unit.get("description", "")), f, indent=2)

            # quiz_set_1/2/3_en.json — all 3 sets needed for round-robin rotation
            for set_num in (1, 2, 3):
                quiz_path = os.path.join(unit_dir, f"quiz_set_{set_num}_en.json")
                if not os.path.exists(quiz_path):
                    quiz_data = make_quiz(unit_id, title)
                    quiz_data["set_number"] = set_num
                    with open(quiz_path, "w") as f:
                        json.dump(quiz_data, f, indent=2)

            # tutorial_en.json
            tutorial_path = os.path.join(unit_dir, "tutorial_en.json")
            if not os.path.exists(tutorial_path):
                with open(tutorial_path, "w") as f:
                    json.dump(make_tutorial(unit_id, title), f, indent=2)

            # meta.json
            meta_path = os.path.join(unit_dir, "meta.json")
            if not os.path.exists(meta_path):
                with open(meta_path, "w") as f:
                    json.dump(make_meta(), f, indent=2)

        print(f"  content files: {subject_name} ({len(subj['units'])} units) → {unit_dir.rsplit('/', 2)[0]}/...")

    print("\nDone. Grade 8 dev content is ready.")
    print(f"  DB:      {CURRICULUM_ID} — curricula + units + subject_versions")
    print(f"  Store:   {CONTENT_STORE_PATH}/curricula/{CURRICULUM_ID}/")


if __name__ == "__main__":
    asyncio.run(main())
