#!/bin/bash
# =============================================================================
# scripts/health-check.sh — comprehensive infrastructure health check
#
# Tests all 6 services (API, web, DB, Redis, nginx, PgBouncer) + Auth0.
# Designed for sys admins to diagnose infrastructure issues.
#
# Usage:
#   ./scripts/health-check.sh                      # check localhost
#   ./scripts/health-check.sh demo.usestudybuddy.com  # check demo server
#   ./scripts/health-check.sh --verbose            # verbose output
#   ./scripts/health-check.sh demo.usestudybuddy.com --verbose
#
# Returns:
#   0 = all services operational
#   1 = some services degraded or down
# =============================================================================

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST="${1:-localhost}"
VERBOSE="${2:-}"
ENDPOINT="https://${HOST}/api/v1/health/deep"
if [[ "$HOST" == "localhost" ]]; then
  ENDPOINT="http://localhost:8000/api/v1/health/deep"
fi

# Timeout for curl
TIMEOUT=5

log() { echo "[$(date +'%Y-%m-%dT%H:%M:%SZ')] $*"; }
log_verbose() {
  if [[ "$VERBOSE" == "--verbose" ]]; then
    echo "[$(date +'%Y-%m-%dT%H:%M:%SZ')] [VERBOSE] $*" >&2
  fi
}
log_error() { echo -e "${RED}❌ ERROR:${NC} $*" >&2; }
log_ok() { echo -e "${GREEN}✅ OK:${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠️  WARNING:${NC} $*"; }
log_info() { echo -e "${BLUE}ℹ️  INFO:${NC} $*"; }

log "Starting infrastructure health check"
log_info "Target: $HOST"
log_info "Endpoint: $ENDPOINT"
log ""

# Fetch health status
log "Fetching health status..."
log_verbose "curl $ENDPOINT --max-time $TIMEOUT --silent --show-error"

RESPONSE=$(curl -s --max-time "$TIMEOUT" "$ENDPOINT" 2>&1) || {
  log_error "Failed to connect to $ENDPOINT"
  exit 1
}

log_verbose "Response: $RESPONSE"

# Parse response
STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null) || {
  log_error "Invalid JSON response: $RESPONSE"
  exit 1
}

SERVICES=$(echo "$RESPONSE" | jq '.services' 2>/dev/null)
VERSION=$(echo "$RESPONSE" | jq -r '.version' 2>/dev/null)
BUILD=$(echo "$RESPONSE" | jq -r '.build' 2>/dev/null)

log ""
log "═══════════════════════════════════════════════════════════════"
log "Infrastructure Health Report"
log "═══════════════════════════════════════════════════════════════"
log ""

# Overall status
if [[ "$STATUS" == "operational" ]]; then
  echo -e "${GREEN}Status: 🟢 OPERATIONAL${NC}"
elif [[ "$STATUS" == "degraded" ]]; then
  echo -e "${YELLOW}Status: 🟡 DEGRADED${NC}"
else
  echo -e "${RED}Status: 🔴 DOWN${NC}"
fi

log ""
log "Service Status:"
log "─────────────────────────────────────────────────────────────"

# Check each service
FAILED_SERVICES=()
for service in api web db redis pgbouncer auth0; do
  service_status=$(echo "$SERVICES" | jq -r ".$service" 2>/dev/null || echo "error")

  if [[ "$service_status" == "ok" ]]; then
    printf "  %-15s %s\n" "$service:" "$(printf '%b✅ ok%b\n' "$GREEN" "$NC")"
  else
    printf "  %-15s %s\n" "$service:" "$(printf '%b❌ %s%b\n' "$RED" "$service_status" "$NC")"
    FAILED_SERVICES+=("$service")
  fi
done

log ""
log "Version: $VERSION"
log "Build: $BUILD"
log ""
log "═══════════════════════════════════════════════════════════════"
log ""

# Report result
if [[ "$STATUS" == "operational" ]]; then
  log_ok "All services operational"
  exit 0
elif [[ "$STATUS" == "degraded" ]]; then
  log_warn "Some services degraded: ${FAILED_SERVICES[*]}"
  exit 1
else
  log_error "Critical services down: ${FAILED_SERVICES[*]}"
  exit 1
fi
