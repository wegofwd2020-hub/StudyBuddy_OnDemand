"""
tests/test_check_coverage_thresholds.py

Unit tests for scripts/check_coverage_thresholds.py.

All tests use temporary files — no filesystem side effects.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add the scripts directory to sys.path so we can import it directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from check_coverage_thresholds import DEFAULT_THRESHOLD, THRESHOLDS, _bucket, main


# ── _bucket() routing ─────────────────────────────────────────────────────────


def test_bucket_auth():
    assert _bucket("src/auth/router.py") == "src/auth"


def test_bucket_subscription():
    assert _bucket("src/subscription/router.py") == "src/subscription"


def test_bucket_school_subscription_longer_prefix_wins():
    """src/school/subscription must win over a hypothetical src/school prefix."""
    assert _bucket("src/school/subscription_service.py") == "src/school/subscription"


def test_bucket_content():
    assert _bucket("src/content/router.py") == "src/content"


def test_bucket_progress():
    assert _bucket("src/progress/router.py") == "src/progress"


def test_bucket_unmatched_falls_to_default():
    assert _bucket("src/analytics/router.py") == "default"


def test_bucket_core_falls_to_default():
    assert _bucket("src/core/cache.py") == "default"


# ── main() — helpers ──────────────────────────────────────────────────────────


def _make_report(tmp_path: Path, file_entries: dict[str, tuple[int, int]]) -> Path:
    """
    Build a minimal coverage.json.

    file_entries: {filepath: (covered_lines, num_statements)}
    """
    files = {}
    for filepath, (covered, stmts) in file_entries.items():
        pct = 100.0 * covered / stmts if stmts else 0
        files[filepath] = {
            "summary": {
                "covered_lines": covered,
                "num_statements": stmts,
                "percent_covered": pct,
            }
        }
    report_path = tmp_path / "coverage.json"
    report_path.write_text(json.dumps({"files": files}))
    return report_path


# ── main() tests ──────────────────────────────────────────────────────────────


def test_missing_file_returns_1(tmp_path: Path):
    rc = main(str(tmp_path / "nonexistent.json"))
    assert rc == 1


def test_all_modules_above_threshold_returns_0(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/auth/router.py": (92, 100),          # 92% ≥ 90
            "src/subscription/router.py": (91, 100),   # 91% ≥ 90
            "src/school/subscription_service.py": (90, 100),  # 90% = 90
            "src/content/router.py": (86, 100),        # 86% ≥ 85
            "src/progress/router.py": (80, 100),       # 80% = 80
            "src/analytics/router.py": (80, 100),      # 80% = default 80
        },
    )
    assert main(str(report)) == 0


def test_auth_below_threshold_returns_1(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/auth/router.py": (89, 100),   # 89% < 90
        },
    )
    assert main(str(report)) == 1


def test_subscription_below_threshold_returns_1(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/subscription/router.py": (85, 100),  # 85% < 90
        },
    )
    assert main(str(report)) == 1


def test_school_subscription_below_threshold_returns_1(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/school/subscription_service.py": (89, 100),  # 89% < 90
        },
    )
    assert main(str(report)) == 1


def test_content_below_threshold_returns_1(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/content/router.py": (84, 100),  # 84% < 85
        },
    )
    assert main(str(report)) == 1


def test_default_module_below_threshold_returns_1(tmp_path: Path):
    report = _make_report(
        tmp_path,
        {
            "src/analytics/router.py": (79, 100),  # 79% < 80
        },
    )
    assert main(str(report)) == 1


def test_empty_module_prefix_skipped(tmp_path: Path):
    """A prefix with no matching files must not cause a false failure."""
    report = _make_report(
        tmp_path,
        {
            # Only analytics files — auth/subscription/etc. have no files at all.
            "src/analytics/router.py": (80, 100),
        },
    )
    assert main(str(report)) == 0


def test_aggregate_across_multiple_files_in_module(tmp_path: Path):
    """
    Coverage is aggregated across all files in the module, not per-file.
    80 + 100 covered out of 100 + 100 = 90% aggregate → passes auth threshold.
    """
    report = _make_report(
        tmp_path,
        {
            "src/auth/router.py": (80, 100),   # 80% individually
            "src/auth/service.py": (100, 100), # 100% individually
            # aggregate = 180/200 = 90% ≥ 90 threshold
        },
    )
    assert main(str(report)) == 0


def test_aggregate_below_threshold_despite_one_perfect_file(tmp_path: Path):
    """
    One 100% file cannot mask a very low companion — aggregate must still fail.
    100 + 79 = 179/200 = 89.5% < 90% auth threshold.
    """
    report = _make_report(
        tmp_path,
        {
            "src/auth/router.py": (100, 100),  # 100%
            "src/auth/service.py": (79, 100),  # 79%
            # aggregate = 179/200 = 89.5% < 90
        },
    )
    assert main(str(report)) == 1


def test_zero_statement_file_skipped(tmp_path: Path):
    """Files with num_statements=0 (e.g. __init__.py) must not cause a ZeroDivisionError."""
    report = _make_report(
        tmp_path,
        {
            "src/auth/__init__.py": (0, 0),
            "src/auth/router.py": (91, 100),
        },
    )
    assert main(str(report)) == 0
