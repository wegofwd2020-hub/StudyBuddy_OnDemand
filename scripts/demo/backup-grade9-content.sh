#!/usr/bin/env bash
# =============================================================================
# scripts/demo/backup-grade9-content.sh — backup Grade 9 curriculum content
#
# Backs up all Grade 9 content from content_store_data/curricula/default-2026-g9*
# to a timestamped tarball in backups/grade9/
#
# Usage:
#   bash scripts/demo/backup-grade9-content.sh
#
# Output: backups/grade9/grade9-content-YYYYMMDD-HHMMSS.tar.gz
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-.}"
CONTENT_STORE="${CONTENT_STORE:-$INSTALL_DIR/content_store_data}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups/grade9}"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/grade9-content-$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Backing up Grade 9 content from $CONTENT_STORE/curricula/default-2026-g9*"

# Find all G9 curriculum directories
G9_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g9*" 2>/dev/null || true)

if [[ -z "$G9_DIRS" ]]; then
  log "WARNING: no Grade 9 content found at $CONTENT_STORE/curricula/default-2026-g9*"
  exit 1
fi

log "Found directories:"
echo "$G9_DIRS" | sed 's/^/  /'

# Tar all G9 directories
if tar -czf "$BACKUP_FILE" -C "$CONTENT_STORE/curricula" $(echo "$G9_DIRS" | xargs basename -a); then
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  log "Backup complete: $BACKUP_FILE ($SIZE)"
  log "sha256: $(sha256sum "$BACKUP_FILE" | awk '{print $1}')"
else
  log "ERROR: tar failed"
  exit 1
fi

# Phase 1: Local retention policy — keep last 7 daily backups
log "Applying retention policy: keep last 7 daily backups"
KEEP_DAILY=${BACKUP_KEEP_DAYS:-7}
BACKUP_FILES=$(find "$BACKUP_DIR" -maxdepth 1 -name "grade9-content-*.tar.gz" -type f | sort -r)
COUNT=0
echo "$BACKUP_FILES" | while read -r file; do
  COUNT=$((COUNT + 1))
  if [[ $COUNT -gt $KEEP_DAILY ]]; then
    log "  Deleting old backup (exceeds retention): $(basename "$file")"
    rm -f "$file"
  fi
done

log "Retention policy applied. Current backups:"
find "$BACKUP_DIR" -maxdepth 1 -name "grade9-content-*.tar.gz" -type f | wc -l | sed 's/^/  Count: /'

exit 0
