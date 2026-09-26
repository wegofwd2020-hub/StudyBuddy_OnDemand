#!/usr/bin/env bash
# =============================================================================
# scripts/demo/restore-grade9-content.sh — restore Grade 9 curriculum content
#
# Restores Grade 9 content from a backup tarball created by
# backup-grade9-content.sh
#
# Usage:
#   bash scripts/demo/restore-grade9-content.sh backups/grade9/grade9-content-*.tar.gz
#
# WARNING: This OVERWRITES existing Grade 9 content in content_store_data/curricula/
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-.}"
CONTENT_STORE="${CONTENT_STORE:-$INSTALL_DIR/content_store_data}"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-tarball>"
  echo ""
  echo "Example:"
  echo "  $0 backups/grade9/grade9-content-20260926-124500.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [[ ! -f "$BACKUP_FILE" ]]; then
  log "ERROR: backup file not found: $BACKUP_FILE"
  exit 1
fi

log "Restoring Grade 9 content from $BACKUP_FILE"
log "Destination: $CONTENT_STORE/curricula/"
log ""
log "WARNING: This will overwrite existing Grade 9 content."
log "Press Ctrl+C to cancel, or Enter to proceed..."
read -r

# Create backup of current G9 content before overwriting (safety measure)
CURRENT_G9_DIRS=$(find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g9*" 2>/dev/null || true)
if [[ -n "$CURRENT_G9_DIRS" ]]; then
  SAFETY_BACKUP="$CONTENT_STORE/curricula/.grade9-pre-restore-$(date -u +%Y%m%d-%H%M%S).tar.gz"
  log "Creating safety backup of current G9 content at $SAFETY_BACKUP"
  tar -czf "$SAFETY_BACKUP" -C "$CONTENT_STORE/curricula" $(echo "$CURRENT_G9_DIRS" | xargs basename -a) 2>/dev/null || log "WARNING: safety backup failed"
fi

# Extract restore backup
log "Extracting $BACKUP_FILE to $CONTENT_STORE/curricula/"
if tar -xzf "$BACKUP_FILE" -C "$CONTENT_STORE/curricula/"; then
  log "Restore complete."
  log ""
  log "Restored directories:"
  find "$CONTENT_STORE/curricula" -maxdepth 1 -type d -name "default-2026-g9*" | sed 's/^/  /'
  exit 0
else
  log "ERROR: tar extraction failed"
  exit 1
fi
