#!/usr/bin/env python3
"""
backend/scripts/index_help_library.py

Parses the Lib-A help content JSONL file, embeds each chunk with Voyage AI
voyage-3-lite, and upserts the vectors into the help_chunks table.

Run this once after deploying migration 0040 to populate the vector index.
Re-run it whenever help_chunks.jsonl is updated (it is idempotent).

Usage:
    # From backend/ directory (requires VOYAGE_API_KEY in env or .env):
    python scripts/index_help_library.py

    # Skip embedding (inserts text-only rows for dev without Voyage API key):
    SKIP_EMBED=1 python scripts/index_help_library.py

Requires:
    voyageai>=0.3.0   (in requirements.txt)
    asyncpg           (in requirements.txt)

Environment:
    DATABASE_URL      — PostgreSQL connection string (required)
    VOYAGE_API_KEY    — Voyage AI API key (optional; skip embedding if absent)
    SKIP_EMBED        — Set to "1" to skip embedding step (dev / testing)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# ── Bootstrap ─────────────────────────────────────────────────────────────────

_here = Path(__file__).parent.parent
load_dotenv(_here / ".env")

_JSONL_PATH = _here / "data" / "help_chunks.jsonl"
_DATABASE_URL = os.environ.get("DATABASE_URL", "")
_VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
_SKIP_EMBED = os.environ.get("SKIP_EMBED", "") == "1"

_VOYAGE_MODEL = "voyage-3-lite"
_EMBED_DIM = 512
_BATCH_SIZE = 16  # Voyage AI rate limit — embed up to 16 texts per call
# Seconds between batches. 3 requests/minute is the free-tier cap (no payment
# method on the account), so 21s keeps a whole run inside it without ever being
# refused. Overridable for accounts on a paid tier, where this is pure waiting.
_BATCH_PAUSE_S = float(os.getenv("EMBED_BATCH_PAUSE_S", "21"))


# ── Embedding ─────────────────────────────────────────────────────────────────


async def _embed_batch(texts: list[str], *, attempts: int = 6) -> list[list[float]]:
    """Call Voyage AI to embed a batch of texts. Returns parallel list of vectors.

    Retries on rate limiting, which is not an edge case here: a Voyage account
    without a payment method is capped at 3 requests per minute, and this script
    fires its batches back to back. On the 67-chunk library that is 5 calls in
    about a second, so it failed on the third every time — which is very likely
    why the help corpus had never actually been indexed anywhere.

    Backoff starts above the 20s-per-request budget that 3 RPM implies, so the
    common case recovers on the first retry rather than grinding through several.
    """
    import voyageai

    client = voyageai.AsyncClient(api_key=_VOYAGE_API_KEY)
    delay = 25.0
    for attempt in range(1, attempts + 1):
        try:
            result = await client.embed(texts, model=_VOYAGE_MODEL, input_type="document")
            return result.embeddings
        except Exception as exc:  # voyageai raises its own RateLimitError type
            transient = "rate" in type(exc).__name__.lower() or "rate limit" in str(exc).lower()
            if not transient or attempt == attempts:
                raise
            print(f"  rate-limited (attempt {attempt}/{attempts}); waiting {delay:.0f}s")
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 90.0)
    raise RuntimeError("unreachable")


# ── Database upsert ───────────────────────────────────────────────────────────


async def _upsert_chunk(
    conn: asyncpg.Connection,
    chunk_id: uuid.UUID,
    persona: str,
    source_file: str,
    section_id: str,
    heading: str,
    body: str,
    embedding: list[float] | None,
) -> None:
    """Upsert one help_chunk row (idempotent on chunk_id)."""
    if embedding is not None:
        vec_literal = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
        await conn.execute(
            """
            INSERT INTO help_chunks
                (chunk_id, persona, source_file, section_id, heading, body, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7::vector)
            ON CONFLICT (chunk_id) DO UPDATE
                SET persona     = EXCLUDED.persona,
                    source_file = EXCLUDED.source_file,
                    section_id  = EXCLUDED.section_id,
                    heading     = EXCLUDED.heading,
                    body        = EXCLUDED.body,
                    embedding   = EXCLUDED.embedding
            """,
            chunk_id,
            persona,
            source_file,
            section_id,
            heading,
            body,
            vec_literal,
        )
    else:
        await conn.execute(
            """
            INSERT INTO help_chunks
                (chunk_id, persona, source_file, section_id, heading, body)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (chunk_id) DO UPDATE
                SET persona     = EXCLUDED.persona,
                    source_file = EXCLUDED.source_file,
                    section_id  = EXCLUDED.section_id,
                    heading     = EXCLUDED.heading,
                    body        = EXCLUDED.body
            """,
            chunk_id,
            persona,
            source_file,
            section_id,
            heading,
            body,
        )


# ── Deterministic chunk ID ────────────────────────────────────────────────────


def _chunk_uuid(source_file: str, section_id: str) -> uuid.UUID:
    """
    Derive a stable UUID from source_file + section_id using UUIDv5.

    Using a fixed namespace means re-running the script always produces the
    same chunk_id for the same content source — ON CONFLICT DO UPDATE is safe.
    """
    namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    return uuid.uuid5(namespace, f"{source_file}::{section_id}")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    if not _DATABASE_URL:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    if not _JSONL_PATH.exists():
        print(f"ERROR: JSONL not found: {_JSONL_PATH}", file=sys.stderr)
        sys.exit(1)

    # Load all chunks from JSONL.
    chunks = []
    with _JSONL_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    print(f"Loaded {len(chunks)} chunks from {_JSONL_PATH.name}")

    # Embed in batches (or skip).
    embeddings: list[list[float] | None]
    if _SKIP_EMBED or not _VOYAGE_API_KEY:
        reason = "SKIP_EMBED=1" if _SKIP_EMBED else "no VOYAGE_API_KEY"
        print(f"Skipping embedding ({reason}) — inserting text-only rows.")
        embeddings = [None] * len(chunks)
    else:
        print(f"Embedding {len(chunks)} chunks with {_VOYAGE_MODEL} …")
        texts = [f"{c['heading']}\n\n{c['body']}" for c in chunks]
        embeddings = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            # Pace the calls rather than relying on the retry alone. A Voyage
            # account with no payment method allows 3 requests per minute, so
            # firing every batch immediately spends the whole minute's quota on
            # the first three and then waits regardless — pacing costs the same
            # wall-clock time and never surfaces an error.
            if i:
                await asyncio.sleep(_BATCH_PAUSE_S)
            batch_vecs = await _embed_batch(batch)
            embeddings.extend(batch_vecs)
            print(f"  Embedded {min(i + _BATCH_SIZE, len(texts))}/{len(texts)}")

    # Upsert all chunks.
    conn = await asyncpg.connect(_DATABASE_URL, statement_cache_size=0)
    try:
        inserted = 0
        # strict=True: if the embedding list ever comes back shorter than the
        # chunk list, zip() would silently index only the prefix and report
        # success for a partial corpus. Better to fail loudly than to leave the
        # help widget quietly missing sections nobody knows are absent.
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_id = _chunk_uuid(chunk["source_file"], chunk["section_id"])
            await _upsert_chunk(
                conn,
                chunk_id=chunk_id,
                persona=chunk["persona"],
                source_file=chunk["source_file"],
                section_id=chunk["section_id"],
                heading=chunk["heading"],
                body=chunk["body"],
                embedding=embedding,
            )
            inserted += 1

        print(f"Upserted {inserted} chunk(s) into help_chunks.")
        embedded_count = sum(1 for e in embeddings if e is not None)
        print(f"  {embedded_count} with embeddings, {inserted - embedded_count} text-only.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
