#!/bin/bash
# =============================================================================
# scripts/pull-backups-local.sh — pull Grade 9 backups from demo to local
#
# Downloads all Grade 9 backup files from demo server to local machine.
# Uses rsync for efficient transfer (only pulls new/changed files).
#
# Usage:
#   bash scripts/pull-backups-local.sh
#   ./scripts/pull-backups-local.sh ~/backups-grade9  # custom local dir
#
# Requires:
#   - SSH key auth to root@178.105.160.62 (should already work)
#   - rsync installed locally
# =============================================================================

set -euo pipefail

DEMO_HOST="178.105.160.62"
DEMO_USER="root"
DEMO_BACKUP_DIR="/opt/studybuddy/backups/grade9"

# Local destination directory (default: ~/backups-grade9)
LOCAL_BACKUP_DIR="${1:-$HOMEDocuments/code/projects/AIStuff/backups-grade9}"

log() { echo "[$(date +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Syncing Grade 9 backups from demo server"
log "  Remote: $DEMO_USER@$DEMO_HOST:$DEMO_BACKUP_DIR"
log "  Local:  $LOCAL_BACKUP_DIR"

mkdir -p "$LOCAL_BACKUP_DIR"

# Use rsync to pull backups (efficient — only pulls new/changed files)
# -a: archive (preserves permissions, timestamps)
# -v: verbose
# -z: compress during transfer
# --progress: show progress
# --delete: remove local files not on remote (optional — comment out to keep old files)
if rsync -avz --progress \
    "$DEMO_USER@$DEMO_HOST:$DEMO_BACKUP_DIR/" \
    "$LOCAL_BACKUP_DIR/"; then
  log "✅ Backup sync complete"
  log ""
  log "Local backups:"
  ls -lh "$LOCAL_BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{print "  " $5 "\t" $9}' || log "  (none yet)"
  log ""
  log "Total size:"
  du -sh "$LOCAL_BACKUP_DIR" | awk '{print "  " $1}'
else
  log "❌ Sync failed"
  exit 1
fi
