#!/usr/bin/env python3
"""
export_content_bundle.py — package AI-generated lesson content + the DB rows it
depends on into a single tar.gz bundle that can be transferred to another
machine (demo laptop, staging, a colleague's dev box) and imported via
import_content_bundle.py.

Bundle contents:
    manifest.json                          -- format, timestamps, row counts, filter
    rows/curricula.jsonl                   -- curricula rows (1 per line)
    rows/curriculum_units.jsonl            -- curriculum_units rows
    rows/content_subject_versions.jsonl    -- content_subject_versions rows
    content/curricula/{id}/{unit}/...      -- lesson / quiz / tutorial JSON + MP3

Usage:
    # Export everything
    docker compose exec api python scripts/export_content_bundle.py \\
        --out /data/content/bundle-$(date +%Y%m%d).tar.gz --all

    # Export a single default curriculum
    docker compose exec api python scripts/export_content_bundle.py \\
        --out /data/content/g8-2026.tar.gz --curriculum-id default-2026-g8

    # Export all grade-8 curricula, excluding MP3s (small bundle for demos)
    docker compose exec api python scripts/export_content_bundle.py \\
        --out /data/content/g8-text-only.tar.gz --grade 8 --exclude-audio

Output path note: paths inside the container (/data/content/...) land on the
host at ./content_store_data/ because of the bind-mount in docker-compose.yml.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

BUNDLE_FORMAT_VERSION = "1"

DB_URL = os.getenv(
    "DIRECT_DB_URL",
    os.getenv("DATABASE_URL", "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy"),
)
CONTENT_STORE_PATH = Path(os.getenv("CONTENT_STORE_PATH", "/data/content"))


def _json_default(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, Decimal):
        return str(v)
    raise TypeError(f"not JSON-serialisable: {type(v).__name__}")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=_json_default, ensure_ascii=False) + "\n")


async def _fetch_rows(conn: asyncpg.Connection, query: str, *args: Any) -> list[dict]:
    records = await conn.fetch(query, *args)
    return [dict(r) for r in records]


def _build_curriculum_filter(args: argparse.Namespace) -> tuple[str, list[Any]]:
    if args.all:
        return "TRUE", []
    if args.curriculum_id:
        return "curriculum_id = $1", [args.curriculum_id]
    if args.grade is not None:
        return "grade = $1", [args.grade]
    raise SystemExit("error: one of --all, --curriculum-id, --grade required")


async def _export(args: argparse.Namespace) -> None:
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force:
        raise SystemExit(f"error: {out_path} already exists (pass --force to overwrite)")

    where_clause, where_args = _build_curriculum_filter(args)

    conn = await asyncpg.connect(DB_URL)
    # Bypass RLS — bundles are admin operations.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    try:
        curricula = await _fetch_rows(
            conn, f"SELECT * FROM curricula WHERE {where_clause}", *where_args
        )
        if not curricula:
            raise SystemExit("No curricula matched the filter. Nothing to export.")

        curriculum_ids = [c["curriculum_id"] for c in curricula]

        units = await _fetch_rows(
            conn,
            "SELECT * FROM curriculum_units WHERE curriculum_id = ANY($1::text[]) "
            "ORDER BY curriculum_id, sequence",
            curriculum_ids,
        )

        status_filter = (
            "status IN ('published','approved','ready_for_review')"
            if args.include_drafts
            else "status IN ('published','approved')"
        )
        versions = await _fetch_rows(
            conn,
            f"SELECT * FROM content_subject_versions "
            f"WHERE curriculum_id = ANY($1::text[]) AND {status_filter} "
            f"AND archived_at IS NULL",
            curriculum_ids,
        )
    finally:
        await conn.close()

    print(f"Matched {len(curricula)} curricula / {len(units)} units / {len(versions)} versions")

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)

        _write_jsonl(stage / "rows" / "curricula.jsonl", curricula)
        _write_jsonl(stage / "rows" / "curriculum_units.jsonl", units)
        _write_jsonl(stage / "rows" / "content_subject_versions.jsonl", versions)

        # Copy content files for each included curriculum.
        file_count = 0
        byte_count = 0
        for cid in curriculum_ids:
            src_dir = CONTENT_STORE_PATH / "curricula" / cid
            if not src_dir.exists():
                continue
            dst_dir = stage / "content" / "curricula" / cid
            dst_dir.mkdir(parents=True, exist_ok=True)

            for src in src_dir.rglob("*"):
                if src.is_dir():
                    continue
                if args.exclude_audio and src.suffix.lower() == ".mp3":
                    continue
                rel = src.relative_to(src_dir)
                dst = dst_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                file_count += 1
                byte_count += src.stat().st_size

        manifest = {
            "format_version": BUNDLE_FORMAT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "filter": {
                "all": bool(args.all),
                "curriculum_id": args.curriculum_id,
                "grade": args.grade,
                "include_drafts": bool(args.include_drafts),
                "exclude_audio": bool(args.exclude_audio),
            },
            "counts": {
                "curricula": len(curricula),
                "curriculum_units": len(units),
                "content_subject_versions": len(versions),
                "content_files": file_count,
                "content_bytes": byte_count,
            },
            "curriculum_ids": curriculum_ids,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2))

        with tarfile.open(out_path, "w:gz") as tar:
            for entry in sorted(stage.rglob("*")):
                if entry.is_dir():
                    continue
                tar.add(entry, arcname=str(entry.relative_to(stage)))

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(
        f"Wrote {out_path} — {size_mb:.1f} MB "
        f"({file_count} content files, {len(curricula)} curricula)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="Output path for the bundle (.tar.gz)")
    sel = parser.add_mutually_exclusive_group(required=True)
    sel.add_argument("--all", action="store_true", help="Export every curriculum")
    sel.add_argument("--curriculum-id", help="Export a single curriculum (e.g. default-2026-g8)")
    sel.add_argument("--grade", type=int, help="Export every curriculum for a given grade")
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Include ready_for_review versions (default: approved/published only)",
    )
    parser.add_argument(
        "--exclude-audio",
        action="store_true",
        help="Skip .mp3 files to produce a smaller bundle",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite --out if it exists")
    args = parser.parse_args()

    try:
        asyncio.run(_export(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
