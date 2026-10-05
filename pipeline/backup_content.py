"""
pipeline/backup_content.py

Backup the content store to a labelled tarball.

Usage:
    python3 pipeline/backup_content.py
    python3 pipeline/backup_content.py --out-dir /opt/backups
    python3 pipeline/backup_content.py --label myschool --out-dir /opt/backups

Output filename: {label}_{YYYY-MM-DD_HH-MM}.tgz
"""

from __future__ import annotations

import argparse
import os
import sys
import tarfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup the content store")
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Directory to write the tarball into (default: current dir)",
    )
    parser.add_argument(
        "--label",
        default="default",
        help="Label prefix for the tarball name (default: default)",
    )
    args = parser.parse_args()

    store = Path(settings.CONTENT_STORE_PATH)
    if not store.exists():
        print(f"ERROR: CONTENT_STORE_PATH does not exist: {store}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    archive_name = f"{args.label}_{timestamp}.tgz"
    archive_path = out_dir / archive_name

    print(f"Backing up: {store}")
    print(f"       To: {archive_path}")

    file_count = 0
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in sorted(store.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(store.parent))
                file_count += 1

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"Done: {file_count} files, {size_mb:.1f} MB → {archive_path}")


if __name__ == "__main__":
    main()
