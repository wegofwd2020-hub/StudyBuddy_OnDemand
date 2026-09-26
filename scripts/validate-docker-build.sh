#!/bin/bash
# =============================================================================
# scripts/validate-docker-build.sh — Docker build validation harness
#
# Tests Docker image builds and docker-compose configuration.
# Variants: DEV (syntax) and DEMO (comprehensive).
#
# Usage:
#   ./scripts/validate-docker-build.sh dev      # dockerfile syntax
#   ./scripts/validate-docker-build.sh demo     # full validation
#
# Returns: 0 = pass, 1 = fail
# =============================================================================

VARIANT="${1:-demo}"
PASSED=0
FAILED=0

pass() { echo "✅ $*"; ((PASSED++)); }
fail() { echo "❌ $*"; ((FAILED++)); }

echo "[$(date +%H:%M:%S)] Docker build validation — $VARIANT mode"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Shared: Dockerfile checks
# ─────────────────────────────────────────────────────────────────────────────

echo "Checking Dockerfiles..."
for df in ./backend/Dockerfile ./web/Dockerfile ./pipeline/Dockerfile; do
  if [[ ! -f "$df" ]]; then
    fail "$df: not found"
  elif ! grep -q "^FROM" "$df"; then
    fail "$df: missing FROM"
  else
    pass "$df"
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# DEMO mode: docker-compose validation
# ─────────────────────────────────────────────────────────────────────────────

if [[ "$VARIANT" == "demo" ]]; then
  echo ""
  echo "Checking docker-compose.yml..."
  if docker compose config >/dev/null 2>&1; then
    pass "docker-compose.yml valid"
  else
    fail "docker-compose.yml invalid"
  fi

  echo ""
  echo "Checking required services..."
  for service in api web db redis migrate; do
    if docker compose config --services 2>/dev/null | grep -q "^${service}\$"; then
      pass "service: $service"
    else
      fail "service: $service (not found)"
    fi
  done

  echo ""
  echo "Checking images..."
  for image in studybuddy-api studybuddy-web studybuddy-migrate studybuddy-celery-worker studybuddy-celery-pipeline; do
    if docker image inspect "${image}:latest" >/dev/null 2>&1; then
      pass "image: $image"
    else
      fail "image: $image (not built)"
    fi
  done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Passed: $PASSED | Failed: $FAILED"

if [[ $FAILED -eq 0 ]]; then
  echo "✅ All checks passed"
  exit 0
else
  echo "❌ $FAILED check(s) failed"
  exit 1
fi
