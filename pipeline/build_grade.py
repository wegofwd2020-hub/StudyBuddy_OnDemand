"""
pipeline/build_grade.py

CLI to build all content for a full grade (all subjects, all units).

Usage:
  python pipeline/build_grade.py --grade 8 --lang en,fr,es [--force] [--dry-run] [--year 2026]

Steps:
  1. Load data/grade{N}_stem.json for the unit list.
  2. Compute curriculum_id = default-{year}-g{grade}.
  3. Upsert curriculum row in DB (via asyncpg).
  4. For each subject → for each unit → build_unit() for each lang.
  5. Track total tokens/cost; abort if SpendCapExceeded.
  6. After each subject: create/update content_subject_versions row.
  7. Emit per-unit structured logs + final run summary.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Allow running as a script from the repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

log = logging.getLogger("pipeline.build_grade")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _upsert_curriculum(conn: object, curriculum_id: str, grade: int, year: int) -> None:
    """Insert curriculum row if not already present."""
    await conn.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
        VALUES ($1, $2, $3, $4, true)
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        curriculum_id,
        grade,
        year,
        f"Default Grade {grade} STEM Curriculum ({year})",
    )


async def _upsert_curriculum_units(
    conn: object,
    curriculum_id: str,
    subject_id: str,
    units: list[dict],
) -> None:
    """Upsert curriculum_units rows for a subject."""
    for sort_order, unit in enumerate(units):
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, description, has_lab, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (unit_id, curriculum_id) DO NOTHING
            """,
            unit["unit_id"],
            curriculum_id,
            subject_id,
            unit.get("title", unit["unit_id"]),
            unit.get("description", ""),
            unit.get("has_lab", False),
            sort_order,
        )


async def _upsert_content_subject_version(
    conn: object,
    curriculum_id: str,
    subject: str,
    subject_name: str,
    alex_warnings: int,
    auto_approve: bool,
    pipeline_run_id: str,
    provider: str = "anthropic",
) -> None:
    """Create or update content_subject_versions record."""
    status = "pending"

    if auto_approve:
        status = "published"
        published_at = _now_iso()
    else:
        published_at = None

    # Determine next version number
    row = await conn.fetchrow(
        """
        SELECT COALESCE(MAX(version_number), 0) as max_ver
        FROM content_subject_versions
        WHERE curriculum_id = $1 AND subject = $2
        """,
        curriculum_id,
        subject,
    )
    next_version = (row["max_ver"] or 0) + 1

    await conn.execute(
        """
        INSERT INTO content_subject_versions
            (curriculum_id, subject, subject_name, version_number, status, alex_warnings_count,
             provider, generated_at, published_at, pipeline_run_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, $9)
        ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE
            SET status = EXCLUDED.status,
                subject_name = EXCLUDED.subject_name,
                alex_warnings_count = EXCLUDED.alex_warnings_count,
                provider = EXCLUDED.provider,
                published_at = EXCLUDED.published_at,
                pipeline_run_id = EXCLUDED.pipeline_run_id
        """,
        curriculum_id,
        subject,
        subject_name,
        next_version,
        status,
        alex_warnings,
        provider,
        published_at,
        pipeline_run_id,
    )


def run_grade(
    grade: int,
    langs: list[str],
    year: int = 2026,
    force: bool = False,
    dry_run: bool = False,
    providers: list[str] | None = None,
) -> dict:
    """
    Build all content for a grade. Returns a run summary dict.

    Args:
        providers: List of provider IDs to run, e.g. ["anthropic", "openai"].
                   Each provider gets its own content_subject_versions row so
                   outputs land in the review queue for side-by-side comparison.
                   Defaults to [config.DEFAULT_PROVIDER] when not given.
    """
    from pipeline.config import settings as config
    from pipeline.build_unit import build_unit, SpendCapExceeded
    from pipeline.providers import get_provider

    start_ms = time.monotonic()
    pipeline_run_id = f"run-g{grade}-{int(start_ms)}"

    # Resolve provider list — default to the single configured default provider
    resolved_providers = providers or [getattr(config, "DEFAULT_PROVIDER", "anthropic")]
    is_comparison = len(resolved_providers) > 1

    # ── Load grade data ───────────────────────────────────────────────────────
    data_path = os.path.join(_REPO_ROOT, "data", f"grade{grade}_stem.json")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Grade data not found: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        grade_data = json.load(f)

    curriculum_id = f"default-{year}-g{grade}"
    subjects = grade_data.get("subjects", [])

    # ── DB connection (optional — skip if DATABASE_URL not set) ───────────────
    db_conn = None
    if config.DATABASE_URL and not dry_run:
        try:
            import asyncpg  # type: ignore

            async def _get_conn():
                return await asyncpg.connect(config.DATABASE_URL)

            db_conn = asyncio.get_event_loop().run_until_complete(_get_conn())
            asyncio.get_event_loop().run_until_complete(
                _upsert_curriculum(db_conn, curriculum_id, grade, year)
            )
        except Exception as exc:
            log.warning("db_connect_skip: %s", exc)
            db_conn = None

    # ── Build units ───────────────────────────────────────────────────────────
    total_tokens = 0
    total_cost = 0.0
    total_units = 0
    succeeded = 0
    failed = 0
    all_failed = False

    if is_comparison:
        log.info(
            "comparison_build_start grade=%d providers=%s",
            grade, resolved_providers,
        )

    for subject in subjects:
        subject_id = subject.get("subject_id", "unknown")
        subject_name = subject.get("name", subject_id)
        units = subject.get("units", [])

        # Upsert units into DB once — provider-agnostic schema
        if db_conn and not dry_run:
            try:
                asyncio.get_event_loop().run_until_complete(
                    _upsert_curriculum_units(db_conn, curriculum_id, subject_id, units)
                )
            except Exception as exc:
                log.warning("db_upsert_units_skip: %s", exc)

        # Run each provider in sequence; each gets its own version row
        for provider_id in resolved_providers:
            subject_alex_warnings = 0

            # Instantiate provider once per subject×provider (keeps connection open across units)
            try:
                llm_provider = get_provider(provider_id, config) if not dry_run else None
            except RuntimeError as exc:
                log.error("provider_init_failed provider=%s error=%s", provider_id, exc)
                failed += len(units) * len(langs)
                continue

            for unit in units:
                unit_id = unit["unit_id"]
                if provider_id == resolved_providers[0]:
                    total_units += 1

                unit_data = {
                    **unit,
                    "subject": subject_id,
                    "grade": grade,
                }

                for lang in langs:
                    try:
                        result = build_unit(
                            curriculum_id=curriculum_id,
                            unit_id=unit_id,
                            unit_data=unit_data,
                            lang=lang,
                            config=config,
                            force=force,
                            dry_run=dry_run,
                            provider_id=provider_id,
                            provider=llm_provider,
                        )

                        total_tokens += result.get("tokens_used", 0)
                        total_cost += result.get("cost_usd", 0.0)
                        subject_alex_warnings += result.get("alex_warnings", 0)

                        if result["status"] in ("ok", "skipped", "dry_run"):
                            succeeded += 1
                        else:
                            failed += 1

                        # Per-unit structured log
                        print(json.dumps({
                            "event": "unit_complete",
                            "unit_id": unit_id,
                            "lang": lang,
                            "provider": provider_id,
                            "tokens": result.get("tokens_used", 0),
                            "cost_usd": round(result.get("cost_usd", 0.0), 6),
                            "duration_ms": result.get("duration_ms", 0),
                            "alex_warnings": result.get("alex_warnings", 0),
                            "status": result["status"],
                        }))

                    except SpendCapExceeded as exc:
                        log.error("spend_cap_exceeded provider=%s: %s", provider_id, exc)
                        all_failed = True
                        break

                if all_failed:
                    break

            if all_failed:
                log.error("aborting_due_to_spend_cap")
                break

            # ── Create/update content_subject_versions in DB (per provider) ──
            if db_conn and not dry_run:
                try:
                    asyncio.get_event_loop().run_until_complete(
                        _upsert_content_subject_version(
                            db_conn,
                            curriculum_id,
                            subject_id,
                            subject_name,
                            subject_alex_warnings,
                            config.REVIEW_AUTO_APPROVE,
                            pipeline_run_id,
                            provider=provider_id,
                        )
                    )
                    log.info(
                        "content_subject_version_created curriculum=%s subject=%s provider=%s warnings=%d",
                        curriculum_id, subject_id, provider_id, subject_alex_warnings,
                    )
                except Exception as exc:
                    log.warning("db_csv_upsert_skip: %s", exc)

        if all_failed:
            break

    if db_conn:
        try:
            asyncio.get_event_loop().run_until_complete(db_conn.close())
        except Exception:
            pass

    duration_ms = int((time.monotonic() - start_ms) * 1000)

    summary = {
        "event": "run_complete",
        "grade": grade,
        "langs": langs,
        "providers": resolved_providers,
        "curriculum_id": curriculum_id,
        "total_units": total_units,
        "succeeded": succeeded,
        "failed": failed,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "duration_ms": duration_ms,
    }
    print(json.dumps(summary))

    # ── Push metrics to Prometheus Pushgateway (best-effort) ──────────────────
    _push_pipeline_metrics(
        pipeline_run_id=pipeline_run_id,
        grade=grade,
        succeeded=succeeded,
        failed=failed,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        duration_ms=duration_ms,
        config=config,
    )

    return summary


def _push_pipeline_metrics(
    *,
    pipeline_run_id: str,
    grade: int,
    succeeded: int,
    failed: int,
    total_tokens: int,
    total_cost_usd: float,
    duration_ms: int,
    config: object,
) -> None:
    """
    Push per-run metrics to Prometheus Pushgateway.

    Silently skipped if:
    - prometheus_client is not installed, or
    - PUSHGATEWAY_URL is not configured.
    """
    pushgateway_url = getattr(config, "PUSHGATEWAY_URL", None)
    if not pushgateway_url:
        log.debug("pushgateway_skip: PUSHGATEWAY_URL not set")
        return

    try:
        from prometheus_client import (
            CollectorRegistry,
            Counter,
            Gauge,
            push_to_gateway,
        )

        registry = CollectorRegistry()

        units_succeeded = Gauge(
            "sb_pipeline_units_succeeded_total",
            "Units successfully generated in this pipeline run",
            registry=registry,
        )
        units_failed = Gauge(
            "sb_pipeline_units_failed_total",
            "Units that failed generation in this pipeline run",
            registry=registry,
        )
        tokens_used = Gauge(
            "sb_pipeline_tokens_used_total",
            "Total Claude tokens consumed in this pipeline run",
            registry=registry,
        )
        cost_usd = Gauge(
            "sb_pipeline_cost_usd",
            "Estimated USD cost of this pipeline run",
            registry=registry,
        )
        duration = Gauge(
            "sb_pipeline_duration_ms",
            "Pipeline run wall-clock duration in milliseconds",
            registry=registry,
        )

        units_succeeded.set(succeeded)
        units_failed.set(failed)
        tokens_used.set(total_tokens)
        cost_usd.set(total_cost_usd)
        duration.set(duration_ms)

        grouping_key = {"grade": str(grade), "run_id": pipeline_run_id}
        push_to_gateway(pushgateway_url, job="studybuddy_pipeline", grouping_key=grouping_key, registry=registry)
        log.info("pushgateway_push_ok run_id=%s", pipeline_run_id)

    except ImportError:
        log.debug("pushgateway_skip: prometheus_client not installed")
    except Exception as exc:
        log.warning("pushgateway_push_failed: %s", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Build all content for a grade.")
    parser.add_argument("--grade", type=int, required=True, help="Grade number (5–12)")
    parser.add_argument("--lang", default="en", help="Comma-separated language codes e.g. en,fr,es")
    parser.add_argument("--year", type=int, default=2026, help="Curriculum year (default: 2026)")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already built")
    parser.add_argument("--dry-run", action="store_true", help="Log what would be done without calling the LLM")
    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "Comma-separated provider IDs e.g. anthropic,openai. "
            "Multiple providers run sequentially; each gets its own version row "
            "in the review queue for side-by-side comparison. "
            "Default: config.DEFAULT_PROVIDER (anthropic)."
        ),
    )
    args = parser.parse_args()

    langs = [l.strip() for l in args.lang.split(",") if l.strip()]
    providers = [p.strip() for p in args.provider.split(",") if p.strip()] if args.provider else None
    run_grade(
        grade=args.grade,
        langs=langs,
        year=args.year,
        force=args.force,
        dry_run=args.dry_run,
        providers=providers,
    )


if __name__ == "__main__":
    main()
