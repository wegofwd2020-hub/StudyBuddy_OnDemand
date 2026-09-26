#!/bin/bash
# =============================================================================
# scripts/demo/backup-all-grades-content.sh — backup all grades (8-12) content
#
# Backs up content for grades 8-12 into organized structure:
#   backups/<YYYY-mm-dd_HH-MM>/grade_8/
#   backups/<YYYY-mm-dd_HH-MM>/grade_9/
#   ...
#
# Usage:
#   bash scripts/demo/backup-all-grades-content.sh
#
# Output: backups/<YYYY-mm-dd_HH-MM>/grade_{8,9,10,11,12}/
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-.}"
CONTENT_STORE="${CONTENT_STORE:-$INSTALL_DIR/content_store_data}"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-$INSTALL_DIR/backups}"

# Timestamp for this backup run (used for directory grouping)
TIMESTAMP=$(date -u +'%Y-%m-%d_%H-%M')
BACKUP_RUN_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
log_err() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2; }

log "Starting backup of all grades (8-12)"
log "Backup directory: $BACKUP_RUN_DIR"
log ""

mkdir -p "$BACKUP_RUN_DIR"

TOTAL_SIZE=0
FAILED_GRADES=()

# Backup each grade
for grade in 8 9 10 11 12; do
  GRADE_DIR="$BACKUP_RUN_DIR/grade_$grade"
  mkdir -p "$GRADE_DIR"

  log "Backing up Grade $grade..."

  # Find all curriculum directories for this grade
  G_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g${grade}*" 2>/dev/null || true)

  if [[ -z "$G_DIRS" ]]; then
    log "  WARNING: no content found for grade $grade"
    FAILED_GRADES+=("$grade")
    continue
  fi

  # Create tarball for this grade
  TARBALL="$GRADE_DIR/content.tar.gz"

  if tar -czf "$TARBALL" -C "$CONTENT_STORE/curricula" $(echo "$G_DIRS" | xargs basename -a) 2>/dev/null; then
    SIZE=$(du -h "$TARBALL" | cut -f1)
    TOTAL_SIZE=$((TOTAL_SIZE + $(du -b "$TARBALL" | cut -f1)))
    SHA=$(sha256sum "$TARBALL" | awk '{print $1}')

    log "  ✅ Grade $grade: $TARBALL ($SIZE)"
    log "     SHA256: $SHA"

    # Write manifest for this grade
    echo "{\"grade\": $grade, \"timestamp\": \"$TIMESTAMP\", \"size_bytes\": $(du -b "$TARBALL" | cut -f1), \"sha256\": \"$SHA\", \"file\": \"content.tar.gz\"}" > "$GRADE_DIR/manifest.json"
  else
    log "  ❌ Grade $grade: tar failed"
    FAILED_GRADES+=("$grade")
  fi
done

log ""
log "═════════════════════════════════════════════════════════════════"
log "Backup Summary"
log "═════════════════════════════════════════════════════════════════"
log "Timestamp: $TIMESTAMP"
log "Total size: $(numfmt --to=iec-i --suffix=B $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")"
log ""

if [[ ${#FAILED_GRADES[@]} -eq 0 ]]; then
  log "✅ All grades backed up successfully"
  log ""
  log "Backup structure:"
  find "$BACKUP_RUN_DIR" -type f | sed 's|^|  |'
  exit 0
else
  log "⚠️  Failed grades: ${FAILED_GRADES[*]}"
  exit 1
fi
