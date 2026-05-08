#!/usr/bin/env bash
# =============================================================================
# scripts/demo/backup.sh — daily DB + content-store backup
#
# Runs from cron at 02:00 UTC (provisioned by scripts/demo/provision.sh).
# Three-step routine:
#   1. pg_dump compressed → /opt/studybuddy/backups/db-YYYYMMDD.dump.gz
#   2. rsync content_store → /opt/studybuddy/backups/content-YYYYMMDD/
#   3. (optional) trigger a Hetzner Cloud snapshot via API if HCLOUD_TOKEN set
# Plus retention: prune backups older than RETENTION_DAYS (default 7).
#
# Usage (typically via cron, but manual invocation works):
#   sudo bash /opt/studybuddy/scripts/demo/backup.sh
#
# Cron entry installed by provision.sh:
#   0 2 * * * root cd /opt/studybuddy && bash scripts/demo/backup.sh \
#     >> /var/log/studybuddy-backup.log 2>&1
#
# Exit codes:
#   0 — backup successful (or "nothing to do")
#   1 — pg_dump failed
#   2 — rsync failed
#   3 — Hetzner snapshot API call failed (still exits non-zero so cron emails)
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE_TAG="$(date -u +%Y%m%d)"
ENV_FILE="${ENV_FILE:-$INSTALL_DIR/.env.demo}"

# Source .env.demo so we have HCLOUD_TOKEN (if set) and POSTGRES_PASSWORD
# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && set -a && . "$ENV_FILE" && set +a

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# ── 1. pg_dump ──────────────────────────────────────────────────────────────
DB_OUT="$BACKUP_DIR/db-${DATE_TAG}.dump.gz"
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

# ── 2. content-store rsync ──────────────────────────────────────────────────
CONTENT_OUT="$BACKUP_DIR/content-${DATE_TAG}"
log "step 2/3  content-store rsync → $CONTENT_OUT"
if rsync -a --delete /data/content/ "$CONTENT_OUT/"; then
  log "  rsync OK ($(du -sh "$CONTENT_OUT" | cut -f1))"
else
  log "  rsync FAILED"
  exit 2
fi

# ── 3. Hetzner snapshot trigger (optional) ─────────────────────────────────
if [[ -n "${HCLOUD_TOKEN:-}" ]] && [[ "$HCLOUD_TOKEN" != "<your-hetzner-cloud-api-token-or-leave-blank>" ]]; then
  log "step 3/3  Hetzner snapshot trigger"
  # Get the server ID by hostname (assumes one Hetzner server matches `hostname -f`)
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
      -d "{\"description\":\"studybuddy-demo-${DATE_TAG}\",\"type\":\"snapshot\"}" \
      "https://api.hetzner.cloud/v1/servers/$SERVER_ID/actions/create_image" \
      > /dev/null; then
      log "  snapshot triggered"
    else
      log "  snapshot trigger FAILED — exiting non-zero so cron emails the failure"
      exit 3
    fi
  fi
else
  log "step 3/3  Hetzner snapshot trigger SKIPPED (HCLOUD_TOKEN not set)"
fi

# ── Retention prune ─────────────────────────────────────────────────────────
log "retention prune — removing backups older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -maxdepth 1 -name 'db-*.dump.gz'  -mtime +"$RETENTION_DAYS" -print -delete
find "$BACKUP_DIR" -maxdepth 1 -name 'content-*' -type d -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} +

log "backup complete. Current artefacts:"
ls -lh "$BACKUP_DIR" | tail -n +2 | awk '{printf "  %-40s  %s\n", $9, $5}'
