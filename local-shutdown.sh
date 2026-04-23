#!/usr/bin/env bash
# =============================================================================
# StudyBuddy OnDemand — Local Shutdown Script
#
# Companion to local-setup.sh. Stops the Docker Compose stack cleanly.
#
# By default, delegates the dependency-safe graceful drain to dev_stop.sh
# (which stops Celery → Web → API → PgBouncer → Redis BGSAVE → Postgres in
# the right order). Falls back to a plain `docker compose down` if
# dev_stop.sh is not present.
#
# Usage:
#   ./local-shutdown.sh             # graceful shutdown; data preserved
#   ./local-shutdown.sh --force     # skip Celery drain; stop immediately
#   ./local-shutdown.sh --wipe      # stop AND delete all volumes (data loss)
#   ./local-shutdown.sh --status    # show what's running (delegates to docker compose ps)
#   ./local-shutdown.sh --help      # show this help
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Colour helpers — matched to local-setup.sh
# ---------------------------------------------------------------------------
bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"
red="\033[0;31m"; cyan="\033[0;36m"; reset="\033[0m"

info()    { echo -e "${cyan}[info]${reset}  $*"; }
ok()      { echo -e "${green}[ok]${reset}    $*"; }
warn()    { echo -e "${yellow}[warn]${reset}  $*"; }
error()   { echo -e "${red}[error]${reset} $*" >&2; }
sep()     { echo -e "${cyan}$(printf '─%.0s' {1..70})${reset}"; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
FORCE=false
WIPE=false
CMD="down"

for arg in "$@"; do
  case "$arg" in
    --force)  FORCE=true ;;
    --wipe)   WIPE=true ;;
    --status) CMD="status" ;;
    --help|-h)
      sed -n '3,17p' "$0"
      exit 0
      ;;
    *)
      error "Unknown option: $arg  (use --help for usage)"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Resolve docker compose command (v2 plugin or standalone)
# ---------------------------------------------------------------------------
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
else
  error "Docker Compose not found. Install: https://docs.docker.com/compose/install/"
  exit 1
fi

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
sep
echo -e "${bold}  StudyBuddy OnDemand — Local Shutdown${reset}"
echo -e "  Root : $REPO_ROOT"
echo -e "  Date : $(date '+%Y-%m-%d %H:%M:%S')"
sep

# ---------------------------------------------------------------------------
# Status-only mode
# ---------------------------------------------------------------------------
if [[ "$CMD" == "status" ]]; then
  $COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" ps
  exit 0
fi

# ---------------------------------------------------------------------------
# Wipe confirmation
# ---------------------------------------------------------------------------
if [[ "$WIPE" == "true" ]]; then
  echo ""
  warn "─── WIPE requested ────────────────────────────────────────────"
  warn "This will DELETE all database data, Redis state, and content."
  warn "The content_store bind-mount under ./data is NOT touched."
  echo ""
  read -r -p "  Are you sure? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }
  echo ""
fi

# ---------------------------------------------------------------------------
# Graceful shutdown — prefer dev_stop.sh when present
# ---------------------------------------------------------------------------
if [[ -x "$REPO_ROOT/dev_stop.sh" ]]; then
  info "Delegating graceful drain to dev_stop.sh..."
  if [[ "$FORCE" == "true" ]]; then
    "$REPO_ROOT/dev_stop.sh" --force
  else
    "$REPO_ROOT/dev_stop.sh"
  fi
else
  warn "dev_stop.sh not found or not executable — falling back to 'docker compose down'"
  $COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" down --remove-orphans
fi

# ---------------------------------------------------------------------------
# Optional volume wipe
# ---------------------------------------------------------------------------
if [[ "$WIPE" == "true" ]]; then
  echo ""
  info "Removing named volumes (postgres_data, redis_data)..."
  $COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" down -v --remove-orphans 2>/dev/null || true
  ok "Volumes wiped. Next ./local-setup.sh run will bootstrap a fresh DB."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
sep
echo -e "${bold}  Shutdown complete.${reset}"
sep
echo ""
if [[ "$WIPE" == "true" ]]; then
  echo -e "  ${cyan}To start fresh:${reset}      ./local-setup.sh"
else
  echo -e "  ${cyan}To restart:${reset}           ./local-setup.sh"
  echo -e "  ${cyan}To wipe + restart:${reset}    ./local-shutdown.sh --wipe && ./local-setup.sh"
fi
echo ""
