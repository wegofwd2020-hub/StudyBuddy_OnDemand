#!/usr/bin/env bash
# =============================================================================
# scripts/demo/vm-localhost-bootstrap.sh
#
# Bring StudyBuddy up on a fresh Linux VM as a LOCALHOST MIRROR of the
# Saturday demo stack. No domain, no TLS, no Cloudflare, no Auth0/Stripe/
# SMTP accounts required — same container shape as Saturday (docker-compose.yml
# + docker-compose.demo.yml), just stubbed externals and localhost URLs.
#
# Companion to scripts/demo/provision.sh (which is for the production
# Hetzner second-tenant box). This script DOES NOT touch host nginx, host
# SSL certs, restic, or cron — it's a developer/test bootstrap.
#
# Run on the destination VM (Debian or Ubuntu — derivatives like Mint
# auto-detected) as a sudo-capable NON-root user.
#
#   # Path A — pull pre-built images from GHCR (matches Saturday verbatim;
#   #         needs a GitHub PAT with read:packages scope):
#   GHCR_PAT=ghp_xxxxx bash vm-localhost-bootstrap.sh
#
#   # Path B — build images locally (no GHCR auth needed; needs working
#   #         Docker daemon DNS):
#   IMAGE_STRATEGY=build bash vm-localhost-bootstrap.sh
#
#   # Optional: also rsync content from the old machine in the same run.
#   OLD_HOST=siva@old-box-ip OLD_REPO_DIR=/path/to/StudyBuddy_OnDemand \
#     GHCR_PAT=ghp_xxxxx bash vm-localhost-bootstrap.sh
#
# Env vars (all optional except where noted):
#   REPO_URL          default https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand.git
#   REPO_BRANCH       default main
#   INSTALL_DIR       default /opt/studybuddy
#   IMAGE_STRATEGY    pull | build         (default pull)
#   GHCR_USER         default wegofwd2020-hub
#   GHCR_PAT          REQUIRED if IMAGE_STRATEGY=pull
#   OLD_HOST          user@host for content rsync; blank skips Step 8
#   OLD_REPO_DIR      path to old-machine repo root; required if OLD_HOST set
#   LOG_FILE          where to write the install log
#                     (default /tmp/studybuddy-bootstrap-<timestamp>.log)
#
# Install log:
#   Every step start, success, and failure is written to the log file.
#   On failure, the script exits non-zero and prints the log path.
#   The log captures all command output (stdout + stderr) with ANSI codes
#   stripped, plus structured STEP_START / STEP_OK / STEP_FAIL markers.
#
# Steps:
#   1/8  Install Docker, git, rsync
#   2/8  Clone repo
#   3/8  Image strategy (GHCR login OR Docker-DNS sanity check)
#   4/8  Generate .env.demo + .env + web/.env.local + compose overrides
#   5/8  Content store directories
#   6/8  Hydrate /opt/studybuddy/web from prebuilt image (pull strategy only)
#   7/8  docker compose pull + up -d + migrations + seed
#   8/8  (optional) rsync content from OLD_HOST
#
# Exit codes:
#   0   bootstrap complete
#   1   fatal error (failing step name written to log)
#   2   must NOT be run as root (uses sudo internally)
#   3   missing required env var
# =============================================================================

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
IMAGE_STRATEGY="${IMAGE_STRATEGY:-pull}"
GHCR_USER="${GHCR_USER:-wegofwd2020-hub}"
GHCR_PAT="${GHCR_PAT:-}"
OLD_HOST="${OLD_HOST:-}"
OLD_REPO_DIR="${OLD_REPO_DIR:-}"

# ── Install log setup ──────────────────────────────────────────────────────
# Single log file per run. Capture every step start/end/fail plus all
# command output. ANSI color codes are stripped from the log copy so it
# stays grep-friendly; the terminal still sees colored output.
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_FILE:-/tmp/studybuddy-bootstrap-${TIMESTAMP}.log}"
mkdir -p "$(dirname "$LOG_FILE")"

# Mirror stdout + stderr to LOG_FILE (with ANSI stripped) AND the terminal.
# `sed -u` keeps the log updating in real-time without waiting for buffer flush.
exec > >(tee >(sed -u 's/\x1b\[[0-9;]*[mGKHF]//g' >> "$LOG_FILE")) 2>&1

# Track current step name so the ERR trap knows what failed.
CURRENT_STEP="preflight"
STEP_STARTED_AT=""

# Wall-clock log helper (printed only to the log copy; terminal already has it).
_log_only() {
  printf '%s\n' "$*" | sed -u 's/\x1b\[[0-9;]*[mGKHF]//g' >> "$LOG_FILE"
}

# ── Helpers ────────────────────────────────────────────────────────────────
bold=$'\033[1m'; green=$'\033[0;32m'; yellow=$'\033[0;33m'; red=$'\033[0;31m'; reset=$'\033[0m'
info()  { echo -e "${green}[bootstrap]${reset}  $*"; }
warn()  { echo -e "${yellow}[warn]${reset}       $*"; }
fail()  { echo -e "${red}[FAIL]${reset}       $*" >&2; exit 1; }

step() {
  CURRENT_STEP="$*"
  STEP_STARTED_AT="$(date -u +%H:%M:%SZ)"
  echo ""
  echo -e "${bold}── ${CURRENT_STEP} ──${reset}"
  _log_only "STEP_START [${STEP_STARTED_AT}] ${CURRENT_STEP}"
}

step_ok() {
  local now; now="$(date -u +%H:%M:%SZ)"
  _log_only "STEP_OK    [${now}] ${CURRENT_STEP}"
  echo -e "${green}  ✓ step OK${reset}"
}

# ERR trap — fires on any command failure under set -e. Logs the failing
# step name + exit code, points to the log, and exits non-zero.
on_error() {
  local rc=$?
  local now; now="$(date -u +%H:%M:%SZ)"
  _log_only "STEP_FAIL  [${now}] ${CURRENT_STEP} (exit $rc)"
  echo ""
  echo -e "${red}════════════════════════════════════════════════════════════════════${reset}" >&2
  echo -e "${red}✘ FATAL: step '${CURRENT_STEP}' failed (exit $rc)${reset}" >&2
  echo -e "  full install log: ${LOG_FILE}" >&2
  echo -e "  last 25 log lines:" >&2
  tail -n 25 "$LOG_FILE" | sed 's/^/    /' >&2
  echo -e "${red}════════════════════════════════════════════════════════════════════${reset}" >&2
  exit "$rc"
}
trap on_error ERR

# Banner
_log_only ""
_log_only "================================================================"
_log_only "StudyBuddy localhost-mirror bootstrap"
_log_only "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
_log_only "host:    $(hostname)"
_log_only "user:    ${USER}"
_log_only "strategy: ${IMAGE_STRATEGY}"
_log_only "================================================================"
info "install log: ${LOG_FILE}"

# ── Preflight ──────────────────────────────────────────────────────────────
step "preflight  Validate config"
if [[ $EUID -eq 0 ]]; then
  echo "Do NOT run this as root. Run as your normal user; the script will sudo where needed."
  exit 2
fi
if ! command -v sudo >/dev/null 2>&1; then
  fail "sudo not installed. Install sudo and add your user to the sudoers group first."
fi
if [[ "$IMAGE_STRATEGY" != "pull" && "$IMAGE_STRATEGY" != "build" ]]; then
  fail "IMAGE_STRATEGY must be 'pull' or 'build' (got '$IMAGE_STRATEGY')"
fi
if [[ "$IMAGE_STRATEGY" == "pull" && -z "$GHCR_PAT" ]]; then
  echo "IMAGE_STRATEGY=pull requires GHCR_PAT to be set." >&2
  echo "Generate a PAT at https://github.com/settings/tokens with read:packages scope, then:" >&2
  echo "    GHCR_PAT=ghp_xxxxx bash $0" >&2
  echo "Or use IMAGE_STRATEGY=build to build images locally." >&2
  exit 3
fi
if [[ -n "$OLD_HOST" && -z "$OLD_REPO_DIR" ]]; then
  fail "OLD_HOST set but OLD_REPO_DIR is empty. Set OLD_REPO_DIR to the absolute path of the repo on the old machine."
fi
info "preflight green — IMAGE_STRATEGY=${IMAGE_STRATEGY}, INSTALL_DIR=${INSTALL_DIR}"
step_ok

# ── 1/8  Install Docker, git, rsync ────────────────────────────────────────
step "1/8  Install Docker, git, rsync"
if ! command -v docker >/dev/null 2>&1; then
  info "installing Docker Engine + Compose v2 + git + rsync"
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg git rsync

  sudo install -m 0755 -d /etc/apt/keyrings

  # Map derivatives (Mint, Pop!_OS, KDE Neon, etc.) to their upstream
  # Ubuntu/Debian repo, since Docker only ships repos for the two parent
  # distros. UBUNTU_CODENAME / DEBIAN_CODENAME in /etc/os-release is the
  # upstream codename — that's what Docker's apt repo expects.
  . /etc/os-release
  ID_LIKE="${ID_LIKE:-}"
  case "$ID" in
    ubuntu)
      DOCKER_DIST="ubuntu"
      DIST_CODENAME="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
      ;;
    debian)
      DOCKER_DIST="debian"
      DIST_CODENAME="${DEBIAN_CODENAME:-$VERSION_CODENAME}"
      ;;
    *)
      if [[ " $ID_LIKE " == *" ubuntu "* ]]; then
        DOCKER_DIST="ubuntu"
        DIST_CODENAME="${UBUNTU_CODENAME:-}"
        [[ -z "$DIST_CODENAME" ]] && fail "Detected Ubuntu derivative '$ID' but UBUNTU_CODENAME is unset in /etc/os-release. Install Docker manually."
        info "detected Ubuntu derivative '$ID' — using upstream codename '$DIST_CODENAME'"
      elif [[ " $ID_LIKE " == *" debian "* ]]; then
        DOCKER_DIST="debian"
        DIST_CODENAME="${DEBIAN_CODENAME:-$VERSION_CODENAME}"
        [[ -z "$DIST_CODENAME" ]] && fail "Detected Debian derivative '$ID' but no codename available. Install Docker manually."
        info "detected Debian derivative '$ID' — using codename '$DIST_CODENAME'"
      else
        fail "Unsupported OS: $ID (ID_LIKE='$ID_LIKE'). Install Docker manually then re-run."
      fi
      ;;
  esac

  curl -fsSL "https://download.docker.com/linux/${DOCKER_DIST}/gpg" \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DOCKER_DIST} ${DIST_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -y
  sudo apt-get install -y \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  sudo usermod -aG docker "$USER"
  warn "Added $USER to the 'docker' group. Group membership only takes effect on next login."
  warn "This script uses 'sudo docker' so it keeps working in the current shell."
else
  info "Docker already installed: $(docker --version 2>/dev/null || sudo docker --version)"
fi

# Confirm Docker is alive
sudo docker run --rm hello-world >/dev/null 2>&1 \
  || fail "Docker hello-world failed — fix Docker before continuing"
info "Docker working"
step_ok

# ── 2/8  Clone repo ────────────────────────────────────────────────────────
step "2/8  Clone repo into $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R "$USER:$USER" "$INSTALL_DIR"
cd "$INSTALL_DIR"
if [[ -d .git ]]; then
  info "repo already cloned — attempting git fetch + reset --hard origin/$REPO_BRANCH"
  if git fetch origin "$REPO_BRANCH" 2>/dev/null; then
    git reset --hard "origin/$REPO_BRANCH"
    info "repo refreshed"
  else
    warn "git fetch failed (offline or DNS broken?) — continuing with the current checkout"
    warn "current HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  fi
else
  git clone --branch "$REPO_BRANCH" "$REPO_URL" .
  info "cloned $REPO_URL @ $REPO_BRANCH"
fi
step_ok

# ── 3/8  Image strategy ────────────────────────────────────────────────────
step "3/8  Image strategy: $IMAGE_STRATEGY"
if [[ "$IMAGE_STRATEGY" == "pull" ]]; then
  info "logging into ghcr.io as $GHCR_USER"
  echo "$GHCR_PAT" | sudo docker login ghcr.io -u "$GHCR_USER" --password-stdin
  info "GHCR login OK"
else
  info "validating Docker daemon DNS (a build needs apt-get inside containers)"
  if sudo docker run --rm debian:bookworm-slim sh -c \
       'apt-get update >/dev/null 2>&1 && echo ok' >/dev/null 2>&1; then
    info "Docker daemon DNS OK — local build will work"
  else
    fail "Docker daemon DNS broken — apt-get update fails inside containers.
       Fix daemon DNS (try: sudo systemctl restart docker; check /etc/docker/daemon.json),
       or re-run with: GHCR_PAT=... IMAGE_STRATEGY=pull bash $0"
  fi
fi
step_ok

# ── 4/8  Generate .env.demo + compose overrides ────────────────────────────
step "4/8  Generate .env.demo + .env symlink + web/.env.local + compose overrides"

ENV_FILE="$INSTALL_DIR/.env.demo"
if [[ -f "$ENV_FILE" ]]; then
  warn ".env.demo exists — leaving in place. Delete it and re-run to regenerate."
else
  JWT_SECRET=$(openssl rand -hex 32)
  ADMIN_JWT_SECRET=$(openssl rand -hex 32)
  METRICS_TOKEN=$(openssl rand -hex 32)
  POSTGRES_PASSWORD=$(openssl rand -hex 32)
  REDIS_PASSWORD=$(openssl rand -hex 32)

  cat > "$ENV_FILE" <<EOF
# Generated by scripts/demo/vm-localhost-bootstrap.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
APP_ENV=staging
LOG_LEVEL=INFO
APP_VERSION=demo

# Server-generated secrets
JWT_SECRET=$JWT_SECRET
ADMIN_JWT_SECRET=$ADMIN_JWT_SECRET
METRICS_TOKEN=$METRICS_TOKEN
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD

# Postgres + Redis — service-name DNS inside the compose network
DATABASE_URL=postgresql://studybuddy:${POSTGRES_PASSWORD}@db:5432/studybuddy
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# Content store
CONTENT_STORE_PATH=/data/content

# Auth0 — stubbed. Demo personas use local-auth (Phase A), not Auth0.
AUTH0_DOMAIN=stub.local
AUTH0_JWKS_URL=http://stub.local/.well-known/jwks.json
AUTH0_STUDENT_CLIENT_ID=stub-student
AUTH0_TEACHER_CLIENT_ID=stub-teacher
AUTH0_MGMT_CLIENT_ID=stub-mgmt
AUTH0_MGMT_CLIENT_SECRET=stub-mgmt-secret
AUTH0_MGMT_API_URL=http://stub.local/api/v2

# SMTP — blank; localhost demo doesn't need outbound email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_NAME=StudyBuddy

# Stripe — blank; /subscriptions paths will error, other flows work
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# CORS + frontend — localhost only
ALLOWED_ORIGINS=http://localhost:8443,http://localhost:3000,http://127.0.0.1:8443,http://127.0.0.1:3000
FRONTEND_URL=http://localhost:8443

# Sentry — disabled for localhost
SENTRY_DSN=
SENTRY_ENVIRONMENT=demo

# Optional
HCLOUD_TOKEN=
EOF
  chmod 600 "$ENV_FILE"
  info "wrote $ENV_FILE (mode 600)"
fi

# Base compose has `env_file: - .env` hardcoded in 8 services. The
# `--env-file .env.demo` flag governs variable substitution only, not those
# per-service env_file directives. Symlink so the same file backs both.
if [[ -L "$INSTALL_DIR/.env" || -f "$INSTALL_DIR/.env" ]]; then
  info ".env already present — leaving in place"
else
  ln -s .env.demo "$INSTALL_DIR/.env"
  info "symlinked .env → .env.demo (for base-compose env_file: directives)"
fi

# Web service also has env_file: ./web/.env.local. Real client values are
# inlined in compose; an empty file is sufficient.
WEB_ENV_FILE="$INSTALL_DIR/web/.env.local"
if [[ -f "$WEB_ENV_FILE" ]]; then
  info "$WEB_ENV_FILE already present"
else
  mkdir -p "$INSTALL_DIR/web"
  cat > "$WEB_ENV_FILE" <<'EOF'
# Generated by scripts/demo/vm-localhost-bootstrap.sh — intentionally empty.
# Real client-side env vars are set inline in docker-compose.yml's web
# service `environment:` block. This file exists only so the env_file:
# directive in compose can read it without failing.
EOF
  info "created empty $WEB_ENV_FILE"
fi

# Patch base docker-compose.yml to remove pgbouncer from the depends_on
# YAML anchors. Compose's depends_on merge is deep-merge (not replace), so
# a sidecar override CAN'T remove pgbouncer from the merged result. Only
# fix on Compose <2.21 is to edit the source anchor.
if grep -qE "^  pgbouncer:$" "$INSTALL_DIR/docker-compose.yml"; then
  info "patching docker-compose.yml — remove pgbouncer from anchor definitions"
  cp -n "$INSTALL_DIR/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml.bak"
  python3 <<PYEOF
import re, pathlib
p = pathlib.Path("$INSTALL_DIR/docker-compose.yml")
text = p.read_text()
head, sep, body = text.partition("\nservices:")
# Both x-depends-infra (service_started) and x-depends-all (service_healthy)
# have a pgbouncer entry. Match either condition.
patched = re.sub(
    r"  pgbouncer:\n    condition: service_\w+\n",
    "",
    head,
)
removed = head.count("  pgbouncer:\n") - patched.count("  pgbouncer:\n")
if patched != head:
    p.write_text(patched + sep + body)
    print(f"  patched — removed {removed} pgbouncer entries from anchors")
else:
    print("  no anchor change (pgbouncer was already absent above services:)")
PYEOF
else
  info "docker-compose.yml anchors already clean"
fi

# Generate the localhost override: per-service depends_on (pgbouncer-free),
# python-based api healthcheck (image has no curl), and `volumes: []` for
# web (clears the bind mount that hides the prebuilt /app/server.js).
LOCAL_OVERRIDE="$INSTALL_DIR/docker-compose.localhost.yml"
if [[ -f "$LOCAL_OVERRIDE" ]]; then
  info "$LOCAL_OVERRIDE already present"
else
  cat > "$LOCAL_OVERRIDE" <<'EOF'
# =============================================================================
# docker-compose.localhost.yml — third overlay on top of base + demo overrides
#
# Generated by scripts/demo/vm-localhost-bootstrap.sh. Three concerns:
#   1. Per-service depends_on with pgbouncer dropped (works alongside the
#      base-compose YAML anchor patch that the bootstrap also applies).
#   2. api healthcheck via python urllib (the image has no curl).
#   3. web volumes cleared (base compose's bind-mount ./web:/app hides the
#      prebuilt /app/server.js — Compose volume merge is unreliable across
#      versions, so we also docker-cp the image contents onto the host in
#      Step 6 as belt-and-suspenders).
#
# Use:
#   docker compose \
#     -f docker-compose.yml \
#     -f docker-compose.demo.yml \
#     -f docker-compose.localhost.yml \
#     --env-file .env.demo up -d
# =============================================================================

services:
  api:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/healthz', timeout=3); sys.exit(0 if r.status == 200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  celery-worker:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  celery-pipeline:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  celery-beat-primary:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  celery-beat-standby:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  pipeline:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  web:
    volumes: []
EOF
  info "created $LOCAL_OVERRIDE"
fi
step_ok

# ── 5/8  Content store directories ─────────────────────────────────────────
step "5/8  Content store directories (mode 777)"
# Container bind targets:
#   /opt/studybuddy/data            → container /data
#   /opt/studybuddy/content_store_data → container /data/content
# Container UID likely differs from host user; 777 keeps the
# seed_dev_content.py mkdir step from failing with PermissionError.
sudo mkdir -p "$INSTALL_DIR/content_store_data" "$INSTALL_DIR/data"
sudo chown -R "$USER:$USER" "$INSTALL_DIR/content_store_data" "$INSTALL_DIR/data"
sudo chmod -R 777 "$INSTALL_DIR/content_store_data" "$INSTALL_DIR/data"
# Also pre-create /data/* in case a future override flips bind targets.
sudo mkdir -p /data/content /data/sample-visuals
sudo chown -R "$USER:$USER" /data
sudo chmod -R 777 /data
info "  /opt/studybuddy/content_store_data → container /data/content"
info "  /opt/studybuddy/data               → container /data"
step_ok

# ── 6/8  Hydrate /opt/studybuddy/web from prebuilt image ──────────────────
if [[ "$IMAGE_STRATEGY" == "pull" && ! -f "$INSTALL_DIR/web/server.js" ]]; then
  step "6/8  Hydrate /opt/studybuddy/web/ from prebuilt web image"
  # Base compose bind-mounts ./web:/app over the prebuilt Next.js standalone
  # image, hiding /app/server.js. Compose `volumes: []` override doesn't
  # reliably wipe the inherited bind. Reliable fix: extract the image's
  # /app contents onto the host so the bind mount serves them.
  WEB_IMAGE="ghcr.io/$GHCR_USER/studybuddy-web:latest"
  info "ensuring $WEB_IMAGE is cached"
  sudo docker pull "$WEB_IMAGE" >/dev/null
  TEMP_NAME="temp-web-extract-$$"
  sudo docker create --name "$TEMP_NAME" "$WEB_IMAGE" >/dev/null
  info "extracting image:/app/. into $INSTALL_DIR/web/"
  sudo docker cp "$TEMP_NAME:/app/." "$INSTALL_DIR/web/"
  sudo docker rm "$TEMP_NAME" >/dev/null
  if [[ -f "$INSTALL_DIR/web/server.js" ]]; then
    info "  ✓ /opt/studybuddy/web/server.js present"
  else
    fail "server.js NOT extracted from image — investigate manually"
  fi
  step_ok
else
  info "6/8  web hydration skipped (IMAGE_STRATEGY=$IMAGE_STRATEGY, server.js already present)"
fi

# ── 7/8  Bring stack up + migrations + seed ────────────────────────────────
step "7/8  Bring stack up + migrations + seed"
cd "$INSTALL_DIR"
if [[ "$IMAGE_STRATEGY" == "pull" ]]; then
  COMPOSE_ARGS="-f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo"
  info "docker compose pull (this is the big download — ~3 min)"
  sudo docker compose $COMPOSE_ARGS pull
  info "docker compose up -d"
  sudo docker compose $COMPOSE_ARGS up -d
else
  COMPOSE_ARGS="--env-file .env.demo"
  info "docker compose up -d --build (this is the big build — ~5 min)"
  sudo docker compose $COMPOSE_ARGS up -d --build
fi

info "waiting 45s for services to settle…"
sleep 45
sudo docker compose $COMPOSE_ARGS ps

# Verify api is reachable from inside its container before seeding.
info "verifying api is healthy"
if ! sudo docker compose $COMPOSE_ARGS exec -T api python -c \
     "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).status==200 else 1)"; then
  fail "api /healthz check failed — see 'docker compose logs api --tail 100'"
fi
info "api responding to /healthz"

info "running alembic upgrade head"
sudo docker compose $COMPOSE_ARGS exec -T api alembic upgrade head

# The api image's bind mount is ./backend → /app, so /app/scripts/ has the
# Python seed_*.py files but NOT the orchestrator at scripts/demo/seed.sh.
# Copy it in, then run. (Idempotent: each underlying script handles its
# own "already exists" cases.)
info "copying scripts/demo/seed.sh into api container"
sudo docker compose $COMPOSE_ARGS exec -T api mkdir -p /app/scripts/demo
API_CID=$(sudo docker compose $COMPOSE_ARGS ps -q api)
sudo docker cp "$INSTALL_DIR/scripts/demo/seed.sh" "$API_CID:/app/scripts/demo/seed.sh"
sudo docker compose $COMPOSE_ARGS exec -T api chmod +x /app/scripts/demo/seed.sh

info "running scripts/demo/seed.sh inside api container"
sudo docker compose $COMPOSE_ARGS exec -T api bash /app/scripts/demo/seed.sh
step_ok

# ── 8/8  Optional content rsync ────────────────────────────────────────────
# Bind targets are /opt/studybuddy/content_store_data and
# /opt/studybuddy/web/public/sample-visuals — NOT /data/* on host.
if [[ -n "$OLD_HOST" ]]; then
  step "8/8  Rsync content from $OLD_HOST"
  info "rsync content_store_data → $INSTALL_DIR/content_store_data/"
  rsync -avh --progress \
    "${OLD_HOST}:${OLD_REPO_DIR%/}/content_store_data/" \
    "$INSTALL_DIR/content_store_data/"
  info "rsync web/public/sample-visuals → $INSTALL_DIR/web/public/sample-visuals/"
  mkdir -p "$INSTALL_DIR/web/public/sample-visuals"
  rsync -avh --progress \
    "${OLD_HOST}:${OLD_REPO_DIR%/}/web/public/sample-visuals/" \
    "$INSTALL_DIR/web/public/sample-visuals/"
  info "content rsync complete"
  step_ok
else
  info "8/8  OLD_HOST not set — skipping content rsync"
fi

# ── Done ───────────────────────────────────────────────────────────────────
_log_only ""
_log_only "STEP_OK    [$(date -u +%H:%M:%SZ)] BOOTSTRAP COMPLETE"
_log_only "================================================================"

echo ""
echo -e "${bold}═════════════════════════════════════════════════════════════════════${reset}"
echo -e "${green}✓ StudyBuddy localhost-mirror bootstrap complete${reset}"
echo -e "${bold}═════════════════════════════════════════════════════════════════════${reset}"
echo ""
info "install log: $LOG_FILE"
echo ""

if [[ "$IMAGE_STRATEGY" == "pull" ]]; then
  cat <<EOF
Smoke test:
    curl -sfI http://127.0.0.1:8443/healthz
    curl -sfI http://127.0.0.1:8443/

Open in browser:
    http://localhost:8443      (compose-internal nginx, proxies to api+web)
EOF
else
  cat <<EOF
Smoke test:
    curl -sf http://127.0.0.1:8000/healthz && echo OK
    curl -sfI http://127.0.0.1:3000/ | head -1

Open in browser:
    http://localhost:3000      (web; api on http://localhost:8000)
EOF
fi

echo ""
if [[ -z "$OLD_HOST" ]]; then
  cat <<EOF
You skipped the content rsync. Copy from the old box when ready (bind
targets are /opt/studybuddy/*, NOT /data/*):

  rsync -avh --progress \\
    siva@old-box:/path/to/StudyBuddy_OnDemand/content_store_data/ \\
    /opt/studybuddy/content_store_data/

  rsync -avh --progress \\
    siva@old-box:/path/to/StudyBuddy_OnDemand/web/public/sample-visuals/ \\
    /opt/studybuddy/web/public/sample-visuals/

EOF
fi

cat <<EOF
Log out and back in so 'docker' works without sudo.

Demo personas (seeded — see access_info.txt produced by the seed scripts
above for the full list with passwords):

  Super admin:
    /admin/login    wegofwd2020@gmail.com    (password from seed_super_admin.py output)

  MilfordWaterford School (4 teachers, 16 students, 7 classrooms):
    /signin   sam.houston@milfordwaterford.edu      MWTeacher-Sam-2026!      (G11 STEM teacher)
    /signin   warren.buffett@milfordwaterford.edu   MWTeacher-Warren-2026!   (G11/G12 Commerce teacher)
    /signin   linda.ronstad@milfordwaterford.edu    MWTeacher-Linda-2026!    (G11/G12 Science teacher)
    /signin   anya.iyer@milfordwaterford.edu        MWStudent-Anya-2026!     (G11 Commerce student)
    /signin   fatima.alhassan@milfordwaterford.edu  MWStudent-Fatima-2026!   (G11 Science student)
    /signin   emma.thompson@milfordwaterford.edu    MWStudent-Emma-2026!     (G11 STEM student)

  Phase A Dev School (for local-auth testing):
    /signin   admin@devschool.dev      DevAdmin1234!     (school admin)
    /signin   teacher@devschool.dev    DevTeacher1234!   (teacher)
    /signin   student@devschool.dev    DevStudent1234!   (student G8)

  Public "request demo via email" (test-run flow):
    Visit /demo on the marketing site → submit your email → verify link →
    auto-provisioned to Grade 11 Science at MilfordWaterford (both teacher
    + student accounts). See backend/src/demo/test_run_router.py.

  Persistent test account (no email needed):
    /signin   demo-test@studybuddy.dev    DemoTest-2026!    (G8 student, 30-day TTL)

EOF
