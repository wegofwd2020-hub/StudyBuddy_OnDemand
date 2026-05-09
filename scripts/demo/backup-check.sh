#!/usr/bin/env bash
# =============================================================================
# scripts/demo/backup-check.sh — weekly restic integrity check + prune
#
# Runs from cron at 03:00 UTC on Sundays (one hour after Sunday's daily
# backup at 02:00, so they don't compete for the repo lock).
#
# Two-step routine:
#   1. restic check --read-data-subset 5%
#      Reads 5% of pack files to catch silent bit-rot. Full 100% audit on
#      a daily disk takes too long; 5% weekly cycles every pack within
#      ~5 months on average.
#   2. restic prune --max-unused 5%
#      Reclaims disk that daily forgets have marked unreferenced.
#
# Output streams to /var/log/studybuddy-backup.log via cron, so Promtail
# picks it up alongside the daily-backup output. Loki query:
#   {job="backups", which="studybuddy"} |~ "(?i)check|prune|error"
#
# Exit codes match scripts/launch/backup-check.sh exactly so a generic
# "BackupCheckFailed" alert can fire on either site.
#
# Exit codes:
#   0 — check + prune successful
#   1 — restic check failed (POSSIBLE BIT-ROT — investigate immediately)
#   2 — restic prune failed
#   3 — repo not initialised
#   4 — password file unreadable
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
RESTIC_REPO="${RESTIC_REPO:-$BACKUP_DIR/restic}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/etc/restic/studybuddy.password}"

export RESTIC_REPOSITORY="$RESTIC_REPO"
export RESTIC_PASSWORD_FILE

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

[[ -r "$RESTIC_PASSWORD_FILE" ]] || { log "FATAL: $RESTIC_PASSWORD_FILE unreadable"; exit 4; }
[[ -f "$RESTIC_REPO/config" ]]   || { log "FATAL: repo not at $RESTIC_REPO"; exit 3; }

log "step 1/2  restic check --read-data-subset 5%"
if ! restic check --read-data-subset 5%; then
  log "  CHECK FAILED — possible bit-rot or repo corruption."
  log "  Investigate immediately. Recent snapshots may not be restorable."
  log "  Try: restic check --read-data-subset 100%   (slower; full audit)"
  exit 1
fi
log "  check OK"

log "step 2/2  restic prune --max-unused 5%"
if ! restic prune --max-unused 5%; then
  log "  prune FAILED"
  exit 2
fi
log "  prune OK"

REPO_SIZE=$(du -sh "$RESTIC_REPO" 2>/dev/null | cut -f1 || echo "?")
log "weekly check complete. repo on-disk size: $REPO_SIZE"
