#!/bin/bash
# =============================================================================
# scripts/pull-backups-local.sh — pull all grade backups from demo to local
#
# Downloads all grade backup files from demo server to local machine.
# Backs up: content.tar.gz, schema.sql, manifest.json, metadata.json
# Uses rsync for efficient transfer (only pulls new/changed files).
#
# Phase 3 structure:
#   backups/
#     2026-09-26_HH-MM/
#       metadata.json
#       grade_8/
#         content.tar.gz
#         schema.sql
#         manifest.json
#       grade_9/
#       ... (grade 10-12)
#
# Usage:
#   bash scripts/pull-backups-local.sh
#   ./scripts/pull-backups-local.sh ~/backups-all-grades  # custom local dir
#
# Requires:
#   - SSH key auth to root@178.105.160.62 (should already work)
#   - rsync installed locally
# =============================================================================

set -euo pipefail

DEMO_HOST="178.105.160.62"
DEMO_USER="root"
DEMO_BACKUP_DIR="/opt/studybuddy/backups"

# Local destination directory (default: ~/backups-all-grades)
LOCAL_BACKUP_DIR="${1:-$HOME/backups-all-grades}"

log() { echo "[$(date +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Syncing all grade backups from demo server"
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
  log "Local backup structure:"
  find "$LOCAL_BACKUP_DIR" -maxdepth 3 -type f | sort | sed 's|^|  |' || log "  (none yet)"
  log ""
  log "Total size:"
  du -sh "$LOCAL_BACKUP_DIR" | awk '{print "  " $1}'
else
  log "❌ Sync failed"
  exit 1
fi
