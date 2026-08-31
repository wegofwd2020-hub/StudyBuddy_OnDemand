#!/usr/bin/env bash
# =============================================================================
# scripts/demo/disk-check.sh — disk headroom guard for the demo VPS
#
# Written after 2026-08-31, when the box filled to 100% (0 bytes free) and the
# next deploy failed inside `migrate` with psycopg2 DiskFull while building an
# index. Because `migrate` gates the app services, the whole stack stayed down
# and the demo served 502 until someone looked. Nothing reported the disk
# filling; the deploy failure was the first signal, and by then it was an outage.
#
# The cause was not the database. It was 34.4 GB of Docker BUILD CACHE plus
# 6.4 GB of dangling images — pure accumulation, nothing referenced by any
# container. Pruning both took the box from 100% to 23%.
#
# So this script does two things, in order of how safe they are:
#
#   1. RECLAIM, quietly. Above RECLAIM_PCT, prune build cache and dangling
#      images. Both are caches by definition — nothing a running or stopped
#      container depends on — so this is the one remediation safe to automate.
#      It is deliberately NOT `docker image prune -a`: that would delete the
#      SHA-tagged prior releases this box keeps as rollback targets, trading a
#      one-command rollback for a few hundred MB.
#
#   2. ALERT, loudly, if reclaiming was not enough. Above WARN_PCT or CRIT_PCT
#      an email goes out, because the remaining space is then held by something
#      that needs a human decision.
#
# Email rather than a log line: this box's cron comments reference Promtail →
# Loki, but promtail/loki/grafana are all `inactive` here, so a log-based alert
# would be written to a file nobody reads. The app's SMTP credentials are in
# .env.demo and demonstrably work (backup notifications ship through them), so
# the mail goes out the same proven path rather than a second one nobody tests.
#
# Deliberately quiet when healthy. A cron job that mails on success trains you
# to filter it, and a filtered alert is the same as no alert.
#
# Exit codes:
#   0 — below the warning threshold (after any reclaim)
#   1 — at or above WARN_PCT, alert sent
#   2 — at or above CRIT_PCT, alert sent
#   3 — could not read disk usage (the check itself is broken)
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
MOUNT="${DISK_CHECK_MOUNT:-/}"

# Reclaim before anyone is told: caches refill, and waking a human for something
# a machine can safely undo is how alerts get ignored.
RECLAIM_PCT="${DISK_RECLAIM_PCT:-70}"
WARN_PCT="${DISK_WARN_PCT:-80}"
CRIT_PCT="${DISK_CRIT_PCT:-90}"

# One alert per level per day. Without this an hourly cron mails 24 times for
# one problem and the mailbox becomes the thing you filter.
STATE_DIR="${DISK_CHECK_STATE_DIR:-/var/lib/studybuddy-diskcheck}"

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] disk-check: $*"; }

usage_pct() {
  df -P "$MOUNT" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}'
}

human_state() {
  df -h "$MOUNT" 2>/dev/null | awk 'NR==2 {printf "%s used of %s (%s), %s free", $3, $2, $5, $4}'
}

# ── Send an alert email through the app's own SMTP path ──────────────────────
#
# Runs inside the api container: it already holds the SMTP settings and has been
# sending mail in production, so this reuses a path that is exercised daily
# instead of introducing a second, untested one on the host.
send_alert() {
  local level="$1" pct="$2" detail="$3"
  local to
  to="$(grep -oP '^ALERT_EMAIL=\K.*' "$INSTALL_DIR/.env.demo" 2>/dev/null || true)"
  [ -z "$to" ] && to="$(grep -oP '^SMTP_USER=\K.*' "$INSTALL_DIR/.env.demo" 2>/dev/null || true)"
  if [ -z "$to" ]; then
    log "ERROR: no ALERT_EMAIL or SMTP_USER in .env.demo — cannot send the alert"
    return 1
  fi

  cd "$INSTALL_DIR"
  docker compose -f docker-compose.yml -f docker-compose.demo.yml --env-file .env.demo \
    exec -T api python - "$to" "$level" "$pct" "$detail" <<'PY' 2>&1 | tail -2
import smtplib, ssl, sys
from email.message import EmailMessage
from config import settings  # backend/config.py, top level — NOT src.config

to, level, pct, detail = sys.argv[1:5]
msg = EmailMessage()
msg["Subject"] = f"[StudyBuddy demo] {level}: disk at {pct}%"
msg["From"] = getattr(settings, "EMAIL_FROM", None) or settings.SMTP_USER
msg["To"] = to
msg.set_content(
    f"The demo VPS is at {pct}% disk.\n\n"
    f"{detail}\n\n"
    "Build cache and dangling images are pruned automatically before this fires,\n"
    "so the remaining space is held by something that needs a decision:\n"
    "  docker system df                 # what is actually using it\n"
    "  du -sh /var/lib/docker/* | sort -rh | head\n"
    "  docker images                    # SHA-tagged releases are rollback targets\n\n"
    "Context: on 2026-08-31 this reached 100% unnoticed and the next deploy failed\n"
    "inside `migrate` with DiskFull, taking the demo down until someone looked.\n"
)
ctx = ssl.create_default_context()
with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT)) as s:
    s.starttls(context=ctx)
    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    s.send_message(msg)
print("alert email sent to", to)
PY
}

# One alert per level per calendar day.
should_alert() {
  local level="$1"
  local stamp="$STATE_DIR/${level}.$(date -u +%Y%m%d)"
  mkdir -p "$STATE_DIR"
  [ -e "$stamp" ] && return 1
  : > "$stamp"
  # Keep the directory from growing without bound.
  find "$STATE_DIR" -type f -mtime +14 -delete 2>/dev/null || true
  return 0
}

# ── Main ─────────────────────────────────────────────────────────────────────

PCT="$(usage_pct || true)"
if ! [[ "$PCT" =~ ^[0-9]+$ ]]; then
  log "ERROR: could not read usage for $MOUNT — the check itself is broken"
  exit 3
fi

log "$MOUNT at ${PCT}% — $(human_state)"

if [ "$PCT" -ge "$RECLAIM_PCT" ]; then
  log "at or above ${RECLAIM_PCT}% — reclaiming caches before alerting"
  # Build cache first: it was 34 GB of the 2026-08-31 outage on its own.
  docker builder prune -af 2>&1 | tail -1 | sed "s/^/[$(ts)] disk-check:   /" || true
  # Dangling (untagged) images only. NOT -a, which would remove the SHA-tagged
  # prior releases kept for rollback.
  docker image prune -f 2>&1 | tail -1 | sed "s/^/[$(ts)] disk-check:   /" || true

  PCT="$(usage_pct || echo "$PCT")"
  log "after reclaim: ${PCT}% — $(human_state)"
fi

if [ "$PCT" -ge "$CRIT_PCT" ]; then
  log "CRITICAL: ${PCT}% >= ${CRIT_PCT}% after reclaim"
  if should_alert critical; then
    send_alert "CRITICAL" "$PCT" "$(human_state)" || log "alert send failed"
  else
    log "critical alert already sent today — not repeating"
  fi
  exit 2
fi

if [ "$PCT" -ge "$WARN_PCT" ]; then
  log "WARNING: ${PCT}% >= ${WARN_PCT}% after reclaim"
  if should_alert warning; then
    send_alert "WARNING" "$PCT" "$(human_state)" || log "alert send failed"
  else
    log "warning alert already sent today — not repeating"
  fi
  exit 1
fi

log "healthy"
exit 0
