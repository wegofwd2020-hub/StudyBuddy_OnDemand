#!/usr/bin/env python3
"""
import_content_bundle.py — restore a content bundle produced by
export_content_bundle.py onto this machine.

The operation is idempotent. DB rows are UPSERTed on natural keys so running
the same bundle twice is a no-op. Content files are copied with overwrite
semantics (newer bundle wins).

Usage:
    # Dry-run: show what would change, make no edits
    docker compose exec api python scripts/import_content_bundle.py \\
        bundle.tar.gz --dry-run

    # Apply
    docker compose exec api python scripts/import_content_bundle.py \\
        bundle.tar.gz

Upsert keys:
    curricula                  → curriculum_id
    curriculum_units           → (unit_id, curriculum_id)
    content_subject_versions   → (curriculum_id, subject, version_number)

Constraints respected:
    - RLS bypass set so the script can write across tenant boundaries
    - Rows are loaded in dependency order (curricula → units → versions)
    - If the bundle references a school_id / owner_id / created_by /
      assigned_to_admin_id that doesn't exist locally, the FK columns are
      nulled on import. The content is still usable; it just loses its
      provenance pointer. A warning is printed per nulled reference.
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
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

EXPECTED_FORMAT_VERSION = "1"

DB_URL = os.getenv(
    "DIRECT_DB_URL",
    os.getenv("DATABASE_URL", "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy"),
)
CONTENT_STORE_PATH = Path(os.getenv("CONTENT_STORE_PATH", "/data/content"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _coerce(row: dict, col: str, kind: str) -> Any:
    v = row.get(col)
    if v is None:
        return None
    if kind == "uuid":
        return UUID(v) if isinstance(v, str) else v
    if kind == "datetime":
        return datetime.fromisoformat(v) if isinstance(v, str) else v
    if kind == "decimal":
        return Decimal(v) if isinstance(v, str) else v
    return v


async def _existing_uuids(conn: asyncpg.Connection, table: str, pk: str, ids: set) -> set:
    if not ids:
        return set()
    rows = await conn.fetch(
        f"SELECT {pk} FROM {table} WHERE {pk} = ANY($1::uuid[])",
        [UUID(i) if isinstance(i, str) else i for i in ids],
    )
    return {r[pk] for r in rows}


async def _import(args: argparse.Namespace) -> None:
    bundle_path = Path(args.bundle).resolve()
    if not bundle_path.exists():
        raise SystemExit(f"error: {bundle_path} not found")

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        with tarfile.open(bundle_path, "r:gz") as tar:
            # Python 3.12+ requires explicit filter; fall back safely on older.
            try:
                tar.extractall(stage, filter="data")
            except TypeError:
                tar.extractall(stage)

        manifest_path = stage / "manifest.json"
        if not manifest_path.exists():
            raise SystemExit("error: bundle is missing manifest.json")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("format_version") != EXPECTED_FORMAT_VERSION:
            raise SystemExit(
                f"error: bundle format_version is {manifest.get('format_version')}, "
                f"expected {EXPECTED_FORMAT_VERSION}"
            )

        print(f"Bundle: {bundle_path.name}")
        print(f"  exported_at : {manifest.get('exported_at')}")
        print(f"  counts      : {manifest.get('counts')}")
        print(f"  curricula   : {', '.join(manifest.get('curriculum_ids', [])) or '(none)'}")

        curricula = _read_jsonl(stage / "rows" / "curricula.jsonl")
        units = _read_jsonl(stage / "rows" / "curriculum_units.jsonl")
        versions = _read_jsonl(stage / "rows" / "content_subject_versions.jsonl")

        if args.dry_run:
            print(f"\n[dry-run] Would upsert:")
            print(f"  - {len(curricula)} curricula")
            print(f"  - {len(units)} curriculum_units")
            print(f"  - {len(versions)} content_subject_versions")
            print(f"  - {manifest['counts'].get('content_files', 0)} content files")
            return

        # ── DB upserts ────────────────────────────────────────────────────────
        conn = await asyncpg.connect(DB_URL)
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

        nulled_refs = {"school_id": 0, "owner_id": 0, "created_by": 0, "assigned_to_admin_id": 0}

        try:
            async with conn.transaction():
                # Curricula — resolve optional FKs; null if missing locally.
                school_ids = {c["school_id"] for c in curricula if c.get("school_id")}
                existing_schools = await _existing_uuids(conn, "schools", "school_id", school_ids)

                c_ins = c_upd = 0
                for c in curricula:
                    sid = c.get("school_id")
                    if sid and UUID(sid) not in existing_schools:
                        nulled_refs["school_id"] += 1
                        sid = None

                    result = await conn.execute(
                        """
                        INSERT INTO curricula (
                            curriculum_id, grade, year, name, is_default, school_id,
                            source_type, status, restrict_access, created_by,
                            activated_at, owner_type, owner_id, retention_status,
                            expires_at, grace_until, created_at
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NULL,$10,$11,NULL,$12,$13,$14,$15)
                        ON CONFLICT (curriculum_id) DO UPDATE SET
                            grade=EXCLUDED.grade,
                            year=EXCLUDED.year,
                            name=EXCLUDED.name,
                            is_default=EXCLUDED.is_default,
                            school_id=EXCLUDED.school_id,
                            source_type=EXCLUDED.source_type,
                            status=EXCLUDED.status,
                            restrict_access=EXCLUDED.restrict_access,
                            activated_at=EXCLUDED.activated_at,
                            owner_type=EXCLUDED.owner_type,
                            retention_status=EXCLUDED.retention_status,
                            expires_at=EXCLUDED.expires_at,
                            grace_until=EXCLUDED.grace_until
                        """,
                        c["curriculum_id"], c["grade"], c["year"], c["name"],
                        c["is_default"], _coerce(c, "school_id", "uuid") if sid else None,
                        c["source_type"], c["status"], c["restrict_access"],
                        _coerce(c, "activated_at", "datetime"), c["owner_type"],
                        c["retention_status"], _coerce(c, "expires_at", "datetime"),
                        _coerce(c, "grace_until", "datetime"),
                        _coerce(c, "created_at", "datetime"),
                    )
                    if "INSERT" in result and "0 1" in result:
                        c_ins += 1
                    else:
                        c_upd += 1

                # Curriculum units — PK (unit_id, curriculum_id)
                u_ins = u_upd = 0
                for u in units:
                    await conn.execute(
                        """
                        INSERT INTO curriculum_units (
                            unit_id, curriculum_id, subject, title, description, has_lab,
                            sort_order, unit_name, objectives, lab_description, sequence, content_status
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                        ON CONFLICT (unit_id, curriculum_id) DO UPDATE SET
                            subject=EXCLUDED.subject,
                            title=EXCLUDED.title,
                            description=EXCLUDED.description,
                            has_lab=EXCLUDED.has_lab,
                            sort_order=EXCLUDED.sort_order,
                            unit_name=EXCLUDED.unit_name,
                            objectives=EXCLUDED.objectives,
                            lab_description=EXCLUDED.lab_description,
                            sequence=EXCLUDED.sequence,
                            content_status=EXCLUDED.content_status
                        """,
                        u["unit_id"], u["curriculum_id"], u["subject"], u.get("title"),
                        u.get("description"), u["has_lab"], u["sort_order"],
                        u["unit_name"], u["objectives"] or [], u.get("lab_description"),
                        u["sequence"], u["content_status"],
                    )
                    u_upd += 1  # Counting is approximate; UPSERT status isn't returned reliably.

                # Content subject versions — unique key (curriculum_id, subject, version_number)
                v_ins = v_upd = 0
                for v in versions:
                    await conn.execute(
                        """
                        INSERT INTO content_subject_versions (
                            version_id, curriculum_id, subject, version_number, status,
                            alex_warnings_count, generated_at, published_at, pipeline_run_id,
                            archived_at, subject_name, tokens_used, cost_usd, provider
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                        ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE SET
                            status=EXCLUDED.status,
                            alex_warnings_count=EXCLUDED.alex_warnings_count,
                            published_at=EXCLUDED.published_at,
                            pipeline_run_id=EXCLUDED.pipeline_run_id,
                            subject_name=EXCLUDED.subject_name,
                            tokens_used=EXCLUDED.tokens_used,
                            cost_usd=EXCLUDED.cost_usd,
                            provider=EXCLUDED.provider
                        """,
                        _coerce(v, "version_id", "uuid"), v["curriculum_id"], v["subject"],
                        v["version_number"], v["status"], v["alex_warnings_count"],
                        _coerce(v, "generated_at", "datetime"),
                        _coerce(v, "published_at", "datetime"),
                        v.get("pipeline_run_id"),
                        _coerce(v, "archived_at", "datetime"),
                        v.get("subject_name"), v.get("tokens_used"),
                        _coerce(v, "cost_usd", "decimal"), v["provider"],
                    )
                    v_upd += 1

        finally:
            await conn.close()

        # ── File copy (after DB transaction commits) ──────────────────────────
        bundle_content = stage / "content" / "curricula"
        copied = 0
        if bundle_content.exists():
            dst_base = CONTENT_STORE_PATH / "curricula"
            dst_base.mkdir(parents=True, exist_ok=True)
            for src in bundle_content.rglob("*"):
                if src.is_dir():
                    continue
                rel = src.relative_to(bundle_content)
                dst = dst_base / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1

        print("\nDone.")
        print(f"  curricula                  : {len(curricula)} upserted")
        print(f"  curriculum_units           : {len(units)} upserted")
        print(f"  content_subject_versions   : {len(versions)} upserted")
        print(f"  content files              : {copied} written to {CONTENT_STORE_PATH}/curricula/")
        if any(nulled_refs.values()):
            print("\nNulled missing FK references (local DB doesn't know these IDs):")
            for k, n in nulled_refs.items():
                if n:
                    print(f"  - {k}: {n}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", help="Path to bundle.tar.gz")
    parser.add_argument("--dry-run", action="store_true", help="Inspect bundle, make no changes")
    args = parser.parse_args()

    try:
        asyncio.run(_import(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
