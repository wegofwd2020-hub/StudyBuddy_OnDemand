"""
backend/src/visuals/resolver.py — visual library resolver (issue #323 / 319c).

Given a list of VisualNeed (from pipeline.visual_primitives), look up
matching entries in visual_library_entries via cosine similarity over
the 512-d voyage-3-lite embedding column (migration 0057).  Returns one
ResolvedVisual per input — either a hit (entry_id + s3_path) or a miss
(with diagnostic distances).

Design notes
------------
- Embedding shape parity is critical: the section side embeds
  `topic_phrase + " " + keywords.join(" ")` exactly as the library side
  did at promotion time (see scripts/promote_library_metadata.py +
  backend/src/visuals/library.py::embedding_text_for_entry).  The two
  inputs must hash through voyage-3-lite identically for cosine to be
  meaningful.
- Subject filter is enforced at the SQL level (`WHERE subject = $2`),
  not just in ranking — a math section never matches physics library
  entries (ISC-20 anti).
- RLS bypass: visual_library_entries' SELECT policy allows any session
  with `app.current_school_id` set, but the resolver runs outside a
  FastAPI request context, so it stamps the variable itself
  immediately after acquiring the connection (ISC-11).
- Fail-open under missing VOYAGE_API_KEY: every need returns
  `status='miss'` with `closest_distance=None` and a logged warning,
  rather than crashing the pipeline.

Public surface
--------------
  - ResolvedVisual              Pydantic — discriminated union via `status`
  - resolve(needs, subject, *, threshold=None, top_k=None, pool=None)
  - DEFAULT_THRESHOLD           float read from VISUAL_RESOLVER_THRESHOLD
  - DEFAULT_TOP_K               int   read from VISUAL_RESOLVER_TOP_K
"""

from __future__ import annotations

import logging
import os
from typing import Literal

import asyncpg
from pydantic import BaseModel, Field

from src.visuals.library import compute_embedding

log = logging.getLogger("visuals.resolver")

DEFAULT_THRESHOLD: float = float(os.environ.get("VISUAL_RESOLVER_THRESHOLD", "0.85"))
DEFAULT_TOP_K: int = int(os.environ.get("VISUAL_RESOLVER_TOP_K", "1"))

# pgvector ivfflat probes — number of inverted-list cells to inspect per
# query. The migration 0057 index uses lists=100. At our expected scale
# (hundreds of library entries, not millions), probes=100 effectively
# inspects every list — exact NN behavior with the index providing no
# useful pruning. This is the right tradeoff at small scale: ANN with
# probes < lists silently misses entries that ARE in the table when the
# row's list isn't probed. The pgvector default of probes=1 is tuned
# for million-vector tables and yields unreliable recall here. Once the
# library exceeds ~10k entries, retune (e.g. lists=1000, probes=32) via
# a fresh migration + this env var.
IVFFLAT_PROBES: int = int(os.environ.get("VISUAL_RESOLVER_IVFFLAT_PROBES", "100"))


# ── Result shape ──────────────────────────────────────────────────────────────


class ResolvedVisual(BaseModel):
    """Outcome of resolving one VisualNeed against the library.

    A *hit* carries the matched entry's identifiers; a *miss* carries
    the closest distance observed so the operator can debug whether the
    threshold is too tight or the library is missing coverage.
    """

    status: Literal["hit", "miss"]

    # Echo of the originating need — lets the caller line up resolver
    # outputs with their inputs without keeping a parallel index.
    need_topic_phrase: str
    need_kind: str
    need_subject: str

    # Hit-only fields
    entry_id: str | None = None
    s3_path: str | None = None
    entry_kind: str | None = None
    entry_topic_phrase: str | None = None
    distance: float | None = None

    # Miss-only fields
    closest_distance: float | None = None
    threshold: float | None = None
    second_best_id: str | None = None

    # Diagnostic — preserved on both hit and miss
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _query_text(need) -> str:
    """Build the embedding-input text from a VisualNeed.

    Must mirror library.embedding_text_for_entry() so both sides hash
    through voyage-3-lite identically.
    """
    return f"{need.topic_phrase} {' '.join(need.keywords)}".strip()


def _vec_literal(vec: list[float]) -> str:
    """Render a Python list as a pgvector literal string."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


async def _set_rls_bypass(conn: asyncpg.Connection) -> None:
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")


async def _set_ivfflat_probes(conn: asyncpg.Connection) -> None:
    """Tune ANN recall — must come before any ORDER BY embedding query."""
    await conn.execute(f"SET LOCAL ivfflat.probes = {IVFFLAT_PROBES}")


# ── Single-need lookup ────────────────────────────────────────────────────────


async def _lookup_one(
    conn: asyncpg.Connection,
    need,
    subject: str,
    threshold: float,
    top_k: int,
) -> ResolvedVisual:
    text = _query_text(need)
    embedding = await compute_embedding(text)

    base = ResolvedVisual(
        status="miss",
        need_topic_phrase=need.topic_phrase,
        need_kind=need.kind,
        need_subject=subject,
        threshold=threshold,
        confidence=getattr(need, "confidence", 0.0),
    )

    if embedding is None:
        log.warning(
            "resolver: VOYAGE_API_KEY missing — cannot embed %r, returning miss",
            text,
        )
        return base

    rows = await conn.fetch(
        """
        SELECT
            entry_id::text                AS entry_id,
            kind                          AS kind,
            s3_path                       AS s3_path,
            topic_phrase                  AS topic_phrase,
            (embedding <=> $1::vector)    AS distance
        FROM visual_library_entries
        WHERE subject = $2
          AND archived_at IS NULL
          AND embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT $3
        """,
        _vec_literal(embedding),
        subject,
        top_k,
    )

    if not rows:
        return base  # empty library for this subject — miss

    best = rows[0]
    second = rows[1] if len(rows) > 1 else None
    distance = float(best["distance"])

    if distance <= threshold:
        return ResolvedVisual(
            status="hit",
            need_topic_phrase=need.topic_phrase,
            need_kind=need.kind,
            need_subject=subject,
            entry_id=best["entry_id"],
            s3_path=best["s3_path"],
            entry_kind=best["kind"],
            entry_topic_phrase=best["topic_phrase"],
            distance=distance,
            threshold=threshold,
            confidence=getattr(need, "confidence", 0.0),
        )

    return ResolvedVisual(
        status="miss",
        need_topic_phrase=need.topic_phrase,
        need_kind=need.kind,
        need_subject=subject,
        closest_distance=distance,
        threshold=threshold,
        second_best_id=str(second["entry_id"]) if second is not None else None,
        confidence=getattr(need, "confidence", 0.0),
    )


# ── Public entry ──────────────────────────────────────────────────────────────


async def resolve(
    needs: list,
    subject: str,
    *,
    threshold: float | None = None,
    top_k: int | None = None,
    pool: asyncpg.Pool | None = None,
    conn: asyncpg.Connection | None = None,
) -> list[ResolvedVisual]:
    """Resolve a batch of VisualNeed against visual_library_entries.

    Args:
        needs: list of VisualNeed (from pipeline.visual_primitives).
        subject: closed-enum subject string. Filtered at SQL level so a
                 math need never matches a physics entry.
        threshold: cosine distance ≤ threshold counts as a hit.
                   Defaults to env VISUAL_RESOLVER_THRESHOLD or 0.85.
        top_k: rows to fetch per need; ≥ 2 enables `second_best_id` on
               miss for diagnostic. Defaults to env or 1.
        pool: asyncpg pool. Required when `conn` is None.  The resolver
              acquires its own connection and sets RLS bypass.
        conn: pre-acquired connection. Caller is responsible for RLS
              setup in this case (test fixtures use this path).

    Returns:
        list[ResolvedVisual] same length as `needs`.

    Never raises on a per-need failure — embedding errors yield a miss
    with a logged warning so a flaky provider can't down the pipeline.
    """
    if not needs:
        return []

    threshold = DEFAULT_THRESHOLD if threshold is None else threshold
    top_k = DEFAULT_TOP_K if top_k is None else top_k
    if top_k < 1:
        top_k = 1

    if conn is None and pool is None:
        raise RuntimeError("resolve() requires either a pool or a connection")

    async def _run(c: asyncpg.Connection) -> list[ResolvedVisual]:
        await _set_rls_bypass(c)
        # SET LOCAL needs a transaction; wrap the whole batch so probes
        # tuning sticks for every fetch in this run.
        async with c.transaction():
            await _set_ivfflat_probes(c)
            out: list[ResolvedVisual] = []
            for need in needs:
                try:
                    out.append(await _lookup_one(c, need, subject, threshold, top_k))
                except Exception as e:
                    log.warning(
                        "resolver: lookup failed for %r: %s",
                        getattr(need, "topic_phrase", "<?>"), e,
                    )
                    out.append(
                        ResolvedVisual(
                            status="miss",
                            need_topic_phrase=getattr(need, "topic_phrase", ""),
                            need_kind=getattr(need, "kind", "image"),
                            need_subject=subject,
                            threshold=threshold,
                            confidence=getattr(need, "confidence", 0.0),
                        )
                    )
            return out

    if conn is not None:
        return await _run(conn)

    async with pool.acquire() as c:
        return await _run(c)
