#!/usr/bin/env bash
# =============================================================================
# Vaganam local dev stack
#
# Usage (from anywhere):
#   deploy/vaganam/start.sh [up|down|reset|logs|seed|test-api|test-e2e|test]
#
# API  → http://localhost:8001
# Web  → http://localhost:3000
# =============================================================================

set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

COMPOSE="docker compose --project-directory . \
  -f docker-compose.yml \
  -f deploy/vaganam/overrides.yml"

case "${1:-up}" in

  up)
    $COMPOSE up -d
    echo ""
    echo "Vaganam stack up"
    echo "  API  → http://localhost:8001/api/docs"
    echo "  Web  → http://localhost:3000"
    echo ""
    echo "  Seed (first run): deploy/vaganam/start.sh seed"
    ;;

  down)
    $COMPOSE down
    ;;

  reset)
    echo "This will delete ALL local volumes (DB + Redis data)."
    read -r -p "Continue? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    $COMPOSE down -v
    ;;

  logs)
    $COMPOSE logs -f "${2:-api}"
    ;;

  seed)
    $COMPOSE exec api python scripts/seed_vaganam.py
    ;;

  test-api)
    # Runs pytest inside the api container against an isolated test DB.
    # The studybuddy_test DB is created alongside studybuddy by postgres init.
    # NEVER pass -e TEST_DB_URL= here — that's only needed for alembic (pitfall #37).
    $COMPOSE exec \
      -e TEST_DB_URL="postgresql://studybuddy:${POSTGRES_PASSWORD:-studybuddy_dev}@db:5432/studybuddy_test" \
      api python -m pytest tests/ -v
    ;;

  test-e2e)
    cd web
    BASE_URL=http://localhost:3000 \
    NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1 \
      npx playwright test
    ;;

  test)
    "$0" test-api
    "$0" test-e2e
    ;;

  *)
    echo "Usage: $0 [up|down|reset|logs [service]|seed|test-api|test-e2e|test]"
    exit 1
    ;;

esac
