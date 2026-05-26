#!/usr/bin/env python3
"""
backend/scripts/export_book.py

Export a *published* authored curriculum (Curriculum Authoring Studio) to a
StudyBuddy Q ``Book`` JSON file. Phase 1 of the content migration documented in
StudyBuddy_SelfLearner `docs/CONTENT_MIGRATION_CONTEXT_ENGINEERING.md`.

The transform logic lives in ``src/admin/book_export.py`` (pure, unit-tested);
this is the thin asyncpg shell that reads the authoring tables and writes the
file.

Usage (operator-run, from backend/ or inside the api container):
    python scripts/export_book.py --project-id <uuid> --out book.json
    # find the project id by title first:
    python scripts/export_book.py --list

Notes:
- Reads the DB (authoring_projects + active topic versions + curriculum_units),
  not the content store — the bodies are the same, and the DB also carries the
  TOC + authoritative unit order in one place.
- Sets app.current_school_id='bypass' before querying platform-owned curricula
  (pitfall #28).
- "Ready" gate: the project should be published (status='published'); a warning
  is printed if it is not, but the export still runs against accepted versions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

_here = Path(__file__).parent.parent
load_dotenv(_here / ".env")
sys.path.insert(0, str(_here))

from src.admin.book_export import BookExportError, assemble_book  # noqa: E402

DATABASE_URL = os.environ["DATABASE_URL"]


def _as_dict(value) -> dict | None:
    """asyncpg returns JSONB as str or dict depending on codec; normalise."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


async def _list_projects(conn: asyncpg.Connection) -> None:
    rows = await conn.fetch(
        "SELECT project_id, title, status, curriculum_id "
        "FROM authoring_projects ORDER BY created_at DESC"
    )
    if not rows:
        print("(no authoring projects found)")
        return
    for r in rows:
        print(f"{r['project_id']}  [{r['status']:>10}]  {r['title']}")


async def _export(conn: asyncpg.Connection, project_id: str, lang: str) -> tuple[dict, list[str]]:
    proj = await conn.fetchrow(
        "SELECT project_id, title, grade, structured_toc, status, curriculum_id "
        "FROM authoring_projects WHERE project_id = $1",
        project_id,
    )
    if proj is None:
        raise BookExportError(f"no authoring project with id {project_id!r}")
    if not proj["curriculum_id"]:
        raise BookExportError("project has not been materialized (no curriculum_id)")
    if proj["status"] != "published":
        print(
            f"[export_book] WARNING: project status is {proj['status']!r}, not 'published' — "
            "exporting accepted versions anyway.",
            file=sys.stderr,
        )

    unit_rows = await conn.fetch(
        "SELECT unit_id, title FROM curriculum_units WHERE curriculum_id = $1 ORDER BY sort_order",
        proj["curriculum_id"],
    )
    version_rows = await conn.fetch(
        """
        SELECT tv.unit_id, tv.content_type, tv.lang, tv.body
          FROM authoring_active_versions av
          JOIN authoring_topic_versions tv ON tv.topic_version_id = av.topic_version_id
         WHERE av.project_id = $1 AND tv.review_status = 'accepted'
        """,
        project_id,
    )

    project = {
        "project_id": str(proj["project_id"]),
        "title": proj["title"],
        "grade": proj["grade"],
        "structured_toc": _as_dict(proj["structured_toc"]),
    }
    units = [{"unit_id": r["unit_id"], "title": r["title"]} for r in unit_rows]
    versions = [
        {
            "unit_id": r["unit_id"],
            "content_type": r["content_type"],
            "lang": r["lang"],
            "body": _as_dict(r["body"]),
        }
        for r in version_rows
    ]
    return assemble_book(project, units, versions, lang=lang)


async def _run(args: argparse.Namespace) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("SET app.current_school_id = 'bypass'")
        if args.list:
            await _list_projects(conn)
            return
        book, warnings = await _export(conn, args.project_id, args.lang)
    finally:
        await conn.close()

    for w in warnings:
        print(f"[export_book] WARNING: {w}", file=sys.stderr)

    out = Path(args.out)
    out.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
    topic_count = len(book["content"])
    print(
        f"[export_book] wrote {out} — '{book['title']}' "
        f"({topic_count} topic(s) with content, {len(warnings)} warning(s))"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a published authored curriculum to a StudyBuddy Q Book JSON."
    )
    parser.add_argument("--list", action="store_true", help="List authoring projects and exit")
    parser.add_argument("--project-id", help="Authoring project id to export")
    parser.add_argument("--out", default="book.json", help="Output JSON path (default: book.json)")
    parser.add_argument("--lang", default="en", help="Language to export (default: en)")
    args = parser.parse_args()

    if not args.list and not args.project_id:
        parser.error("--project-id is required (or use --list to find one)")

    asyncio.run(_run(args))


if __name__ == "__main__":
    try:
        main()
    except KeyError as exc:
        print(f"[export_book] Missing env var: {exc}", file=sys.stderr)
        sys.exit(1)
    except BookExportError as exc:
        print(f"[export_book] {exc}", file=sys.stderr)
        sys.exit(1)
