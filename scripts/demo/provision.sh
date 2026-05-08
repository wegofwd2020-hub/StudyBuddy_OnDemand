#!/usr/bin/env bash
# =============================================================================
# scripts/demo/provision.sh — one-shot Hetzner CX22 bootstrap
#
# Run this on a freshly-created Ubuntu 22.04 Hetzner box (as root). Idempotent
# — re-running is safe; finished steps are skipped.
#
# Usage (one-liner from a fresh box):
#   curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh | bash
#
# Or, if you've already cloned the repo:
#   sudo bash scripts/demo/provision.sh
#
# What it does:
#   1. Updates apt, installs system packages
#   2. Configures UFW firewall (ssh / 80 / 443) + fail2ban
#   3. Installs Docker CE + Compose plugin
#   4. Creates /opt/studybuddy + clones the repo
#   5. Adds the `deploy` system user (passwordless sudo for docker compose only)
#   6. Generates .env.demo skeleton with comments
#   7. Installs Nginx (used as the reverse proxy from docker-compose.demo.yml)
#   8. Sets up cron for the daily backup at 02:00 UTC
#   9. Prints a checklist of next steps the operator must complete manually
#
# Exit codes:
#   0 — provisioning complete (or already done)
#   1 — fatal error
#   2 — must be run as root
# =============================================================================

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"

# ── Output helpers ─────────────────────────────────────────────────────────
bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"; red="\033[0;31m"; reset="\033[0m"
info() { echo -e "${green}[info]${reset}  $*"; }
warn() { echo -e "${yellow}[warn]${reset}  $*"; }
fail() { echo -e "${red}[FAIL]${reset}  $*" >&2; exit 1; }
step() { echo -e "\n${bold}── $* ──${reset}"; }

[[ $EUID -eq 0 ]] || { echo "must be run as root (try: sudo bash $0)"; exit 2; }

# ── 1. apt update + system packages ────────────────────────────────────────
step "1/9  apt update + system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  ufw fail2ban \
  git rsync cron \
  postgresql-client-common postgresql-client \
  jq unzip
info "system packages installed"

# ── 2. UFW + fail2ban ───────────────────────────────────────────────────────
step "2/9  UFW firewall + fail2ban"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

systemctl enable --now fail2ban
info "ufw + fail2ban configured"

# ── 3. Docker CE + Compose plugin ───────────────────────────────────────────
step "3/9  Docker CE + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  info "docker installed: $(docker --version)"
else
  info "docker already present: $(docker --version)"
fi

# ── 4. /opt/studybuddy + git clone ──────────────────────────────────────────
step "4/9  $INSTALL_DIR  +  git clone"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
if [[ -d .git ]]; then
  info "repo already cloned at $INSTALL_DIR — running git pull"
  git fetch origin "$REPO_BRANCH"
  git reset --hard "origin/$REPO_BRANCH"
else
  git clone --branch "$REPO_BRANCH" --depth 50 "$REPO_URL" .
  info "cloned $REPO_URL @ $REPO_BRANCH"
fi
chown -R root:root "$INSTALL_DIR"

# ── 5. deploy user + docker group + restricted sudo ─────────────────────────
step "5/9  deploy user + docker group + restricted sudo"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
  info "created user: $DEPLOY_USER"
else
  info "user $DEPLOY_USER already exists"
fi
usermod -aG docker "$DEPLOY_USER"

# Restricted passwordless sudo: only `docker compose` operations under /opt/studybuddy
SUDO_FILE="/etc/sudoers.d/studybuddy-deploy"
cat > "$SUDO_FILE" <<EOF
# Allow $DEPLOY_USER to run docker-compose operations from $INSTALL_DIR
# without a password. Restricts sudo to git pull + compose commands so an
# auto-deploy CI job can't accidentally do anything else.
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/docker compose *, /usr/bin/git -C $INSTALL_DIR *
EOF
chmod 440 "$SUDO_FILE"
visudo -cf "$SUDO_FILE" >/dev/null
info "deploy-user sudo policy installed at $SUDO_FILE"

# Place an authorized_keys placeholder — operator pastes the GH Actions key here
mkdir -p "/home/$DEPLOY_USER/.ssh"
chmod 700 "/home/$DEPLOY_USER/.ssh"
touch "/home/$DEPLOY_USER/.ssh/authorized_keys"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"

# ── 6. .env.demo skeleton ──────────────────────────────────────────────────
step "6/9  .env.demo skeleton"
ENV_FILE="$INSTALL_DIR/.env.demo"
if [[ -f "$ENV_FILE" ]]; then
  warn ".env.demo already exists — leaving in place (not overwriting)"
else
  cat > "$ENV_FILE" <<'ENV_EOF'
# =============================================================================
# StudyBuddy OnDemand — Demo environment
#
# Generated by scripts/demo/provision.sh. Replace every <PLACEHOLDER> below
# with a real value before running `docker compose up -d`.
#
# Three classes of secret here:
#   1. Server-generated (JWT_SECRET, ADMIN_JWT_SECRET, METRICS_TOKEN, POSTGRES_PASSWORD)
#      — the placeholders below are stand-ins; replace with `openssl rand -hex 32`
#   2. Third-party service keys (Auth0, Stripe, Gmail SMTP) — created in those
#      providers' consoles and pasted here
#   3. Operational toggles (APP_ENV, LOG_LEVEL, ALLOWED_ORIGINS) — review the
#      defaults but typically no change needed
# =============================================================================

# ── Application env ────────────────────────────────────────────────────────
APP_ENV=staging
LOG_LEVEL=INFO
APP_VERSION=demo

# ── Server-generated secrets (run `openssl rand -hex 32` for each) ─────────
JWT_SECRET=<REPLACE_WITH_openssl_rand_hex_32>
ADMIN_JWT_SECRET=<REPLACE_WITH_openssl_rand_hex_32>
METRICS_TOKEN=<REPLACE_WITH_openssl_rand_hex_32>
POSTGRES_PASSWORD=<REPLACE_WITH_openssl_rand_hex_32>
REDIS_PASSWORD=<REPLACE_WITH_openssl_rand_hex_32>

# ── Postgres + Redis (auto-wired to the docker-compose services) ──────────
DATABASE_URL=postgresql://studybuddy:${POSTGRES_PASSWORD}@db:5432/studybuddy
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# ── Content store ─────────────────────────────────────────────────────────
CONTENT_STORE_PATH=/data/content

# ── Auth0 (free dev tenant for demo) ───────────────────────────────────────
AUTH0_DOMAIN=<your-demo-tenant>.auth0.com
AUTH0_JWKS_URL=https://<your-demo-tenant>.auth0.com/.well-known/jwks.json
AUTH0_STUDENT_CLIENT_ID=<from-auth0-dashboard>
AUTH0_TEACHER_CLIENT_ID=<from-auth0-dashboard>
AUTH0_MGMT_CLIENT_ID=<from-auth0-m2m-app>
AUTH0_MGMT_CLIENT_SECRET=<from-auth0-m2m-app>
AUTH0_MGMT_API_URL=https://<your-demo-tenant>.auth0.com/api/v2

# ── SMTP (Gmail App Password — free) ───────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your-gmail-address>
SMTP_PASSWORD=<gmail-app-password-from-myaccount.google.com/apppasswords>
SMTP_FROM_NAME=StudyBuddy

# ── Stripe (test mode for demo) ────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_<your-stripe-test-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-test-webhook-secret>

# ── CORS + frontend ────────────────────────────────────────────────────────
ALLOWED_ORIGINS=https://demo.studybuddy.app,http://localhost:3000
FRONTEND_URL=https://demo.studybuddy.app

# ── Sentry (optional but recommended) ──────────────────────────────────────
SENTRY_DSN=<your-sentry-dsn-or-leave-blank>
SENTRY_ENVIRONMENT=demo

# ── Hetzner snapshot trigger (optional; used by scripts/demo/backup.sh) ───
HCLOUD_TOKEN=<your-hetzner-cloud-api-token-or-leave-blank>
ENV_EOF
  chmod 600 "$ENV_FILE"
  chown "$DEPLOY_USER:$DEPLOY_USER" "$ENV_FILE"
  info "wrote $ENV_FILE (mode 600). Replace <PLACEHOLDER> values before deploying."
fi

# ── 7. Nginx (used by docker-compose.demo.yml as a host-port forwarder) ────
step "7/9  Nginx (host-level — not in compose)"
# We mount /etc/ssl/cloudflare/ into the nginx container; create the dir.
mkdir -p /etc/ssl/cloudflare
chmod 700 /etc/ssl/cloudflare
info "created /etc/ssl/cloudflare/ — paste your Cloudflare Origin Cert key + cert here"

# ── 8. cron — daily backup ──────────────────────────────────────────────────
step "8/9  cron — daily backup at 02:00 UTC"
CRON_FILE="/etc/cron.d/studybuddy-demo-backup"
cat > "$CRON_FILE" <<EOF
# StudyBuddy demo daily backup — generated by provision.sh
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

0 2 * * * root cd $INSTALL_DIR && bash scripts/demo/backup.sh >> /var/log/studybuddy-backup.log 2>&1
EOF
chmod 644 "$CRON_FILE"
service cron reload
info "cron entry installed at $CRON_FILE"

# ── 9. content store directory ──────────────────────────────────────────────
step "9/9  content store directory"
mkdir -p /data/content
chown -R "$DEPLOY_USER:$DEPLOY_USER" /data/content
info "/data/content is ready for rsync from the operator's dev machine"

# ── Final checklist ─────────────────────────────────────────────────────────
cat <<EOF

${bold}═════════════════════════════════════════════════════════════════════${reset}
${green}✓ provisioning complete${reset}
${bold}═════════════════════════════════════════════════════════════════════${reset}

Next steps (in order):

1. Edit $ENV_FILE
   - Replace every <REPLACE_WITH_openssl_rand_hex_32> with a fresh secret:
       openssl rand -hex 32
   - Paste real Auth0, Stripe-test, Gmail App Password values
   - Confirm ALLOWED_ORIGINS matches your demo domain

2. Paste the GitHub Actions deploy SSH public key into:
   /home/$DEPLOY_USER/.ssh/authorized_keys
   (the matching private key goes into repo secret DEMO_VPS_SSH_KEY)

3. Paste your Cloudflare Origin Cert into:
   /etc/ssl/cloudflare/origin-cert.pem
   /etc/ssl/cloudflare/origin-key.pem

4. Upload pre-built content from your dev machine:
   rsync -avz ./content_store/ deploy@<this-vps-ip>:/data/content/

5. Bring the stack up (still as root for first time):
   cd $INSTALL_DIR
   docker compose -f docker-compose.yml -f docker-compose.demo.yml \\
     --env-file .env.demo up -d

6. Run migrations + seed:
   docker compose exec api alembic upgrade head
   bash scripts/demo/seed.sh

7. Smoke check:
   bash scripts/demo/smoke.sh https://demo.studybuddy.app

8. Configure Cloudflare DNS:
   demo.studybuddy.app  →  $(curl -s ifconfig.me 2>/dev/null || echo "<this-vps-public-ip>")

When all 8 steps are green, you're live.

EOF
