#!/usr/bin/env python3
"""
scripts/seed_library_local.py — populate the dev DB with the 30 visual
library entries authored under `sample_content/`, without going through
S3 or the GitHub Actions promotion workflow (issue #323 follow-up).

Why this exists
---------------
The promotion CI (`.github/workflows/promote_visual_library.yml` from
#322 phase 3) is the production path: validate sidecars → upload asset
to S3 → compute Voyage embedding → UPSERT visual_library_entries row.
That workflow is gated on cloud-deployment secrets (AWS bucket, IAM
creds) which we don't have on the dev box.

Without library entries in the dev DB, the resolver eval runner
(`run_resolver_eval.py`) can only ever report 0% precision and 0%
recall — every query returns zero rows. That's structurally green but
not informative.

This seeder:
  - Reads every `*.metadata.yaml` under `sample_content/` (reuses the
    parsing logic in `promote_library_metadata.py` so the closed enums
    + filesystem rules are enforced identically).
  - Computes a voyage-3-lite embedding per sidecar.
  - UPSERTs into `visual_library_entries`, using a fake s3_path that
    the resolver doesn't actually dereference (the resolver only
    surfaces s3_path; it never opens it). When real promotion runs,
    the same sidecars will UPSERT the same rows with the real S3 keys.

Required env:
  VOYAGE_API_KEY   — for compute_embedding
  DATABASE_URL     — postgresql:// reachable from this host

Usage from inside the celery-pipeline container (after the bind mounts
added by issue #339 — `./scripts:/app/scripts-repo:ro` and
`./sample_content:/app/sample_content:ro`):

  docker compose exec -T celery-pipeline \\
    python3 /app/scripts-repo/seed_library_local.py

  # idempotent — re-run UPSERTs existing rows; no docker cp needed.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import time
from pathlib import Path

# Free-tier Voyage limit is 3 RPM (one call every 20s). Default to 22s
# spacing for a safety margin; override via VOYAGE_THROTTLE_SECONDS=0 if
# the operator has added a payment method.
VOYAGE_THROTTLE_SECONDS: float = float(os.environ.get("VOYAGE_THROTTLE_SECONDS", "22"))

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))


def _load_promote_module():
    """Reuse promote_library_metadata.py's sidecar parser + helpers
    without invoking its S3 path. Loaded as a module by file path so the
    same closed-enum + filesystem rules apply identically."""
    spec = importlib.util.spec_from_file_location(
        "promote_library_metadata",
        REPO / "scripts" / "promote_library_metadata.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["promote_library_metadata"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _gather_sidecars() -> list[Path]:
    """Find every *.metadata.yaml under sample_content/Option2_Catalogue/."""
    root = REPO / "sample_content"
    candidates = list(root.rglob("Option2_Catalogue/**/*.metadata.yaml"))
    candidates += list(root.rglob("Option2_Catalogue/**/*.metadata.yml"))
    return sorted(set(candidates))


async def _embed_with_backoff(text: str, max_retries: int = 5):
    """compute_embedding with exponential backoff on rate-limit errors.

    Voyage's free tier (3 RPM, 10K TPM) returns a 429-style error with
    a billing-page hint when exceeded. Sleep 65s and retry — that's
    long enough to clear the sliding-window."""
    from src.visuals.library import compute_embedding

    delay = 65.0
    last_err = None
    for attempt in range(max_retries):
        try:
            return await compute_embedding(text)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "rate limit" in msg.lower() or "payment method" in msg.lower():
                last_err = e
                print(
                    f"      rate-limited, sleeping {delay:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})...",
                    flush=True,
                )
                await asyncio.sleep(delay)
                continue
            raise
    raise RuntimeError(
        f"compute_embedding still rate-limited after {max_retries} retries: {last_err}"
    )


async def _seed_one(conn, sidecar) -> str:
    """Compute embedding + UPSERT one sidecar's library row."""
    text = f"{sidecar.topic_phrase} {' '.join(sidecar.keywords)}".strip()
    embedding = await _embed_with_backoff(text)
    if embedding is None:
        raise RuntimeError("VOYAGE_API_KEY missing — cannot embed library entry")

    vec_lit = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"

    # Fake-but-stable s3_path. The resolver surfaces this string but
    # never dereferences it during cosine ranking — production
    # promotion will replace this with the real S3 key on UPSERT.
    s3_path = (
        f"local://visual_library/{sidecar.subject}/{sidecar.id}{sidecar.asset_ext}"
    )

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
        RETURNING entry_id::text
        """,
        sidecar.kind,
        sidecar.subject,
        sidecar.topic_phrase,
        sidecar.keywords,
        s3_path,
        f"local://visual_library/{sidecar.subject}/{sidecar.id}.metadata.yaml",
        sidecar.license,
        sidecar.source_unit,
        vec_lit,
    )
    return str(row["entry_id"])


async def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("error: DATABASE_URL required", file=sys.stderr)
        return 2
    if not os.environ.get("VOYAGE_API_KEY"):
        print("error: VOYAGE_API_KEY required (library entries need embeddings)",
              file=sys.stderr)
        return 2

    promote = _load_promote_module()
    sidecars_paths = _gather_sidecars()
    if not sidecars_paths:
        print("error: no sidecars found under sample_content/", file=sys.stderr)
        return 2

    parsed = [promote._load_sidecar(p) for p in sidecars_paths]
    print(f"Found {len(parsed)} sidecars under sample_content/Option2_Catalogue/")

    import asyncpg
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )

        # Resumable seed — skip rows already in the DB. (To force a clean
        # re-seed, manually `DELETE FROM visual_library_entries WHERE
        # s3_path LIKE 'local://%'` first.)
        existing = {
            row["s3_path"]
            for row in await conn.fetch(
                "SELECT s3_path FROM visual_library_entries "
                "WHERE s3_path LIKE 'local://%'"
            )
        }
        if existing:
            print(f"Found {len(existing)} already-seeded rows; resuming.")

        n_ok = 0
        n_skipped = 0
        embed_calls = 0  # only count actual embed calls for throttling
        for i, s in enumerate(parsed, 1):
            expected_path = (
                f"local://visual_library/{s.subject}/{s.id}{s.asset_ext}"
            )
            if expected_path in existing:
                print(f"  [{i:2d}/{len(parsed)}] ⊙ {s.id:50s} (already seeded — skip)",
                      flush=True)
                n_skipped += 1
                continue
            try:
                if embed_calls > 0 and VOYAGE_THROTTLE_SECONDS > 0:
                    await asyncio.sleep(VOYAGE_THROTTLE_SECONDS)
                embed_calls += 1
                t0 = time.perf_counter()
                eid = await _seed_one(conn, s)
                dt = time.perf_counter() - t0
                print(
                    f"  [{i:2d}/{len(parsed)}] ✓ {s.id:50s} "
                    f"→ entry_id={eid[:8]}… ({dt:.1f}s)",
                    flush=True,
                )
                n_ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [{i:2d}/{len(parsed)}] ✗ {s.id}: {e}",
                      file=sys.stderr, flush=True)
    finally:
        await conn.close()

    print(
        f"\nSeeded {n_ok} new + skipped {n_skipped} existing = "
        f"{n_ok + n_skipped}/{len(parsed)} library entries in dev DB."
    )
    return 0 if (n_ok + n_skipped) == len(parsed) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
