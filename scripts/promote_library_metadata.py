#!/usr/bin/env python3
"""
Promote validated visual-library sidecars into the live library
(S3 + visual_library_entries DB row).  Issue #322 phase 3.

Inputs  : list of paths or globs to *.metadata.yaml files (already
          validated by scripts/validate_library_metadata.ts).
For each : 1. parse the sidecar
           2. resolve sibling asset
           3. upload asset to S3 at visual_library/{subject}/{slug}.{ext}
              (ContentType inferred from the extension)
           4. compute Voyage embedding from
              topic_phrase + " " + keywords.join(" ")
           5. UPSERT visual_library_entries by id

Idempotent — re-promoting the same sidecar replaces the asset on S3 and
updates the DB row in place (so a later asset re-author bumps the same
library entry rather than orphaning the previous one).

Required env:
  VISUAL_STORAGE_S3_BUCKET
  VISUAL_STORAGE_S3_PREFIX  (defaults to "visuals")
  AWS_REGION
  AWS_ACCESS_KEY_ID         (provided by github-actions)
  AWS_SECRET_ACCESS_KEY     (provided by github-actions)
  VOYAGE_API_KEY
  DATABASE_URL              (postgresql://...)

Run from repo root:
  python3 scripts/promote_library_metadata.py \\
    sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/set-operations/union.metadata.yaml
"""

from __future__ import annotations

import asyncio
import glob
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ── Closed enums (must mirror the validator + the Pydantic LibraryEntry) ────

KINDS = {"image", "image-grid", "animated-svg", "video"}
SUBJECTS = {
    "physics", "chemistry", "math", "biology",
    "geography", "history", "languages",
}
LICENSES = {"platform-cc-by-sa", "platform-proprietary"}

EXT_BY_KIND = {
    "image": {".svg", ".png", ".jpg", ".jpeg", ".webp"},
    "image-grid": {".svg", ".png", ".jpg", ".jpeg", ".webp"},
    "animated-svg": {".svg"},
    "video": {".mp4", ".webm"},
}
CONTENT_TYPE = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}

EMBEDDING_MODEL = "voyage-3-lite"
EMBEDDING_DIM = 512


# ── Sidecar parsing — minimal flat YAML, mirrors the TS validator ─────────


@dataclass
class Sidecar:
    schema_version: int
    id: str
    kind: str
    subject: str
    topic_phrase: str
    keywords: list[str]
    license: str
    source_unit: str | None
    asset_path: Path

    @property
    def asset_ext(self) -> str:
        return self.asset_path.suffix.lower()

    @property
    def s3_path(self) -> str:
        return f"visual_library/{self.subject}/{self.id}{self.asset_ext}"

    @property
    def metadata_path(self) -> str:
        return f"visual_library/{self.subject}/{self.id}.metadata.yaml"

    def embedding_text(self) -> str:
        return f"{self.topic_phrase} {' '.join(self.keywords)}".strip()


def _parse_yaml(path: Path) -> dict:
    """Same flat-YAML semantics as scripts/validate_library_metadata.ts."""
    out: dict = {}
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        colon = line.find(":")
        if colon == -1:
            raise ValueError(f"{path}: bad line {i + 1}: {line!r}")
        key = line[:colon].strip()
        after = line[colon + 1 :].strip()
        # Strip trailing comments
        if "#" in after and not (after.startswith('"') or after.startswith("'")):
            after = after.split("#", 1)[0].strip()
        if not after:
            items: list = []
            i += 1
            while i < len(lines):
                sub = lines[i]
                if sub.lstrip().startswith("-"):
                    items.append(_parse_scalar(sub.lstrip()[1:].strip()))
                    i += 1
                elif sub.strip() == "" or sub.strip().startswith("#"):
                    i += 1
                else:
                    break
            out[key] = items
        else:
            out[key] = _parse_scalar(after)
            i += 1
    return out


def _parse_scalar(raw: str):
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.lstrip("-").isdigit():
        return int(raw)
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    return raw


def _load_sidecar(path: Path) -> Sidecar:
    doc = _parse_yaml(path)
    schema_version = doc.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"{path}: schema_version must be 1 (got {schema_version!r})")

    id_ = doc.get("id")
    kind = doc.get("kind")
    subject = doc.get("subject")
    topic_phrase = doc.get("topic_phrase")
    keywords = doc.get("keywords") or []
    license_ = doc.get("license")
    source_unit = doc.get("source_unit")

    if not isinstance(id_, str) or not id_:
        raise ValueError(f"{path}: id missing or not a string")
    if kind not in KINDS:
        raise ValueError(f"{path}: kind {kind!r} not in {sorted(KINDS)}")
    if subject not in SUBJECTS:
        raise ValueError(f"{path}: subject {subject!r} not in {sorted(SUBJECTS)}")
    if not isinstance(topic_phrase, str) or not topic_phrase:
        raise ValueError(f"{path}: topic_phrase missing")
    if not isinstance(keywords, list) or not keywords:
        raise ValueError(f"{path}: keywords missing")
    if license_ not in LICENSES:
        raise ValueError(f"{path}: license {license_!r} not in {sorted(LICENSES)}")

    # Find sibling asset
    stem = path.name.replace(".metadata.yaml", "").replace(".metadata.yml", "")
    candidates = [
        path.parent / f"{stem}{ext}" for ext in EXT_BY_KIND[kind]
    ]
    found = [c for c in candidates if c.is_file()]
    if not found:
        raise ValueError(
            f"{path}: no sibling asset {stem}.<{'|'.join(sorted(EXT_BY_KIND[kind]))}>"
        )
    if len(found) > 1:
        raise ValueError(f"{path}: multiple sibling assets: {[str(c) for c in found]}")

    return Sidecar(
        schema_version=schema_version,
        id=id_,
        kind=kind,
        subject=subject,
        topic_phrase=topic_phrase,
        keywords=keywords,
        license=license_,
        source_unit=source_unit if isinstance(source_unit, str) else None,
        asset_path=found[0],
    )


# ── S3 upload ──────────────────────────────────────────────────────────────


def _s3_client():
    import boto3  # type: ignore

    return boto3.client("s3", region_name=os.environ.get("AWS_REGION"))


def upload_to_s3(sidecar: Sidecar, bucket: str, prefix: str) -> str:
    """Upload the asset (and the sidecar) to S3. Returns the asset's S3 key."""
    client = _s3_client()
    key = f"{prefix}/{sidecar.s3_path}" if prefix else sidecar.s3_path
    meta_key = f"{prefix}/{sidecar.metadata_path}" if prefix else sidecar.metadata_path

    asset_bytes = sidecar.asset_path.read_bytes()
    ct = CONTENT_TYPE.get(sidecar.asset_ext, "application/octet-stream")
    extra: dict = {}
    acl = os.environ.get("VISUAL_STORAGE_ACL")
    if acl:
        extra["ACL"] = acl

    client.put_object(
        Bucket=bucket, Key=key, Body=asset_bytes, ContentType=ct, **extra,
    )

    sidecar_bytes = (
        sidecar.asset_path.parent / f"{sidecar.asset_path.stem}.metadata.yaml"
    ).read_bytes()
    client.put_object(
        Bucket=bucket, Key=meta_key, Body=sidecar_bytes,
        ContentType="text/yaml", **extra,
    )
    return key


# ── Voyage embedding ───────────────────────────────────────────────────────


async def compute_embedding(text: str) -> list[float]:
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY required for library promotion")
    import voyageai  # type: ignore

    client = voyageai.AsyncClient(api_key=api_key)
    result = await client.embed([text], model=EMBEDDING_MODEL, input_type="document")
    vec = result.embeddings[0]
    if len(vec) != EMBEDDING_DIM:
        raise RuntimeError(
            f"Voyage returned {len(vec)}-d vector; expected {EMBEDDING_DIM}"
        )
    return vec


# ── DB upsert ──────────────────────────────────────────────────────────────


async def upsert_entry(sidecar: Sidecar, s3_key: str, embedding: list[float]) -> str:
    """UPSERT visual_library_entries by id. Returns entry_id."""
    import asyncpg  # type: ignore

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL required for library promotion")
    db_url = db_url.replace("@pgbouncer:", "@db:")  # bypass pgbouncer for DDL

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        # We treat `id` as the natural key.  If a row with the same s3_path
        # exists (active) we UPDATE; otherwise INSERT.
        vec_lit = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
        row = await conn.fetchrow(
            """
            INSERT INTO visual_library_entries
                (kind, subject, topic_phrase, keywords, s3_path, s3_metadata_path,
                 license, source_unit, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector)
            ON CONFLICT (s3_path) WHERE archived_at IS NULL
            DO UPDATE SET
                kind             = EXCLUDED.kind,
                topic_phrase     = EXCLUDED.topic_phrase,
                keywords         = EXCLUDED.keywords,
                s3_metadata_path = EXCLUDED.s3_metadata_path,
                license          = EXCLUDED.license,
                source_unit      = EXCLUDED.source_unit,
                embedding        = EXCLUDED.embedding,
                updated_at       = now()
            RETURNING entry_id
            """,
            sidecar.kind,
            sidecar.subject,
            sidecar.topic_phrase,
            sidecar.keywords,
            s3_key,
            f"{os.path.dirname(s3_key)}/{sidecar.id}.metadata.yaml",
            sidecar.license,
            sidecar.source_unit,
            vec_lit,
        )
        return str(row["entry_id"])
    finally:
        await conn.close()


# ── Main ───────────────────────────────────────────────────────────────────


def _resolve_inputs(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for arg in args:
        if any(c in arg for c in "*?["):
            out.extend(Path(p) for p in sorted(glob.glob(arg, recursive=True)))
        else:
            p = Path(arg)
            if p.is_dir():
                out.extend(sorted(p.rglob("*.metadata.yaml")))
                out.extend(sorted(p.rglob("*.metadata.yml")))
            elif p.is_file():
                out.append(p)
    return out


async def promote_one(sidecar_path: Path) -> dict:
    bucket = os.environ.get("VISUAL_STORAGE_S3_BUCKET")
    prefix = os.environ.get("VISUAL_STORAGE_S3_PREFIX", "visuals")
    if not bucket:
        raise RuntimeError("VISUAL_STORAGE_S3_BUCKET required")

    sidecar = _load_sidecar(sidecar_path)
    s3_key = upload_to_s3(sidecar, bucket, prefix)
    embedding = await compute_embedding(sidecar.embedding_text())
    entry_id = await upsert_entry(sidecar, s3_key, embedding)
    return {
        "sidecar": str(sidecar_path),
        "id": sidecar.id,
        "entry_id": entry_id,
        "s3_key": s3_key,
        "embedding_dim": len(embedding),
    }


async def main(args: Iterable[str]) -> int:
    files = _resolve_inputs(list(args))
    if not files:
        print("error: no sidecar files matched", file=sys.stderr)
        return 2

    failures = 0
    for f in files:
        try:
            r = await promote_one(f)
            print(
                f"✓ {r['id']}  ←  {r['sidecar']}  "
                f"(entry_id={r['entry_id']}, embedding={r['embedding_dim']}d)"
            )
        except Exception as e:
            failures += 1
            print(f"✗ {f}: {e}", file=sys.stderr)

    if failures:
        print(f"\n✗ {failures}/{len(files)} sidecar(s) failed", file=sys.stderr)
        return 1
    print(f"\n✓ promoted {len(files)} sidecar(s)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
