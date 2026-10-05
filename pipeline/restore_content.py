"""
pipeline/restore_content.py

Restore the content store from a tarball created by backup_content.py.

Usage:
    python3 pipeline/restore_content.py default_2026-10-05_14-30.tgz
    python3 pipeline/restore_content.py backup.tgz --target /custom/store --force

By default the target is CONTENT_STORE_PATH from pipeline config.
Without --force the script aborts if the target directory already has content.
"""

from __future__ import annotations

import argparse
import os
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore the content store from a tarball")
    parser.add_argument("archive", help="Path to the .tgz backup file")
    parser.add_argument(
        "--target",
        default=None,
        help="Restore destination (default: CONTENT_STORE_PATH from config)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing content without prompting",
    )
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.exists():
        print(f"ERROR: archive not found: {archive}", file=sys.stderr)
        sys.exit(1)
    if not tarfile.is_tarfile(archive):
        print(f"ERROR: not a valid tarball: {archive}", file=sys.stderr)
        sys.exit(1)

    # Determine the parent of CONTENT_STORE_PATH — the archive was created
    # with paths relative to store.parent so extraction lands correctly.
    store = Path(args.target or settings.CONTENT_STORE_PATH)
    extract_root = store.parent

    if store.exists() and any(store.iterdir()):
        if not args.force:
            answer = input(
                f"Target {store} already has content. Overwrite? [y/N] "
            ).strip().lower()
            if answer != "y":
                print("Aborted.")
                sys.exit(0)

    extract_root.mkdir(parents=True, exist_ok=True)
    print(f"Restoring: {archive}")
    print(f"      To:  {store}")

    def _safe_members(tf: tarfile.TarFile, root: Path):
        """Yield only members whose resolved path stays inside root."""
        root_resolved = root.resolve()
        for member in tf.getmembers():
            member_path = (root / member.name).resolve()
            try:
                member_path.relative_to(root_resolved)
            except ValueError:
                print(f"SKIPPED (path traversal): {member.name}", file=sys.stderr)
                continue
            yield member

    file_count = 0
    with tarfile.open(archive, "r:gz") as tar:
        safe = list(_safe_members(tar, extract_root))
        for member in safe:
            tar.extract(member, path=extract_root)
            if member.isfile():
                file_count += 1

    print(f"Done: {file_count} files restored to {store}")


if __name__ == "__main__":
    main()
