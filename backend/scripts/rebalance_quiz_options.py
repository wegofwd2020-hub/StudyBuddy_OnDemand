"""
backend/scripts/rebalance_quiz_options.py

Balance the correct-answer position in every stored quiz set (#779).

    python scripts/rebalance_quiz_options.py                 # dry-run (default)
    python scripts/rebalance_quiz_options.py --commit        # write changes
    python scripts/rebalance_quiz_options.py --root /path    # another store

On the demo `pipeline` is NOT inside the api image; mount it for the run:

    sudo /usr/bin/docker compose -f docker-compose.yml -f docker-compose.demo.yml \\
      --env-file .env.demo run --rm -v /opt/studybuddy/pipeline:/pipeline \\
      api python /app/scripts/rebalance_quiz_options.py

Every file is checked before it is written: same question ids, same option
texts, and the answer key resolves each question to the same correct TEXT. A
violation stops the run before that file is touched (files already written were
each verified). Placeholder content is skipped (pitfall #36). Teacher overrides
live in the database and are not touched.

After a --commit on a live store, clear the Redis `content:*` keys as
scripts/demo/sync-content.sh does (never FLUSHDB).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from src.admin.authoring_service import ensure_pipeline_path  # noqa: E402

ensure_pipeline_path()

from pipeline.quiz_options import balance_options  # noqa: E402

from src.content.service import _parse_quiz_answer_key  # noqa: E402

_QUIZ_FILE = re.compile(r"^quiz_set_(\d+)_([a-z]{2,3})\.json$")
_PLACEHOLDER_MODEL = "dev-placeholder"


class RebalanceInvariantError(Exception):
    """A rebalanced body would not grade identically to the original."""


@dataclass
class Report:
    files_seen: int = 0
    files_changed: int = 0
    skipped_placeholder: int = 0
    before: Counter = field(default_factory=Counter)
    after: Counter = field(default_factory=Counter)


def _correct_texts(body: dict, cid: str, unit: str, set_number: int, lang: str) -> dict[str, str]:
    key = _parse_quiz_answer_key(body, cid, unit, set_number, lang)
    by_id = {q.get("question_id"): q for q in body.get("questions", [])}
    return {
        qid: " ".join((by_id[qid]["options"][entry["index"]].get("text") or "").split())
        for qid, entry in key.items()
    }


def _option_texts(body: dict) -> dict[str, list[str]]:
    return {
        q.get("question_id"): sorted((o.get("text") or "") for o in q.get("options", []))
        for q in body.get("questions", [])
    }


def _verify(
    original: dict, balanced: dict, cid: str, unit: str, set_number: int, lang: str, path: str
) -> None:
    if _option_texts(original) != _option_texts(balanced):
        raise RebalanceInvariantError(f"option texts changed: {path}")
    if _correct_texts(original, cid, unit, set_number, lang) != _correct_texts(
        balanced, cid, unit, set_number, lang
    ):
        raise RebalanceInvariantError(f"correct answer changed: {path}")


def _write_atomic(path: str, body: dict) -> None:
    tmp = f"{path}.rebalance.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def rebalance(root: str, *, commit: bool) -> Report:
    report = Report()
    curricula = os.path.join(root, "curricula")
    if not os.path.isdir(curricula):
        return report

    for cid in sorted(os.listdir(curricula)):
        cdir = os.path.join(curricula, cid)
        if not os.path.isdir(cdir):
            continue
        for unit in sorted(os.listdir(cdir)):
            udir = os.path.join(cdir, unit)
            if not os.path.isdir(udir):
                continue
            for name in sorted(os.listdir(udir)):
                match = _QUIZ_FILE.match(name)
                if not match:
                    continue
                path = os.path.join(udir, name)
                with open(path, encoding="utf-8") as f:
                    original = json.load(f)
                if original.get("model") == _PLACEHOLDER_MODEL:
                    report.skipped_placeholder += 1
                    continue

                report.files_seen += 1
                set_number, lang = int(match.group(1)), match.group(2)
                balanced = balance_options(original, unit_id=unit, lang=lang)
                report.before.update(q.get("correct_option") for q in original.get("questions", []))
                report.after.update(q.get("correct_option") for q in balanced.get("questions", []))

                if balanced == original:
                    continue
                _verify(original, balanced, cid, unit, set_number, lang, path)
                report.files_changed += 1
                if commit:
                    _write_atomic(path, balanced)
    return report


def _share(counter: Counter) -> str:
    total = sum(counter.values()) or 1
    return "  ".join(f"{k}={counter[k]} ({100 * counter[k] / total:.1f}%)" for k in "ABCD")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument(
        "--root", default=None, help="content store root (default: settings.CONTENT_STORE_PATH)"
    )
    parser.add_argument("--commit", action="store_true", help="write changes (default: dry-run)")
    args = parser.parse_args(argv)

    root = args.root
    if root is None:
        from config import settings

        root = settings.CONTENT_STORE_PATH

    try:
        report = rebalance(root, commit=args.commit)
    except RebalanceInvariantError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2

    mode = "COMMIT" if args.commit else "DRY-RUN"
    print(f"[{mode}] root={root}")
    print(
        f"  quiz files seen: {report.files_seen}  changed: {report.files_changed}  placeholder skipped: {report.skipped_placeholder}"
    )
    print(f"  before: {_share(report.before)}")
    print(f"  after:  {_share(report.after)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
