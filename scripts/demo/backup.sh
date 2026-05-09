#!/usr/bin/env bash
# =============================================================================
# scripts/demo/backup.sh — daily restic backup for StudyBuddy
#
# Runs from cron at 02:00 UTC (provisioned by scripts/demo/provision.sh).
# Three-step routine:
#   1. pg_dump compressed → /opt/studybuddy/backups/staging/db-latest.dump.gz
#      (always overwritten; restic snapshots the file in step 2 and dedupes
#       blocks-against-blocks across days, so we don't need 30 separate
#       dump files cluttering the disk)
#   2. restic backup → /opt/studybuddy/backups/restic/
#      sources: the staging dump from step 1, /data/content (content store),
#               /opt/studybuddy/.env.demo
#   3. (optional) trigger a Hetzner Cloud snapshot via API if HCLOUD_TOKEN set
#
# Why restic instead of timestamped tarballs / rsync:
#   - Encryption-at-rest (AES-256). pg_dump output is plaintext PII once
#     real users land. A stolen disk image is not immediately readable.
#   - Content-addressed deduplication. The content_store changes by ~few MB
#     per day on average; 30 daily snapshots take ~1.2x the size of one
#     instead of 30x. Same story for pg_dump (most blocks are unchanged).
#   - Per-snapshot `restic check` integrity verification.
#
# Repo lives at $RESTIC_REPO (default: $INSTALL_DIR/backups/restic). Same
# disk as the originals (deliberate — operator chose local-only retention
# for the demo; see Plans/BACKUPS.md residual-risk section).
#
# Password lives at $RESTIC_PASSWORD_FILE (default /etc/restic/studybuddy.password).
# provision.sh generates and prints it once. If lost, the repo is unrecoverable
# (this is a design property of restic, not a bug).
#
# Forget policy:
#   --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --keep-yearly 1
#
# Usage (typically via cron, but manual invocation works):
#   sudo bash /opt/studybuddy/scripts/demo/backup.sh
#
# Exit codes:
#   0 — backup + forget successful (or "nothing to do")
#   1 — pg_dump failed
#   2 — restic backup failed
#   3 — restic forget/prune failed
#   4 — Hetzner snapshot API call failed
#   5 — repo not initialised (run provision.sh)
#   6 — password file missing or unreadable
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
STAGING_DIR="${STAGING_DIR:-$BACKUP_DIR/staging}"
RESTIC_REPO="${RESTIC_REPO:-$BACKUP_DIR/restic}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/etc/restic/studybuddy.password}"
ENV_FILE="${ENV_FILE:-$INSTALL_DIR/.env.demo}"

# Source .env.demo so we have HCLOUD_TOKEN (if set) and POSTGRES_PASSWORD.
# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && set -a && . "$ENV_FILE" && set +a

HOSTNAME_TAG="$(hostname -s)"
SNAPSHOT_TAG="daily"

export RESTIC_REPOSITORY="$RESTIC_REPO"
export RESTIC_PASSWORD_FILE

mkdir -p "$BACKUP_DIR" "$STAGING_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# ── Pre-flight ──────────────────────────────────────────────────────────────
if ! command -v restic >/dev/null 2>&1; then
  log "FATAL: restic not installed. Run scripts/demo/provision.sh."
  exit 5
fi

if [[ ! -r "$RESTIC_PASSWORD_FILE" ]]; then
  log "FATAL: $RESTIC_PASSWORD_FILE missing or unreadable. Run provision.sh."
  exit 6
fi

if [[ ! -f "$RESTIC_REPO/config" ]]; then
  log "FATAL: restic repo not initialised at $RESTIC_REPO."
  log "  Run: RESTIC_REPOSITORY=$RESTIC_REPO RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE restic init"
  exit 5
fi

# ── 1. pg_dump → staging file (overwritten daily) ──────────────────────────
DB_OUT="$STAGING_DIR/db-latest.dump.gz"
log "step 1/3  pg_dump → $DB_OUT"
if docker compose -f "$INSTALL_DIR/docker-compose.yml" \
                 -f "$INSTALL_DIR/docker-compose.demo.yml" \
                 --env-file "$ENV_FILE" \
                 exec -T db \
                 pg_dump -U studybuddy -Fc studybuddy 2>/dev/null \
                 | gzip -9 > "$DB_OUT"; then
  log "  pg_dump OK ($(du -h "$DB_OUT" | cut -f1))"
else
  log "  pg_dump FAILED"
  exit 1
fi

# ── 2. restic backup ───────────────────────────────────────────────────────
log "step 2/3  restic backup → $RESTIC_REPO"

SOURCES=("$DB_OUT")
[[ -d /data/content ]] && SOURCES+=(/data/content)
[[ -f "$ENV_FILE" ]] && SOURCES+=("$ENV_FILE")

log "  sources:"
for src in "${SOURCES[@]}"; do log "    - $src"; done

if ! restic backup \
    --tag "$SNAPSHOT_TAG" \
    --tag "host=$HOSTNAME_TAG" \
    --exclude-caches \
    "${SOURCES[@]}"; then
  log "  restic backup FAILED"
  exit 2
fi

log "  backup OK"

# ── 3. forget — apply retention policy ─────────────────────────────────────
log "step 3/3  restic forget — keep 7d / 4w / 3m / 1y"
if ! restic forget \
    --tag "$SNAPSHOT_TAG" \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 3 \
    --keep-yearly 1; then
  log "  restic forget FAILED"
  exit 3
fi

# ── (Optional) Hetzner snapshot trigger ────────────────────────────────────
# Belt-and-braces: in addition to the local restic repo, take a same-account
# Hetzner snapshot. Same-Hetzner-account, so doesn't help against account
# compromise — but it does give a fast rollback point if the OS itself is
# corrupted (vs. losing only application data, which restic alone protects).
if [[ -n "${HCLOUD_TOKEN:-}" ]] && [[ "$HCLOUD_TOKEN" != "<your-hetzner-cloud-api-token-or-leave-blank>" ]]; then
  log "(optional) Hetzner snapshot trigger"
  SERVER_ID=$(curl -fsS \
    -H "Authorization: Bearer $HCLOUD_TOKEN" \
    "https://api.hetzner.cloud/v1/servers?name=$(hostname -f)" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['servers'][0]['id'] if d.get('servers') else '')")
  if [[ -z "$SERVER_ID" ]]; then
    log "  could not resolve server ID for hostname=$(hostname -f) — skipping"
  else
    if curl -fsS \
      -H "Authorization: Bearer $HCLOUD_TOKEN" \
      -H "Content-Type: application/json" \
      -X POST \
      -d "{\"description\":\"studybuddy-demo-$(date -u +%Y%m%d)\",\"type\":\"snapshot\"}" \
      "https://api.hetzner.cloud/v1/servers/$SERVER_ID/actions/create_image" \
      > /dev/null; then
      log "  snapshot triggered"
    else
      log "  snapshot trigger FAILED"
      exit 4
    fi
  fi
else
  log "(optional) Hetzner snapshot SKIPPED (HCLOUD_TOKEN not set)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
log "current snapshots:"
restic snapshots --compact | tail -10 | sed 's/^/  /'

REPO_SIZE=$(du -sh "$RESTIC_REPO" 2>/dev/null | cut -f1 || echo "?")
log "repo on-disk size: $REPO_SIZE"
log "backup complete."
