#!/usr/bin/env python3
"""
scripts/run_resolver_eval.py — visual resolver eval runner (issue #323 phase 4).

Reads backend/tests/eval/visual_resolver_eval.jsonl and, for each
record, runs the full resolver pipeline:

  1. identify_visual_needs(section_content, section_title, subject)
     — LLM extracts list[VisualNeed]
  2. For the highest-confidence need: compute_embedding + a top-k
     cosine query against visual_library_entries

Computes:
  - precision @ 1  (correct hit / all predicted hits)
  - recall @ 3     (sections whose expected_entry_id appears in top-3)
  - per-category breakdown (known_positive / known_negative / borderline_*)

Gates exit:
  precision @ 1 < THRESHOLD  →  exit 1   (CI gate)
  any other failure          →  exit 2

Spec note: issue #319c named this `scripts/run_resolver_eval.ts`. We
write it as Python because it imports `pipeline.visual_primitives` and
`backend/src/visuals/resolver`, both Python modules.  Same precedent as
`scripts/promote_library_metadata.py`.

Required env (read at runtime):
  ANTHROPIC_API_KEY   — for identify_visual_needs LLM call
  VOYAGE_API_KEY      — for compute_embedding inside the cosine query
  DATABASE_URL        — postgresql:// reachable from this host

Run from repo root:
  python3 scripts/run_resolver_eval.py
  python3 scripts/run_resolver_eval.py --threshold-gate 0.70 --top-k 3
  python3 scripts/run_resolver_eval.py --eval-file path/to/custom.jsonl --quiet
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make backend.src + pipeline importable when running from repo root.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))


# ── Knobs ─────────────────────────────────────────────────────────────────────

DEFAULT_EVAL_PATH = REPO_ROOT / "backend" / "tests" / "eval" / "visual_resolver_eval.jsonl"
DEFAULT_THRESHOLD_GATE = float(os.environ.get("VISUAL_EVAL_PRECISION_GATE", "0.70"))
DEFAULT_HIT_THRESHOLD = float(os.environ.get("VISUAL_RESOLVER_THRESHOLD", "0.85"))
DEFAULT_TOP_K = int(os.environ.get("VISUAL_EVAL_TOP_K", "3"))
DEFAULT_PROBES = int(os.environ.get("VISUAL_RESOLVER_IVFFLAT_PROBES", "100"))

# Voyage free-tier rate limit is 3 RPM. Set to 22s spacing by default for
# safety margin; if the operator has added a payment method, set
# VOYAGE_THROTTLE_SECONDS=0 to disable throttling.
VOYAGE_THROTTLE_SECONDS = float(os.environ.get("VOYAGE_THROTTLE_SECONDS", "22"))


# ── Eval record ───────────────────────────────────────────────────────────────


def _load_eval(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{i}: bad JSON — {e}")
    return records


# ── Per-record execution ──────────────────────────────────────────────────────


async def _run_one(
    rec: dict,
    conn,
    top_k: int,
    hit_threshold: float,
) -> dict:
    """Run a single eval record through the full resolver pipeline.

    Returns a result dict suitable for JSONL output and metrics.
    """
    from pipeline.visual_primitives import identify_visual_needs
    from src.visuals.library import compute_embedding

    t0 = time.perf_counter()
    needs = await identify_visual_needs(
        section_content=rec["section_content"],
        section_title=rec["section_title"],
        subject=rec["subject"],
    )
    t_llm = time.perf_counter() - t0

    out = {
        "eval_id": rec["id"],
        "category": rec["category"],
        "subject": rec["subject"],
        "expected_hit": rec["expected_hit"],
        "expected_entry_id": rec.get("expected_entry_id"),
        "n_needs_extracted": len(needs),
        "needs": [
            {
                "kind": n.kind,
                "topic_phrase": n.topic_phrase,
                "keywords": n.keywords,
                "confidence": n.confidence,
            }
            for n in needs
        ],
        "top_k": [],
        "predicted_hit": False,
        "predicted_top1_id": None,
        "predicted_top1_distance": None,
        "expected_in_top_k": False,
        "t_llm_s": round(t_llm, 3),
        "t_query_s": None,
    }

    if not needs:
        return out

    # Pick highest-confidence need; fall back to first if confidences tie
    best = max(needs, key=lambda n: n.confidence)
    query_text = f"{best.topic_phrase} {' '.join(best.keywords)}".strip()

    t1 = time.perf_counter()
    embedding = await compute_embedding(query_text)
    if embedding is None:
        out["t_query_s"] = round(time.perf_counter() - t1, 3)
        out["error"] = "VOYAGE_API_KEY missing — cannot embed"
        return out

    vec_lit = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    rows = await conn.fetch(
        """
        SELECT
            entry_id::text                AS entry_id,
            kind                          AS kind,
            topic_phrase                  AS topic_phrase,
            (embedding <=> $1::vector)    AS distance
        FROM visual_library_entries
        WHERE subject = $2
          AND archived_at IS NULL
          AND embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT $3
        """,
        vec_lit,
        rec["subject"],
        top_k,
    )
    out["t_query_s"] = round(time.perf_counter() - t1, 3)

    out["top_k"] = [
        {
            "entry_id": r["entry_id"],
            "kind": r["kind"],
            "topic_phrase": r["topic_phrase"],
            "distance": float(r["distance"]),
        }
        for r in rows
    ]

    if rows:
        top1 = rows[0]
        d = float(top1["distance"])
        out["predicted_top1_id"] = top1["entry_id"]
        out["predicted_top1_distance"] = d
        out["predicted_hit"] = d <= hit_threshold

    if rec.get("expected_entry_id"):
        out["expected_in_top_k"] = any(
            r["entry_id"] == rec["expected_entry_id"] for r in rows
        )

    return out


# ── Metrics ───────────────────────────────────────────────────────────────────


def _compute_metrics(results: list[dict]) -> dict:
    """Compute precision @ 1, recall @ k, cost stats, per-category breakdown."""
    tp = fp = tn = fn = 0
    n_llm_calls = 0
    n_voyage_calls = 0
    t_llm_total = 0.0
    t_query_total = 0.0

    for r in results:
        # LLM was called iff we reached _run_one (failures count as no call).
        if r.get("t_llm_s") is not None:
            n_llm_calls += 1
        # Voyage was called iff at least one need was extracted (compute_embedding
        # only runs after needs is non-empty).
        if (r.get("n_needs_extracted") or 0) > 0:
            n_voyage_calls += 1
        t_llm_total += r.get("t_llm_s") or 0.0
        t_query_total += r.get("t_query_s") or 0.0

    for r in results:
        expected_hit = r["expected_hit"]
        predicted_hit = r["predicted_hit"]
        expected_id = r.get("expected_entry_id")
        predicted_id = r.get("predicted_top1_id")

        if predicted_hit:
            # Predicted positive
            if expected_hit and expected_id == predicted_id:
                tp += 1
            else:
                fp += 1
        else:
            # Predicted negative
            if expected_hit:
                fn += 1
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    expected_hits = [r for r in results if r["expected_hit"]]
    recall_at_k = (
        sum(1 for r in expected_hits if r["expected_in_top_k"]) / len(expected_hits)
        if expected_hits
        else 0.0
    )

    # Per-category breakdown — simpler binary correctness
    by_category: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0, "incorrect": 0}
    )
    for r in results:
        cat = r["category"]
        by_category[cat]["n"] += 1
        # "Correct" = predicted_hit matches expected_hit AND
        # (if expected_hit, predicted_id matches expected_id)
        if r["predicted_hit"] == r["expected_hit"]:
            if not r["expected_hit"] or (
                r.get("expected_entry_id") == r.get("predicted_top1_id")
            ):
                by_category[cat]["correct"] += 1
            else:
                by_category[cat]["incorrect"] += 1
        else:
            by_category[cat]["incorrect"] += 1

    return {
        "n_records": len(results),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision_at_1": round(precision, 4),
        "recall_at_k": round(recall_at_k, 4),
        "cost": {
            "n_llm_calls": n_llm_calls,
            "n_voyage_calls": n_voyage_calls,
            "t_llm_total_s": round(t_llm_total, 2),
            "t_query_total_s": round(t_query_total, 2),
            "t_llm_avg_s": round(t_llm_total / max(n_llm_calls, 1), 2),
            "t_query_avg_s": round(t_query_total / max(n_voyage_calls, 1), 2),
        },
        "by_category": {
            k: {
                **v,
                "accuracy": round(v["correct"] / v["n"], 4) if v["n"] > 0 else 0.0,
            }
            for k, v in sorted(by_category.items())
        },
    }


# ── Reporting ─────────────────────────────────────────────────────────────────


def _print_report(
    metrics: dict,
    results: list[dict],
    threshold_gate: float,
    quiet: bool,
) -> None:
    if quiet:
        print(json.dumps(metrics, indent=2))
        return

    print()
    print("=" * 64)
    print(f"VISUAL RESOLVER EVAL — {metrics['n_records']} records")
    print("=" * 64)
    print()
    print(f"  Precision @ 1  : {metrics['precision_at_1']:.4f}  "
          f"(gate ≥ {threshold_gate:.2f})")
    print(f"  Recall    @ k  : {metrics['recall_at_k']:.4f}  "
          f"(over {sum(1 for r in results if r['expected_hit'])} expected hits)")
    print()
    print(f"  TP={metrics['tp']:3d}   FP={metrics['fp']:3d}   "
          f"TN={metrics['tn']:3d}   FN={metrics['fn']:3d}")
    print()
    c = metrics["cost"]
    print(
        f"  Cost  : {c['n_llm_calls']} LLM × {c['t_llm_avg_s']}s avg  "
        f"({c['t_llm_total_s']}s total)"
    )
    print(
        f"          {c['n_voyage_calls']} Voyage × {c['t_query_avg_s']}s avg  "
        f"({c['t_query_total_s']}s total)"
    )
    print()
    print("  By category:")
    for cat, v in metrics["by_category"].items():
        bar = "█" * int(v["accuracy"] * 20)
        print(
            f"    {cat:32s}  n={v['n']:2d}  acc={v['accuracy']:.2f}  {bar}"
        )

    # First few mismatches help debug what's drifting
    mismatches = [
        r for r in results
        if r["predicted_hit"] != r["expected_hit"]
        or (
            r["expected_hit"]
            and r.get("expected_entry_id") != r.get("predicted_top1_id")
        )
    ]
    if mismatches:
        print()
        print(f"  First {min(5, len(mismatches))} mismatches:")
        for r in mismatches[:5]:
            print(
                f"    {r['eval_id']} ({r['category']})  "
                f"expected={r.get('expected_entry_id') or 'MISS'}  "
                f"got={r.get('predicted_top1_id') or 'MISS'}  "
                f"d={r.get('predicted_top1_distance')}"
            )

    print()
    if metrics["precision_at_1"] >= threshold_gate:
        print(f"✓ precision @ 1 ≥ {threshold_gate:.2f} — gate PASSES")
    else:
        print(f"✗ precision @ 1 < {threshold_gate:.2f} — gate FAILS")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval-file", type=Path, default=DEFAULT_EVAL_PATH,
        help=f"Path to JSONL eval set (default: {DEFAULT_EVAL_PATH})",
    )
    parser.add_argument(
        "--threshold-gate", type=float, default=DEFAULT_THRESHOLD_GATE,
        help="precision @ 1 gate; CI fails below this (default: 0.70)",
    )
    parser.add_argument(
        "--hit-threshold", type=float, default=DEFAULT_HIT_THRESHOLD,
        help="cosine distance ≤ this counts as a hit (default: 0.85)",
    )
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help="rows to fetch per query for recall @ k metric (default: 3)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="emit JSON metrics only (for CI consumption)",
    )
    parser.add_argument(
        "--results-out", type=Path, default=None,
        help="write per-record JSONL results to this path",
    )
    args = parser.parse_args(argv)

    if not args.eval_file.exists():
        print(f"error: eval file not found: {args.eval_file}", file=sys.stderr)
        return 2

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("error: DATABASE_URL required", file=sys.stderr)
        return 2

    records = _load_eval(args.eval_file)
    if not args.quiet:
        print(f"Loaded {len(records)} eval records from {args.eval_file}")

    import asyncpg

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        # ivfflat probes — see resolver.py for rationale
        await conn.execute(f"SET ivfflat.probes = {DEFAULT_PROBES}")

        results: list[dict] = []
        for i, rec in enumerate(records, 1):
            # Throttle Voyage calls — free tier is 3 RPM. The previous
            # iteration always made one Voyage call (one embed for the
            # highest-confidence VisualNeed), so spacing-per-record is
            # the right granularity.
            if i > 1 and VOYAGE_THROTTLE_SECONDS > 0:
                await asyncio.sleep(VOYAGE_THROTTLE_SECONDS)
            if not args.quiet:
                print(f"  [{i:2d}/{len(records)}] {rec['id']} ({rec['category']})...",
                      end="", flush=True)
            try:
                r = await _run_one(rec, conn, args.top_k, args.hit_threshold)
                results.append(r)
                if not args.quiet:
                    status = "HIT" if r["predicted_hit"] else "miss"
                    print(f" {status}")
            except Exception as e:  # noqa: BLE001
                print(f" ERROR: {e}", file=sys.stderr)
                results.append(
                    {
                        "eval_id": rec["id"],
                        "category": rec["category"],
                        "subject": rec["subject"],
                        "expected_hit": rec["expected_hit"],
                        "expected_entry_id": rec.get("expected_entry_id"),
                        "predicted_hit": False,
                        "error": str(e),
                    }
                )
    finally:
        await conn.close()

    if args.results_out:
        with args.results_out.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        if not args.quiet:
            print(f"Wrote {len(results)} per-record results to {args.results_out}")

    metrics = _compute_metrics(results)
    _print_report(metrics, results, args.threshold_gate, args.quiet)

    return 0 if metrics["precision_at_1"] >= args.threshold_gate else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
