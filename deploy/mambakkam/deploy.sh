#!/usr/bin/env bash
# =============================================================================
# Mambakkam demo server — deploy script
#
# Syncs code from this machine to Hetzner and restarts the stack.
#
# Usage (from project root):
#   deploy/mambakkam/deploy.sh [sync|restart|logs|status]
#
# Prerequisites:
#   - SSH key loaded: ssh-add ~/.ssh/id_ed25519 (key: 1Lxokf6)
#   - .env.demo present on server at /opt/studybuddy/.env.demo
# =============================================================================

set -euo pipefail

SERVER="root@178.105.160.62"
REMOTE="/opt/studybuddy"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

COMPOSE_REMOTE="docker compose --project-directory . \
  -f docker-compose.yml \
  -f deploy/mambakkam/overrides.yml \
  --env-file .env.demo"

case "${1:-sync}" in

  sync)
    echo "Syncing code to mambakkam..."
    rsync -av --delete \
      --exclude='.git/' \
      --exclude='node_modules/' \
      --exclude='.next/' \
      --exclude='*.pyc' \
      --exclude='__pycache__/' \
      --exclude='venv/' \
      --exclude='backups/' \
      --exclude='content_store_data/' \
      "$REPO/" "$SERVER:$REMOTE/"
    echo "Sync done."
    ;;

  restart)
    echo "Restarting stack on mambakkam..."
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
