#!/usr/bin/env bash
# =============================================================================
# StudyBuddy OnDemand — Local Setup Script
#
# Bootstraps a complete local development environment using Docker Compose.
# Run this once to get started; use `docker compose up` for subsequent starts.
#
# Usage:
#   ./local-setup.sh            # first-time setup and start
#   ./local-setup.sh --build    # force rebuild of all images
#   ./local-setup.sh --reset    # wipe volumes + rebuild from scratch
#   ./local-setup.sh --stop     # stop all running services
#   ./local-setup.sh --status   # show service status
#   ./local-setup.sh --logs     # tail logs for all services
#   ./local-setup.sh --help     # show this help
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$REPO_ROOT/.env"
WEB_ENV_FILE="$REPO_ROOT/web/.env.local"

# ---------------------------------------------------------------------------
# Colour helpers
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
BUILD_FLAG=""
RESET=false
CMD="up"

for arg in "$@"; do
  case "$arg" in
    --build)  BUILD_FLAG="--build" ;;
    --reset)  RESET=true ;;
    --stop)   CMD="stop" ;;
    --status) CMD="status" ;;
    --logs)   CMD="logs" ;;
    --help|-h)
      sed -n '3,15p' "$0"
      exit 0
      ;;
    *)
      error "Unknown option: $arg  (use --help for usage)"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
sep
echo -e "${bold}  StudyBuddy OnDemand — Local Setup${reset}"
echo -e "  Root : $REPO_ROOT"
echo -e "  Date : $(date '+%Y-%m-%d %H:%M:%S')"
sep

# ---------------------------------------------------------------------------
# Handle non-setup commands early
# ---------------------------------------------------------------------------
case "$CMD" in
  stop)
    info "Stopping all services..."
    docker compose -f "$REPO_ROOT/docker-compose.yml" down
    ok "All services stopped."
    exit 0
    ;;
  status)
    docker compose -f "$REPO_ROOT/docker-compose.yml" ps
    exit 0
    ;;
  logs)
    docker compose -f "$REPO_ROOT/docker-compose.yml" logs -f --tail=50
    exit 0
    ;;
esac

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
echo ""
info "Checking prerequisites..."

check_command() {
  if command -v "$1" &>/dev/null; then
    ok "$1 found ($(command -v "$1"))"
  else
    error "$1 is required but not installed."
    echo "  Install guide: $2"
    exit 1
  fi
}

check_command docker   "https://docs.docker.com/get-docker/"
check_command python3  "https://www.python.org/downloads/"

# Check Docker daemon is running
if ! docker info &>/dev/null; then
  error "Docker daemon is not running. Please start Docker and retry."
  exit 1
fi
ok "Docker daemon is running"

# Check docker compose (v2 plugin or standalone)
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
  ok "Docker Compose v2 found"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
  ok "docker-compose standalone found"
else
  error "Docker Compose not found. Install: https://docs.docker.com/compose/install/"
  exit 1
fi

# ---------------------------------------------------------------------------
# Reset (wipe volumes) if requested
# ---------------------------------------------------------------------------
if [[ "$RESET" == "true" ]]; then
  warn "─── RESET requested ───────────────────────────────────────────"
  warn "This will DELETE all database data, Redis state, and content."
  echo ""
  read -r -p "  Are you sure? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }
  echo ""
  info "Stopping services and removing volumes..."
  $COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" down -v --remove-orphans 2>/dev/null || true
  ok "Volumes wiped."
  BUILD_FLAG="--build"
fi

# ---------------------------------------------------------------------------
# Generate random secrets helper
# ---------------------------------------------------------------------------
gen_secret() {
  python3 -c "import secrets; print(secrets.token_urlsafe(40))"
}

# ---------------------------------------------------------------------------
# Bootstrap .env (backend + compose secrets)
# ---------------------------------------------------------------------------
echo ""
info "Checking .env..."

if [[ ! -f "$ENV_FILE" ]]; then
  info "No .env found — generating one with random secrets..."

  POSTGRES_PASSWORD="$(gen_secret)"
  REDIS_PASSWORD="$(gen_secret)"
  JWT_SECRET="$(gen_secret)"
  ADMIN_JWT_SECRET="$(gen_secret)"
  METRICS_TOKEN="$(gen_secret)"

  cat > "$ENV_FILE" <<EOF
# =============================================================================
# StudyBuddy OnDemand — Environment Configuration
# Generated by local-setup.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# NEVER commit this file to git.
# =============================================================================

# ── Application ───────────────────────────────────────────────────────────────
APP_ENV=development
APP_VERSION=0.1.0
DEBUG=false
LOG_LEVEL=INFO

# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_POOL_MIN=5
DATABASE_POOL_MAX=20

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_MAX_CONNECTIONS=10

# ── JWT (student / teacher — minimum 32 chars) ────────────────────────────────
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ── Admin JWT (MUST differ from JWT_SECRET) ───────────────────────────────────
ADMIN_JWT_SECRET=${ADMIN_JWT_SECRET}
ADMIN_JWT_EXPIRE_MINUTES=60

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# ── Observability ─────────────────────────────────────────────────────────────
METRICS_TOKEN=${METRICS_TOKEN}

# ── Content store ─────────────────────────────────────────────────────────────
CONTENT_STORE_PATH=/data/content

# ── Sentry (leave blank to disable) ──────────────────────────────────────────
SENTRY_DSN=

# =============================================================================
# REQUIRED — Fill in your Auth0 credentials before logging in as a student or
# teacher. The admin console (localhost:3000/admin) works without Auth0.
#
# Steps:
#  1. Sign up at https://auth0.com (free tier is sufficient for local dev)
#  2. Create a Regular Web Application → AUTH0_STUDENT_CLIENT_ID
#  3. Create a Regular Web Application → AUTH0_TEACHER_CLIENT_ID
#  4. Create a Machine-to-Machine app, authorise the Auth0 Management API
#     with scopes: read:users  update:users  delete:users
#     → AUTH0_MGMT_CLIENT_ID + AUTH0_MGMT_CLIENT_SECRET
#  5. Note your tenant domain   → AUTH0_DOMAIN
# =============================================================================
AUTH0_DOMAIN=YOUR_TENANT.us.auth0.com
AUTH0_JWKS_URL=https://YOUR_TENANT.us.auth0.com/.well-known/jwks.json
AUTH0_STUDENT_CLIENT_ID=REPLACE_ME
AUTH0_TEACHER_CLIENT_ID=REPLACE_ME
AUTH0_MGMT_API_URL=https://YOUR_TENANT.us.auth0.com/api/v2
AUTH0_MGMT_CLIENT_ID=REPLACE_ME
AUTH0_MGMT_CLIENT_SECRET=REPLACE_ME

# =============================================================================
# OPTIONAL — Stripe (leave blank to disable payments locally)
#
# Steps:
#  1. Sign up at https://stripe.com and get test-mode keys
#  2. Install Stripe CLI: https://stripe.com/docs/stripe-cli
#  3. Run: docker compose --profile stripe up stripe-cli
#     (forwards webhooks from Stripe to localhost:8000)
# =============================================================================
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_MONTHLY_ID=
STRIPE_PRICE_ANNUAL_ID=

# =============================================================================
# OPTIONAL — Anthropic API key (only needed to run the content pipeline)
#
# Run pipeline with:
#   docker compose run --rm pipeline python seed_default.py --year 2026
#   docker compose run --rm pipeline python build_grade.py --grade 8 --lang en
# =============================================================================
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6
MAX_PIPELINE_COST_USD=50
EOF

  ok ".env generated at $ENV_FILE"
  echo ""
  warn "┌──────────────────────────────────────────────────────────────────┐"
  warn "│  ACTION REQUIRED before student/teacher login works:            │"
  warn "│  Edit .env and fill in your Auth0 credentials.                  │"
  warn "│  The admin console at localhost:3000/admin works immediately.   │"
  warn "└──────────────────────────────────────────────────────────────────┘"
  echo ""
else
  ok ".env already exists — skipping generation"
fi

# ---------------------------------------------------------------------------
# Bootstrap web/.env.local
# ---------------------------------------------------------------------------
echo ""
info "Checking web/.env.local..."

if [[ ! -f "$WEB_ENV_FILE" ]]; then
  info "No web/.env.local found — generating from example..."

  AUTH0_SECRET="$(gen_secret)"

  # Read Auth0 domain from .env if already set
  AUTH0_DOMAIN_VAL="$(grep '^AUTH0_DOMAIN=' "$ENV_FILE" | cut -d= -f2 || echo 'YOUR_TENANT.us.auth0.com')"

  cat > "$WEB_ENV_FILE" <<EOF
# =============================================================================
# StudyBuddy OnDemand — Next.js Web Frontend Environment
# Generated by local-setup.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# NEVER commit this file to git.
# =============================================================================

# ── Auth0 (must match the tenant in root .env) ────────────────────────────────
AUTH0_SECRET=${AUTH0_SECRET}
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://${AUTH0_DOMAIN_VAL}
AUTH0_CLIENT_ID=REPLACE_ME
AUTH0_CLIENT_SECRET=REPLACE_ME

# ── Backend API ───────────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# ── CDN (local dev: serve files directly from backend) ───────────────────────
NEXT_PUBLIC_CDN_URL=http://localhost:8000

# ── Stripe (publishable key only — secret key is in root .env) ───────────────
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_

# ── Sentry (leave blank to disable) ──────────────────────────────────────────
NEXT_PUBLIC_SENTRY_DSN=
EOF

  ok "web/.env.local generated"
  warn "Fill in AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET in web/.env.local"
else
  ok "web/.env.local already exists — skipping generation"
fi

# ---------------------------------------------------------------------------
# Create local content store directory (also created as Docker volume,
# but useful to have on host for direct pipeline access)
# ---------------------------------------------------------------------------
mkdir -p "$REPO_ROOT/data/content_store"
ok "Local content store directory ready: $REPO_ROOT/data/content_store"

# ---------------------------------------------------------------------------
# Build and start services
# ---------------------------------------------------------------------------
echo ""
sep
info "Building and starting services..."
echo ""
echo -e "  This pulls/builds images for the first time — may take a few minutes."
echo ""

$COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" up -d $BUILD_FLAG \
  --remove-orphans \
  db redis pgbouncer

info "Infrastructure up — waiting 5 s for PostgreSQL to stabilise..."
sleep 5

# Run migrations
info "Running database migrations..."
$COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" run --rm migrate
ok "Migrations complete"

# Start application services
info "Starting application services..."
$COMPOSE_CMD -f "$REPO_ROOT/docker-compose.yml" up -d $BUILD_FLAG \
  api celery-worker celery-pipeline celery-beat web

# ---------------------------------------------------------------------------
# Health check loop
# ---------------------------------------------------------------------------
echo ""
info "Waiting for API to become healthy..."
MAX_WAIT=60
WAIT=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  if [[ $WAIT -ge $MAX_WAIT ]]; then
    error "API did not become healthy within ${MAX_WAIT}s."
    echo ""
    echo "  Check logs with:  docker compose logs api"
    exit 1
  fi
  sleep 3
  WAIT=$((WAIT + 3))
done
ok "API is healthy"

# ---------------------------------------------------------------------------
# Done — print service URLs
# ---------------------------------------------------------------------------
echo ""
sep
echo -e "${bold}  All services are running!${reset}"
sep
echo ""
echo -e "  ${green}Web app${reset}         →  http://localhost:3000"
echo -e "  ${green}Admin console${reset}   →  http://localhost:3000/admin/login"
echo -e "  ${green}API (Swagger)${reset}   →  http://localhost:8000/api/docs"
echo -e "  ${green}API health${reset}      →  http://localhost:8000/health"
echo -e "  ${green}Metrics${reset}         →  http://localhost:8000/metrics  (token-protected)"
echo ""
echo -e "  ${cyan}Useful commands:${reset}"
echo -e "    docker compose logs -f api          # tail API logs"
echo -e "    docker compose logs -f web          # tail web logs"
echo -e "    docker compose ps                   # service status"
echo -e "    docker compose down                 # stop everything"
echo -e "    docker compose down -v              # stop + wipe all data"
echo ""
echo -e "  ${cyan}Run content pipeline:${reset}"
echo -e "    docker compose run --rm pipeline python seed_default.py --year 2026"
echo -e "    docker compose run --rm pipeline python build_grade.py --grade 8 --lang en"
echo ""
echo -e "  ${cyan}Stripe webhooks (optional):${reset}"
echo -e "    docker compose --profile stripe up stripe-cli"
echo ""
sep
