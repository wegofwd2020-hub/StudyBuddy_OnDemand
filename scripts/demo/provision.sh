#!/usr/bin/env bash
# =============================================================================
# scripts/demo/provision.sh — second-tenant bootstrap on a shared CX22
#
# Run this on a Hetzner CX22 that mambakkam.net's first-tenant provision.sh
# has already bootstrapped (Docker, UFW, fail2ban, the deploy user, host
# nginx, /etc/ssl/cloudflare/, daily-backup cron at 02:30 UTC). This script
# does NOT re-run any of those steps — it only adds the StudyBuddy-specific
# repo, .env.demo, host-nginx vhost, sudoers entry, content store, restic
# repo, and 02:00 UTC backup cron.
#
# A pre-flight check hard-fails if the mambakkam first-tenant artefacts are
# missing, to prevent silent skip of the system bootstrap.
#
# Idempotent — re-running is safe; finished steps are skipped.
#
# Usage (one-liner from a fresh shell):
#   curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh | bash
#
# Or, if you've already cloned the repo:
#   sudo bash scripts/demo/provision.sh
#
# What it does:
#   0. Pre-flight: confirm mambakkam first-tenant bootstrap is in place
#   1. apt — pgvector client tooling + restic (cheap if already there)
#   2. /opt/studybuddy + git clone
#   3. .env.demo skeleton with comments
#   4. StudyBuddy sudoers entry for the (already-existing) deploy user
#   5. Verify /etc/ssl/cloudflare/ + drop StudyBuddy host-nginx vhost
#   6. cron — daily restic backup at 02:00 UTC + weekly check at Sun 03:00
#   7. Content store directory
#   8. restic password generation + repo init at /opt/studybuddy/backups/restic/
#      (PRINTS PASSWORD ONCE — operator must record it; lost = unrecoverable)
#   9. State stamp at /var/lib/studybuddy/second-tenant-provisioned
#
# Exit codes:
#   0 — provisioning complete (or already done)
#   1 — fatal error
#   2 — must be run as root
#   3 — pre-flight failed (mambakkam first-tenant bootstrap not detected)
# =============================================================================

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/studybuddy}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
MAMBAKKAM_STATE="/var/lib/mambakkam/first-tenant-provisioned"

# ── Output helpers ─────────────────────────────────────────────────────────
bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"; red="\033[0;31m"; reset="\033[0m"
info() { echo -e "${green}[info]${reset}  $*"; }
warn() { echo -e "${yellow}[warn]${reset}  $*"; }
fail() { echo -e "${red}[FAIL]${reset}  $*" >&2; exit 1; }
preflight_fail() { echo -e "${red}[PRE-FLIGHT FAILED]${reset}  $*" >&2; exit 3; }
step() { echo -e "\n${bold}── $* ──${reset}"; }

[[ $EUID -eq 0 ]] || { echo "must be run as root (try: sudo bash $0)"; exit 2; }

# ── 0. Pre-flight: mambakkam first-tenant artefacts ────────────────────────
step "0/9  pre-flight — confirm mambakkam first-tenant provisioning"

PREFLIGHT_OK=1
check() {
  local label="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    info "  ✓ $label"
  else
    echo -e "${red}  ✗ $label${reset}" >&2
    PREFLIGHT_OK=0
  fi
}

check "Docker installed"             "command -v docker"
check "Docker daemon active"         "systemctl is-active --quiet docker"
check "UFW active"                   "ufw status | grep -q 'Status: active'"
check "fail2ban active"              "systemctl is-active --quiet fail2ban"
check "deploy user exists"           "id -u $DEPLOY_USER"
check "host nginx installed"         "command -v nginx && systemctl is-active --quiet nginx"
check "/etc/ssl/cloudflare/ dir"     "[[ -d /etc/ssl/cloudflare ]]"
check "Origin Cert + key present"    "[[ -f /etc/ssl/cloudflare/origin-cert.pem ]] && [[ -f /etc/ssl/cloudflare/origin-key.pem ]]"
check "mambakkam state stamp"        "[[ -f $MAMBAKKAM_STATE ]]"

if [[ $PREFLIGHT_OK -eq 0 ]]; then
  preflight_fail "missing first-tenant artefacts above. Run mambakkam.net's first-tenant provision.sh on this box first:
    curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/mambakkam-net/main/scripts/launch/provision.sh | bash"
fi

# Cert B (Origin Cert for demo.usestudybuddy.com) — operator must paste from
# password manager BEFORE this script runs reload. Lives at a separate path
# from Cert A (mambakkam.net) per the two-cert split — see the header of
# infra/nginx/demo.usestudybuddy.com.conf for the architecture rationale.
CERT_B=/etc/ssl/cloudflare/usestudybuddy.com-cert.pem
KEY_B=/etc/ssl/cloudflare/usestudybuddy.com-key.pem
if [[ ! -f "$CERT_B" || ! -f "$KEY_B" ]]; then
  warn "Cert B not found at $CERT_B / $KEY_B"
  warn "The StudyBuddy host nginx vhost references this cert; nginx -t will"
  warn "fail to reload until you paste it from your password manager:"
  warn "    cat > $CERT_B <<EOF ... EOF"
  warn "    cat > $KEY_B <<EOF ... EOF"
  warn "    chmod 600 $CERT_B $KEY_B"
  warn "Continuing — the script will still drop the vhost; reload after pasting."
elif command -v openssl >/dev/null 2>&1; then
  SAN_B=$(openssl x509 -in "$CERT_B" -noout -text 2>/dev/null \
          | grep -A1 "Subject Alternative Name" | tail -1 || true)
  if [[ -n "$SAN_B" ]] && ! grep -q "demo.usestudybuddy.com" <<< "$SAN_B"; then
    warn "Cert B SAN does NOT include demo.usestudybuddy.com:"
    warn "  $SAN_B"
    warn "Re-issue at Cloudflare (usestudybuddy.com zone → SSL/TLS → Origin Server)."
  else
    info "Cert B present at $CERT_B with demo.usestudybuddy.com SAN"
  fi
fi

info "pre-flight green — mambakkam first-tenant bootstrap detected (provisioned $(grep '^provisioned_at' $MAMBAKKAM_STATE | cut -d= -f2))"

# ── 1. apt — pgvector client tooling + restic ──────────────────────────────
step "1/9  apt — pgvector + postgres client + restic"
export DEBIAN_FRONTEND=noninteractive
# Cheap (no full apt upgrade — mambakkam first-tenant did that on Day -1);
# only install StudyBuddy-specific tooling that mambakkam didn't need.
# restic is installed by mambakkam first-tenant too, but we re-list it here
# for safety (apt skips if already installed).
apt-get install -y --no-install-recommends \
  postgresql-client-common postgresql-client \
  restic
info "postgres client + restic installed (cheap if already present)"

# ── 2. /opt/studybuddy + git clone ──────────────────────────────────────────
step "2/9  $INSTALL_DIR  +  git clone"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
if [[ -d .git ]]; then
  info "repo already cloned at $INSTALL_DIR — running git fetch + reset"
  git fetch origin "$REPO_BRANCH"
  git reset --hard "origin/$REPO_BRANCH"
else
  git clone --branch "$REPO_BRANCH" --depth 50 "$REPO_URL" .
  info "cloned $REPO_URL @ $REPO_BRANCH"
fi
chown -R root:root "$INSTALL_DIR"

# ── 3. .env.demo skeleton ──────────────────────────────────────────────────
step "3/9  .env.demo skeleton"
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

# JWT access-token TTL in minutes. Bumped from the default 15 → 240 (4h) so
# a demo walkthrough does not have to re-login mid-session. The demo_account
# row still caps the effective lifetime at 24h (student) / 48h (teacher)
# via the min(JWT_TTL, remaining_account_lifetime) clamp in demo/router.py.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=240

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
ALLOWED_ORIGINS=https://demo.usestudybuddy.com,http://localhost:3000
FRONTEND_URL=https://demo.usestudybuddy.com

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

# ── 4. StudyBuddy sudoers entry (alongside mambakkam's) ────────────────────
step "4/9  StudyBuddy sudoers entry"
SUDO_FILE="/etc/sudoers.d/studybuddy-deploy"
cat > "$SUDO_FILE" <<EOF
# Allow $DEPLOY_USER to run docker compose + git operations from $INSTALL_DIR
# without a password. Mambakkam's sudoers file already covers
# /usr/bin/docker compose * (broad), but we want a path-scoped git rule for
# /opt/studybuddy specifically. Both files coexist; the deploy user gets
# the union of permissions.
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/git -C $INSTALL_DIR *
EOF
chmod 440 "$SUDO_FILE"
visudo -cf "$SUDO_FILE" >/dev/null
info "deploy-user sudo policy installed at $SUDO_FILE"

# Repo ownership: deploy user needs to git pull
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$INSTALL_DIR"

# ── 5. host nginx vhost for demo.usestudybuddy.com ─────────────────────────
step "5/9  host nginx vhost (alongside mambakkam.net's)"
VHOST_SRC="$INSTALL_DIR/infra/nginx/demo.usestudybuddy.com.conf"
VHOST_AVAIL="/etc/nginx/sites-available/demo.usestudybuddy.com.conf"
VHOST_ENABLED="/etc/nginx/sites-enabled/demo.usestudybuddy.com.conf"

if [[ ! -f "$VHOST_SRC" ]]; then
  fail "vhost source $VHOST_SRC not found — repo state is broken (was the host-nginx vhost ever shipped?)"
fi

cp "$VHOST_SRC" "$VHOST_AVAIL"
info "copied vhost → $VHOST_AVAIL"

ln -sf "$VHOST_AVAIL" "$VHOST_ENABLED"
info "enabled vhost via symlink (mambakkam.net.conf stays enabled — Host header dispatches)"

if nginx -t 2>/dev/null; then
  systemctl reload nginx
  info "nginx -t green; nginx reloaded — both vhosts now active"
else
  warn "nginx -t failed — fix and run: systemctl reload nginx"
  warn "Common cause: the StudyBuddy compose stack is not yet up, so the upstream"
  warn "127.0.0.1:8443 is unreachable. The vhost is installed; reload after compose up."
fi

# ── 6. cron — daily restic backup + weekly integrity check ─────────────────
step "6/9  cron — daily backup (02:00) + weekly check (Sun 03:00)"
CRON_FILE="/etc/cron.d/studybuddy-demo-backup"
cat > "$CRON_FILE" <<EOF
# StudyBuddy demo backup cron — generated by provision.sh
#
# Two entries:
#   - DAILY at 02:00 UTC: pg_dump + restic backup (snapshot + forget)
#     Runs 30 min BEFORE mambakkam's 02:30 UTC backup so the disk I/O
#     doesn't collide. mambakkam's weekly check runs at 03:30 (Sundays);
#     ours at 03:00 — also offset.
#   - WEEKLY Sunday at 03:00 UTC: restic check + prune.
#
# Both append to /var/log/studybuddy-backup.log so Promtail (Loki) picks
# them up under {job="backups", which="studybuddy"}.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

0 2 * * *   root cd $INSTALL_DIR && bash scripts/demo/backup.sh       >> /var/log/studybuddy-backup.log 2>&1
0 3 * * 0   root cd $INSTALL_DIR && bash scripts/demo/backup-check.sh >> /var/log/studybuddy-backup.log 2>&1
EOF
chmod 644 "$CRON_FILE"
service cron reload
info "cron entry installed at $CRON_FILE"

# ── 7. content store directory ──────────────────────────────────────────────
# Two trees land here, both rsync'd from the operator's dev machine:
#   /data/content/        ← from local content_store_data/  (lesson/quiz/
#                           tutorial JSON + audio MP3 + visuals/_legacy SVGs)
#                           mounted into compose as $CONTENT_STORE_PATH and
#                           served via nginx location /content/.
#   /data/sample-visuals/ ← from local web/public/sample-visuals/  (44 MP4
#                           tutorial videos referenced from tutorial_en.json
#                           via /sample-visuals/<unit>/<file>.mp4 URLs).
#                           Gitignored so they never reach the Docker image;
#                           must be deployed out-of-band. Served via nginx
#                           location /sample-visuals/.
step "7/9  content store directories"
mkdir -p /data/content /data/sample-visuals
chown -R "$DEPLOY_USER:$DEPLOY_USER" /data/content /data/sample-visuals
info "/data/content and /data/sample-visuals are ready for rsync from the operator's dev machine"

# ── 8. restic — encrypted backup repository ────────────────────────────────
# Separate repo from mambakkam's so password compromise on one doesn't
# affect the other. The daily-backup cron from step 6 hard-fails if this
# isn't done up-front (see scripts/demo/backup.sh exit code 5/6).
step "8/9  restic password + repo init"

RESTIC_PWD_DIR="/etc/restic"
RESTIC_PWD_FILE="$RESTIC_PWD_DIR/studybuddy.password"
RESTIC_REPO_PATH="$INSTALL_DIR/backups/restic"

mkdir -p "$RESTIC_PWD_DIR"
chmod 700 "$RESTIC_PWD_DIR"

if [[ -f "$RESTIC_PWD_FILE" ]]; then
  info "restic password already exists at $RESTIC_PWD_FILE — leaving in place"
  RESTIC_PWD_NEW=0
else
  openssl rand -hex 32 > "$RESTIC_PWD_FILE"
  chmod 600 "$RESTIC_PWD_FILE"
  chown root:root "$RESTIC_PWD_FILE"
  info "generated restic password at $RESTIC_PWD_FILE (mode 600 root:root)"
  RESTIC_PWD_NEW=1
fi

# Initialise the repo if it doesn't exist yet.
if [[ -f "$RESTIC_REPO_PATH/config" ]]; then
  info "restic repo already initialised at $RESTIC_REPO_PATH"
else
  mkdir -p "$RESTIC_REPO_PATH"
  if RESTIC_REPOSITORY="$RESTIC_REPO_PATH" \
     RESTIC_PASSWORD_FILE="$RESTIC_PWD_FILE" \
     restic init >/dev/null; then
    info "restic repo initialised at $RESTIC_REPO_PATH"
  else
    fail "restic init failed — check $RESTIC_REPO_PATH permissions"
  fi
fi

# ── 9. state stamp (parity with mambakkam) ─────────────────────────────────
step "9/9  state stamp"
STATE_DIR="/var/lib/studybuddy"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/second-tenant-provisioned" <<EOF
# This box has been bootstrapped as a StudyBuddy second tenant on top of
# mambakkam.net's first-tenant provisioning.
provisioned_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
provisioned_by=StudyBuddy_OnDemand/scripts/demo/provision.sh
deploy_user=$DEPLOY_USER
install_dir=$INSTALL_DIR
mambakkam_first_tenant_at=$(grep '^provisioned_at' "$MAMBAKKAM_STATE" 2>/dev/null | cut -d= -f2 || echo "unknown")
EOF
chmod 644 "$STATE_DIR/second-tenant-provisioned"
info "state stamp written to $STATE_DIR/second-tenant-provisioned"

# ── Final checklist ─────────────────────────────────────────────────────────
PUBLIC_IP="$(curl -s ifconfig.me 2>/dev/null || echo "<this-vps-public-ip>")"
cat <<EOF

${bold}═════════════════════════════════════════════════════════════════════${reset}
${green}✓ StudyBuddy second-tenant provisioning complete${reset}
${bold}═════════════════════════════════════════════════════════════════════${reset}
EOF

# ── Print restic password ONCE if it was newly generated ───────────────────
if [[ "${RESTIC_PWD_NEW:-0}" -eq 1 ]]; then
  cat <<EOF

${red}${bold}╔═══════════════════════════════════════════════════════════════════╗${reset}
${red}${bold}║  IMPORTANT — RESTIC BACKUP PASSWORD (shown once, write it down)   ║${reset}
${red}${bold}╚═══════════════════════════════════════════════════════════════════╝${reset}

This password unlocks /opt/studybuddy/backups/restic/. Without it, every
snapshot in that repo is permanently unrecoverable. Save to a password
manager NOW.

${bold}Password:${reset}  $(cat "$RESTIC_PWD_FILE")

A copy is on disk at: $RESTIC_PWD_FILE  (mode 600 root)

If the disk dies, the on-disk copy dies with it. The password manager
copy is your sole guarantee that off-box recovery (e.g. from a Hetzner
volume snapshot) can decrypt the repo.

EOF
fi

cat <<EOF

The shared CX23 is now running:
  - mambakkam.net  (first tenant; Host header dispatch from host nginx)
  - StudyBuddy     (second tenant; this provisioning)

Next steps (in order):

1. Edit $ENV_FILE
   - Replace every <REPLACE_WITH_openssl_rand_hex_32> with a fresh secret:
       openssl rand -hex 32
   - Paste real Auth0, Stripe-test, Gmail App Password values
   - Confirm ALLOWED_ORIGINS matches https://demo.usestudybuddy.com

2. Append the GitHub Actions deploy SSH public key to:
   /home/$DEPLOY_USER/.ssh/authorized_keys
   (do NOT overwrite — mambakkam.net's deploy key is already in this file;
    the matching private key for StudyBuddy goes into repo secret
    DEMO_VPS_SSH_KEY)

3. Confirm the docker-compose.demo.yml nginx port binding is 127.0.0.1:8443
   (NOT 0.0.0.0:443 — that would conflict with the host nginx). The host
   nginx vhost installed in step 5 above proxies demo.usestudybuddy.com
   traffic to 127.0.0.1:8443.

4. Upload pre-built content from your dev machine. One command does the
   inject + both rsyncs + (optional) post-deploy smoke:
   bash scripts/demo/sync-content.sh deploy@$PUBLIC_IP
   # Add --smoke https://demo.usestudybuddy.com to chain into the smoke check
   # once DNS is cut over. See `bash scripts/demo/sync-content.sh --help`
   # for the full flag list. The two rsync targets are
   # /data/content/ (lessons + audio + legacy visuals from
   # content_store_data/) and /data/sample-visuals/ (44 tutorial MP4s
   # from web/public/sample-visuals/ — gitignored, never in the Docker
   # image).

5. Bring the StudyBuddy stack up:
   cd $INSTALL_DIR
   docker compose -f docker-compose.yml -f docker-compose.demo.yml \\
     --env-file .env.demo up -d

6. Reload host nginx (now that the upstream 127.0.0.1:8443 is live):
   sudo nginx -t && sudo systemctl reload nginx

7. Run migrations + seed:
   docker compose exec api alembic upgrade head
   bash scripts/demo/seed.sh

8. Smoke check:
   bash scripts/demo/smoke.sh https://demo.usestudybuddy.com

9. Configure Cloudflare DNS:
   demo.usestudybuddy.com  →  $PUBLIC_IP   (Proxied, orange cloud)
   (mambakkam.net is already pointed here from step 6 of mambakkam's
    first-tenant checklist, on Day 0 morning before this script ran)

When all 9 steps are green, both tenants are live on the same box.

EOF
