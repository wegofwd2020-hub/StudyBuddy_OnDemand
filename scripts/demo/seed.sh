#!/usr/bin/env bash
# =============================================================================
# scripts/demo/seed.sh — orchestrate demo seeding in dependency order
#
# Runs the existing per-module seed scripts in the correct order. Idempotent:
# each underlying script handles its own "already exists" cases. Safe to
# re-run after a `docker compose down` + `up` cycle.
#
# Usage (from the operator's laptop, against running compose):
#   docker compose --env-file .env.demo exec api bash /app/scripts/demo/seed.sh
#
# Or from inside the API container:
#   bash /app/scripts/demo/seed.sh
#
# Pre-flight checks:
#   - DB reachable
#   - Migrations at head (runs `alembic upgrade head` if not)
#
# Exit codes:
#   0 — all seed steps succeeded (or were idempotent skips)
#   1 — a seed step failed; see the per-step output above the failure
# =============================================================================

set -euo pipefail

bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"; red="\033[0;31m"; reset="\033[0m"
info() { echo -e "${green}[seed]${reset}  $*"; }
warn() { echo -e "${yellow}[skip]${reset}  $*"; }
fail() { echo -e "${red}[fail]${reset}  $*" >&2; exit 1; }

# We're inside the api container (cwd = /app/backend per Dockerfile)
cd /app/backend

# ── Pre-flight: DB reachable + at head ─────────────────────────────────────
info "pre-flight — checking DB connection"
python -c "
import asyncio, os
import asyncpg
async def main():
    c = await asyncpg.connect(os.environ['DIRECT_DB_URL'])
    v = await c.fetchval('SELECT 1')
    await c.close()
    assert v == 1
asyncio.run(main())
" || fail "cannot connect to database — check DATABASE_URL and that 'db' service is healthy"

info "pre-flight — running alembic upgrade head (idempotent)"
alembic upgrade head

# ── Step 1: super admin ────────────────────────────────────────────────────
# seed_super_admin.py now REQUIRES SUPER_ADMIN_PASSWORD (no hardcoded default,
# so a known password can never ship). If the operator didn't supply one,
# generate a strong random password and write it once to a chmod-600 file.
if [ -z "${SUPER_ADMIN_PASSWORD:-}" ]; then
  SUPER_ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)Aa1!"
  export SUPER_ADMIN_PASSWORD
  cred_file="${SUPER_ADMIN_CRED_FILE:-./super_admin_credentials.txt}"
  ( umask 177; printf 'super_admin email:    %s\nsuper_admin password: %s\n' \
      "${SUPER_ADMIN_EMAIL:-wegofwd2020@gmail.com}" "$SUPER_ADMIN_PASSWORD" > "$cred_file" )
  chmod 600 "$cred_file"
  warn "  no SUPER_ADMIN_PASSWORD set — generated a random one → $cred_file (chmod 600)."
  warn "  record it somewhere safe, then delete that file."
fi
info "step 1/5 — super admin (${SUPER_ADMIN_EMAIL:-wegofwd2020@gmail.com})"
if python scripts/seed_super_admin.py 2>&1 | tee /tmp/seed_super_admin.log; then
  info "  done"
else
  if grep -qiE "already exists|duplicate" /tmp/seed_super_admin.log; then
    warn "  super admin already seeded — skipping"
  else
    fail "step 1 failed; see /tmp/seed_super_admin.log"
  fi
fi

# ── Step 2: MilfordWaterford school + 4 teachers + 15 students ────────────
info "step 2/5 — MilfordWaterford school (4 teachers, 15 students)"
if python scripts/seed_demo_milfordwaterford.py 2>&1 | tee /tmp/seed_mw.log; then
  info "  done"
else
  if grep -qiE "already exists|duplicate" /tmp/seed_mw.log; then
    warn "  MilfordWaterford already seeded — skipping"
  else
    fail "step 2 failed; see /tmp/seed_mw.log"
  fi
fi

# ── Step 3: public Try-it demo student ─────────────────────────────────────
info "step 3/5 — public 'Try it' G8 student (demo-test@studybuddy.dev)"
if python scripts/seed_demo_test_account.py 2>&1 | tee /tmp/seed_demo_test.log; then
  info "  done"
else
  if grep -qiE "already exists|duplicate" /tmp/seed_demo_test.log; then
    warn "  demo-test student already seeded — skipping"
  else
    fail "step 3 failed; see /tmp/seed_demo_test.log"
  fi
fi

# ── Step 4: Phase A local-auth dev school ──────────────────────────────────
info "step 4/5 — Phase A local-auth Dev School + admin (admin@devschool.dev)"
if python scripts/seed_phase_a_dev.py 2>&1 | tee /tmp/seed_phase_a.log; then
  info "  done"
else
  if grep -qiE "already exists|duplicate" /tmp/seed_phase_a.log; then
    warn "  Dev School already seeded — skipping"
  else
    fail "step 4 failed; see /tmp/seed_phase_a.log"
  fi
fi

# ── Step 5: content-DB shell rows pointing at the uploaded content store ──
info "step 5/5 — content-DB rows for pre-uploaded content"
if python scripts/seed_dev_content.py 2>&1 | tee /tmp/seed_content.log; then
  info "  done"
else
  if grep -qiE "already exists|duplicate" /tmp/seed_content.log; then
    warn "  content-DB rows already present — skipping"
  else
    fail "step 5 failed; see /tmp/seed_content.log"
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
info "${bold}all seed steps complete${reset}"
echo ""
echo "Next: smoke check the deploy with:"
echo "    bash scripts/demo/smoke.sh https://demo.usestudybuddy.com"
