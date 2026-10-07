#!/usr/bin/env bash
# =============================================================================
# StudyBuddy server (77.42.13.139) — deploy script
#
# Syncs code from vaganam and restarts the stack.
#
# Usage (from project root on vaganam):
#   deploy/studybuddy/deploy.sh [sync|restart|deploy|logs|status]
#
# Prerequisites:
#   - SSH access: ssh studybuddy (configured in ~/.ssh/config)
#   - .env.demo present on server at /opt/studybuddy/.env.demo
# =============================================================================

set -euo pipefail

CURRENT_HOST="$(hostname)"
EXPECTED_HOST="vaganam"
if [[ "$CURRENT_HOST" != "$EXPECTED_HOST" ]]; then
  echo "ERROR: wrong machine. Expected '$EXPECTED_HOST', got '$CURRENT_HOST'."
  echo "       Deploy is pushed FROM vaganam, not run on the server."
  exit 1
fi
echo "Host: $CURRENT_HOST  →  pushing to studybuddy (77.42.13.139)"

SERVER="root@77.42.13.139"
REMOTE="/opt/studybuddy"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

COMPOSE_REMOTE="docker compose --project-directory . \
  -f docker-compose.yml \
  -f deploy/studybuddy/overrides.yml \
  --env-file .env.demo"

case "${1:-deploy}" in

  sync)
    echo "Syncing code to studybuddy server..."
    rsync -av --delete \
      --exclude='.git/' \
      --exclude='node_modules/' \
      --exclude='.next/' \
      --exclude='*.pyc' \
      --exclude='__pycache__/' \
      --exclude='venv/' \
      --exclude='backups/' \
      --exclude='content_store_data/' \
      --exclude='.env*' \
      "$REPO/" "$SERVER:$REMOTE/"
    echo "Sync done."
    ;;

  restart)
    echo "Pulling images and restarting stack..."
    ssh "$SERVER" "cd $REMOTE && $COMPOSE_REMOTE pull && $COMPOSE_REMOTE up -d"
    ;;

  deploy)
    "$0" sync
    "$0" restart
    ;;

  logs)
    ssh "$SERVER" "cd $REMOTE && $COMPOSE_REMOTE logs -f ${2:-api}"
    ;;

  status)
    ssh "$SERVER" "cd $REMOTE && $COMPOSE_REMOTE ps"
    ;;

  *)
    echo "Usage: $0 [sync|restart|deploy|logs [service]|status]"
    exit 1
    ;;

esac
