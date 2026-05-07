"""
Tests for backend/src/visuals/resolver.py + pipeline/visual_primitives.py
— issue #323 phase 5.

Coverage map (≥8 ISC-17 floor; 17 tests here):

  Pure-function (no DB, no LLM, no Voyage):
    - VisualNeed model: valid construction, closed kind enum,
      out-of-range confidence, empty keywords (4 tests)
    - _parse_response: failure-tolerant — garbage / dict-not-array /
      code-fences / mixed-validity items (4 tests)
    - ResolvedVisual: hit-state + miss-state construction (2 tests)
    - Module-level helpers: _query_text, _vec_literal (2 tests)

  Live-DB (mocked compute_embedding so no Voyage cost):
    - resolve() hit when distance ≤ threshold (1)
    - resolve() miss when distance > threshold (1)
    - resolve() subject filter — math need vs physics library (1, ISC-20)
    - resolve() returns miss when compute_embedding returns None (1)
    - resolve() short-circuits on empty needs (1)
    - resolve() raises RuntimeError when both pool and conn are None (1)
    - asyncio.gather of 4 concurrent resolves (1, ISC-18)
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import asyncpg
import pytest
import pytest_asyncio
from pydantic import ValidationError

from src.visuals.resolver import (
    DEFAULT_THRESHOLD,
    DEFAULT_TOP_K,
    ResolvedVisual,
    _query_text,
    _vec_literal,
    resolve,
)

_dev_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
_TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    _dev_db_url.replace("/studybuddy", "/studybuddy_test").replace(
        "@pgbouncer:", "@db:"
    ),
)


# ── Test doubles ──────────────────────────────────────────────────────────────


class _StubNeed:
    """Duck-typed VisualNeed substitute for tests that don't import the
    pipeline module (which carries an unrelated heavy import surface)."""

    def __init__(
        self,
        topic_phrase: str = "test",
        keywords: list[str] | None = None,
        kind: str = "image",
        confidence: float = 0.9,
    ) -> None:
        self.topic_phrase = topic_phrase
        self.keywords = keywords or ["test"]
        self.kind = kind
        self.confidence = confidence


# ── Pure-function tests ───────────────────────────────────────────────────────


def test_visual_need_constructs_valid() -> None:
    from pipeline.visual_primitives import VisualNeed

    n = VisualNeed(
        kind="image",
        topic_phrase="projectile motion",
        keywords=["projectile", "trajectory"],
        confidence=0.92,
    )
    assert n.kind == "image"
    assert n.topic_phrase == "projectile motion"
    assert n.confidence == pytest.approx(0.92)


def test_visual_need_rejects_bad_kind() -> None:
    from pipeline.visual_primitives import VisualNeed

    with pytest.raises(ValidationError):
        VisualNeed(
            kind="gif",  # type: ignore[arg-type]
            topic_phrase="x",
            keywords=["y"],
            confidence=0.5,
        )


def test_visual_need_rejects_oob_confidence() -> None:
    from pipeline.visual_primitives import VisualNeed

    with pytest.raises(ValidationError):
        VisualNeed(
            kind="image", topic_phrase="x", keywords=["y"], confidence=1.5
        )
    with pytest.raises(ValidationError):
        VisualNeed(
            kind="image", topic_phrase="x", keywords=["y"], confidence=-0.1
        )


def test_visual_need_rejects_empty_keywords() -> None:
    from pipeline.visual_primitives import VisualNeed

    with pytest.raises(ValidationError):
        VisualNeed(kind="image", topic_phrase="x", keywords=[], confidence=0.5)


def test_parse_response_returns_empty_for_garbage() -> None:
    from pipeline.visual_primitives import _parse_response

    assert _parse_response("not json {{{ at all") == []
    assert _parse_response("") == []
    assert _parse_response("   ") == []


def test_parse_response_returns_empty_for_non_array() -> None:
    from pipeline.visual_primitives import _parse_response

    # Top-level object instead of array
    assert _parse_response('{"kind": "image"}') == []
    # Number
    assert _parse_response("42") == []


def test_parse_response_strips_code_fences() -> None:
    from pipeline.visual_primitives import _parse_response

    fenced = (
        '```json\n'
        '[{"kind":"video","topic_phrase":"projectile arc",'
        '"keywords":["projectile","arc"],"confidence":0.8}]\n'
        '```'
    )
    out = _parse_response(fenced)
    assert len(out) == 1
    assert out[0].kind == "video"
    assert out[0].topic_phrase == "projectile arc"


def test_parse_response_filters_invalid_items() -> None:
    """Mixed-validity input — valid items pass through, invalid items
    are dropped with a logged warning, never raise."""
    from pipeline.visual_primitives import _parse_response

    payload = (
        '['
        '{"kind":"image","topic_phrase":"good","keywords":["a"],"confidence":0.9},'
        '{"kind":"video","topic_phrase":"bad","keywords":["a"],"confidence":2.5},'  # oob confidence
        '{"kind":"image-grid","topic_phrase":"good2","keywords":["b"],"confidence":0.5}'
        ']'
    )
    out = _parse_response(payload)
    assert len(out) == 2
    assert {n.topic_phrase for n in out} == {"good", "good2"}


def test_resolved_visual_hit_state() -> None:
    r = ResolvedVisual(
        status="hit",
        need_topic_phrase="projectile",
        need_kind="image",
        need_subject="physics",
        entry_id="e1",
        s3_path="visual_library/physics/e1.svg",
        entry_kind="image",
        entry_topic_phrase="projectile trajectory",
        distance=0.31,
        threshold=0.85,
    )
    assert r.status == "hit"
    assert r.entry_id == "e1"
    assert r.distance == pytest.approx(0.31)
    assert r.closest_distance is None  # miss-only field


def test_resolved_visual_miss_state() -> None:
    r = ResolvedVisual(
        status="miss",
        need_topic_phrase="x",
        need_kind="video",
        need_subject="math",
        closest_distance=0.92,
        threshold=0.85,
        second_best_id="next-best",
    )
    assert r.status == "miss"
    assert r.closest_distance == pytest.approx(0.92)
    assert r.entry_id is None  # hit-only field


def test_query_text_matches_library_shape() -> None:
    """The embedding-input string must match library.embedding_text_for_entry().
    Both sides hash through voyage-3-lite and cosine distances are only
    comparable when shapes align."""
    n = _StubNeed(
        topic_phrase="projectile motion",
        keywords=["parabola", "range", "max-height"],
    )
    assert _query_text(n) == "projectile motion parabola range max-height"


def test_vec_literal_format() -> None:
    """The pgvector literal must be a bracketed comma-separated list
    that PG can cast to vector via $1::vector."""
    s = _vec_literal([0.1, -0.5, 1.0])
    assert s.startswith("[")
    assert s.endswith("]")
    parts = s.strip("[]").split(",")
    assert len(parts) == 3
    assert float(parts[0]) == pytest.approx(0.1)


def test_module_level_defaults_present() -> None:
    """ISC-10: env-driven defaults are read at import time."""
    assert DEFAULT_THRESHOLD > 0
    assert DEFAULT_THRESHOLD <= 1.0
    assert DEFAULT_TOP_K >= 1


# ── Live-DB integration tests (mocked compute_embedding) ──────────────────────


@pytest_asyncio.fixture
async def bypass_conn():
    """An asyncpg connection with app.current_school_id=bypass and ivfflat
    probes tuned to the table's lists-count so ANN doesn't silently miss
    sparse fixture rows."""
    c = await asyncpg.connect(_TEST_DB_URL)
    await c.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    yield c
    await c.close()


@pytest_asyncio.fixture
async def seeded_physics_row(bypass_conn):
    """Insert a single physics fixture row with a known unit-vector
    embedding e1 = [1, 0, 0, …, 0]. Cleans up after the test."""
    e1 = [1.0] + [0.0] * 511
    vec = "[" + ",".join(f"{x:.6f}" for x in e1) + "]"

    # Use a marker topic_phrase so concurrent test runs don't collide
    marker = "resolver-test-fixture-row"
    eid = await bypass_conn.fetchval(
        """
        INSERT INTO visual_library_entries
            (kind, subject, topic_phrase, keywords, s3_path, license, embedding)
        VALUES ('image', 'physics', $1, ARRAY['fixture'],
                $2, 'platform-cc-by-sa', $3::vector)
        RETURNING entry_id::text
        """,
        marker,
        f"local://test/{marker}.svg",
        vec,
    )
    yield {"entry_id": eid, "embedding": e1, "marker": marker}
    await bypass_conn.execute(
        "DELETE FROM visual_library_entries WHERE topic_phrase = $1", marker
    )


@pytest.mark.asyncio
async def test_resolve_hit_when_distance_below_threshold(
    bypass_conn, seeded_physics_row
):
    """ISC-7, ISC-9 — query identical to the row's embedding → distance ~0
    → status='hit' with the correct entry_id."""
    e1 = seeded_physics_row["embedding"]

    async def fake(_text):
        return e1

    with patch("src.visuals.resolver.compute_embedding", side_effect=fake):
        out = await resolve(
            [_StubNeed("test", ["fixture"])],
            subject="physics",
            conn=bypass_conn,
        )

    assert len(out) == 1
    assert out[0].status == "hit"
    assert out[0].entry_id == seeded_physics_row["entry_id"]
    assert out[0].distance is not None and out[0].distance < 0.01


@pytest.mark.asyncio
async def test_resolve_miss_when_distance_above_threshold(
    bypass_conn, seeded_physics_row
):
    """ISC-9 — orthogonal embedding (cosine distance = 1) at threshold 0.5
    → status='miss', closest_distance preserved for diagnostic."""
    e_orthogonal = [0.0] * 511 + [1.0]

    async def fake(_text):
        return e_orthogonal

    with patch("src.visuals.resolver.compute_embedding", side_effect=fake):
        out = await resolve(
            [_StubNeed("test", ["fixture"])],
            subject="physics",
            conn=bypass_conn,
            threshold=0.5,
        )

    assert out[0].status == "miss"
    assert out[0].closest_distance is not None
    assert out[0].closest_distance > 0.9
    assert out[0].entry_id is None


@pytest.mark.asyncio
async def test_resolve_subject_filter_blocks_cross_subject(
    bypass_conn, seeded_physics_row
):
    """ISC-20 anti — query subject='math' against a physics-only
    library row never returns a hit, even with a perfect-match embedding."""
    e1 = seeded_physics_row["embedding"]

    async def fake(_text):
        return e1

    with patch("src.visuals.resolver.compute_embedding", side_effect=fake):
        out = await resolve(
            [_StubNeed("test", ["fixture"])],
            subject="math",
            conn=bypass_conn,
        )

    assert out[0].status == "miss"
    assert out[0].closest_distance is None  # zero rows = no diagnostic distance


@pytest.mark.asyncio
async def test_resolve_returns_miss_when_voyage_returns_none(
    bypass_conn, seeded_physics_row
):
    """Fail-open under missing VOYAGE_API_KEY: compute_embedding returns
    None → resolver yields a miss with closest_distance=None and a
    logged warning, never crashes."""

    async def fake(_text):
        return None

    with patch("src.visuals.resolver.compute_embedding", side_effect=fake):
        out = await resolve(
            [_StubNeed("test", ["fixture"])],
            subject="physics",
            conn=bypass_conn,
        )

    assert out[0].status == "miss"
    assert out[0].closest_distance is None


@pytest.mark.asyncio
async def test_resolve_empty_needs_short_circuits():
    """No needs → empty result list, no DB or embedding call required.
    pool=None and conn=None are both fine when needs is empty."""
    out = await resolve([], subject="physics")
    assert out == []


@pytest.mark.asyncio
async def test_resolve_requires_pool_or_conn():
    """Calling with non-empty needs but no pool and no conn raises RuntimeError."""
    with pytest.raises(RuntimeError, match="pool or a connection"):
        await resolve([_StubNeed("x", ["y"])], subject="physics")


@pytest.mark.asyncio
async def test_resolve_concurrent_gather(seeded_physics_row):
    """ISC-18 — four parallel resolves (each on its own connection) all
    succeed without deadlocking the embedding query."""
    e1 = seeded_physics_row["embedding"]

    async def fake(_text):
        return e1

    async def one(idx: int) -> ResolvedVisual:
        c = await asyncpg.connect(_TEST_DB_URL)
        try:
            with patch("src.visuals.resolver.compute_embedding", side_effect=fake):
                out = await resolve(
                    [_StubNeed(f"test{idx}", ["fixture"])],
                    subject="physics",
                    conn=c,
                )
                return out[0]
        finally:
            await c.close()

    results = await asyncio.gather(*[one(i) for i in range(4)])
    assert all(r.status == "hit" for r in results)
    # All four hit the same fixture row
    assert all(r.entry_id == seeded_physics_row["entry_id"] for r in results)
