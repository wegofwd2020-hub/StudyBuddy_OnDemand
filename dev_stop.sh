#!/usr/bin/env bash
# =============================================================================
# StudyBuddy OnDemand — Graceful Shutdown Script
#
# Usage:
#   ./dev_stop.sh              — graceful shutdown; data preserved
#   ./dev_stop.sh --force      — skip drain wait; stop containers immediately
#   ./dev_stop.sh --help
#
# Handles two stack modes automatically:
#   docker-compose  — detects a running Compose project and stops services in
#                     dependency-safe order (Celery → API → Web → PgBouncer
#                     → Redis → PostgreSQL)
#   bare containers — stops the sb-db / sb-redis / sb-test-db containers
#                     started by dev_start.sh
# =============================================================================

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()    { echo -e "\n${BLUE}━━ $* ━━${NC}"; }

# ── Parse flags ───────────────────────────────────────────────────────────────
FORCE=false
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        --help|-h)
            echo "Usage: $0 [--force]"
            echo "  (no flags)  Graceful — drain Celery tasks before stopping workers"
            echo "  --force     Skip drain; stop everything immediately"
            exit 0
            ;;
        *) error "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Container runtime detection ───────────────────────────────────────────────
detect_runtime() {
    if command -v podman &>/dev/null; then echo "podman"
    elif command -v docker &>/dev/null; then echo "docker"
    else error "Neither podman nor docker found."; exit 1
    fi
}
RUNTIME="$(detect_runtime)"

# ── Helpers ───────────────────────────────────────────────────────────────────

# True if a container is currently running
is_running() {
    $RUNTIME inspect "$1" --format "{{.State.Running}}" 2>/dev/null | grep -q "^true"
}

# Stop a single named container (docker-compose or bare)
stop_service() {
    local name="$1"
    local timeout="${2:-30}"   # seconds to wait for graceful stop
    if is_running "$name"; then
        info "Stopping $name (timeout ${timeout}s) ..."
        $RUNTIME stop -t "$timeout" "$name" 2>/dev/null || true
        success "$name stopped"
    else
        info "$name is not running — skipping"
    fi
}

# Issue BGSAVE to Redis and wait for it to finish before stopping
flush_redis() {
    local container="$1"
    if ! is_running "$container"; then return; fi

    info "Flushing Redis AOF to disk (BGSAVE) ..."
    # Extract the Redis password from the container's command
    local redis_pass
    redis_pass="$($RUNTIME inspect "$container" \
        --format '{{range .Args}}{{println .}}{{end}}' 2>/dev/null \
        | grep -A1 "requirepass" | tail -1 || true)"

    if [[ -n "$redis_pass" ]]; then
        $RUNTIME exec "$container" redis-cli -a "$redis_pass" --no-auth-warning BGSAVE 2>/dev/null || true
    else
        $RUNTIME exec "$container" redis-cli BGSAVE 2>/dev/null || true
    fi

    # Wait up to 10 s for the BGSAVE to finish
    for i in $(seq 1 10); do
        local status
        status="$($RUNTIME exec "$container" \
            redis-cli ${redis_pass:+-a "$redis_pass" --no-auth-warning} LASTSAVE 2>/dev/null || echo 0)"
        sleep 1
        local status2
        status2="$($RUNTIME exec "$container" \
            redis-cli ${redis_pass:+-a "$redis_pass" --no-auth-warning} LASTSAVE 2>/dev/null || echo 0)"
        if [[ "$status2" != "$status" ]] || [[ "$i" -ge 5 ]]; then
            break
        fi
    done
    success "Redis flush complete"
}

# ── Detect which stack is active ──────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"

# Compose stack: check for any of the known service containers
COMPOSE_SERVICES=(
    studybuddy_ondemand-api-1
    studybuddy_ondemand-web-1
    studybuddy_ondemand-celery-worker-1
    studybuddy_ondemand-db-1
)
BARE_SERVICES=(sb-db sb-redis sb-test-db)

detect_stack() {
    # Try Compose project containers first (docker compose ps -q gives container IDs)
    if [[ -f "$COMPOSE_FILE" ]]; then
        local running
        running="$(cd "$REPO_ROOT" && $RUNTIME compose ps -q 2>/dev/null | wc -l | tr -d ' ')"
        if [[ "$running" -gt 0 ]]; then
            echo "compose"
            return
        fi
    fi
    # Fall back to bare containers
    for c in "${BARE_SERVICES[@]}"; do
        if $RUNTIME inspect "$c" &>/dev/null; then
            echo "bare"
            return
        fi
    done
    echo "none"
}

STACK="$(detect_stack)"

# ── Compose shutdown ──────────────────────────────────────────────────────────
shutdown_compose() {
    step "Docker Compose graceful shutdown"
    cd "$REPO_ROOT"

    # Resolve actual container names from Compose project
    resolve() { $RUNTIME compose ps -q "$1" 2>/dev/null | head -1; }

    # ── 1. Stripe CLI (no state, stop immediately) ────────────────────────────
    step "1/8  Stripe CLI"
    local stripe_id; stripe_id="$(resolve stripe-cli)"
    [[ -n "$stripe_id" ]] && { $RUNTIME stop -t 5 "$stripe_id" 2>/dev/null || true; success "stripe-cli stopped"; } \
                           || info "stripe-cli not running"

    # ── 2. Celery Beat (stop scheduling before workers drain) ─────────────────
    step "2/8  Celery Beat schedulers"
    for svc in celery-beat-standby celery-beat-primary; do
        local id; id="$(resolve "$svc")"
        [[ -n "$id" ]] && stop_service "$id" 15 || info "$svc not running"
    done

    # ── 3. Celery workers — drain in-flight tasks ─────────────────────────────
    step "3/8  Celery workers"
    if [[ "$FORCE" == "true" ]]; then
        warn "--force: skipping drain; stopping Celery workers immediately"
        for svc in celery-pipeline celery-worker; do
            local id; id="$(resolve "$svc")"
            [[ -n "$id" ]] && stop_service "$id" 10 || info "$svc not running"
        done
    else
        info "Sending warm shutdown (SIGTERM) to Celery workers — waiting up to 60s for tasks to drain ..."
        for svc in celery-pipeline celery-worker; do
            local id; id="$(resolve "$svc")"
            if [[ -n "$id" ]] && $RUNTIME inspect "$id" --format "{{.State.Running}}" 2>/dev/null | grep -q "^true"; then
                $RUNTIME kill -s SIGTERM "$id" 2>/dev/null || true
            fi
        done
        # Poll until workers exit or timeout
        local elapsed=0
        while [[ $elapsed -lt 60 ]]; do
            local all_done=true
            for svc in celery-pipeline celery-worker; do
                local id; id="$(resolve "$svc")"
                if [[ -n "$id" ]] && $RUNTIME inspect "$id" --format "{{.State.Running}}" 2>/dev/null | grep -q "^true"; then
                    all_done=false
                fi
            done
            $all_done && break
            sleep 2; elapsed=$((elapsed + 2))
            [[ $((elapsed % 10)) -eq 0 ]] && info "  ... waiting for Celery (${elapsed}s elapsed)"
        done
        if [[ $elapsed -ge 60 ]]; then
            warn "Celery workers did not drain within 60s — forcing stop"
        fi
        for svc in celery-pipeline celery-worker; do
            local id; id="$(resolve "$svc")"
            [[ -n "$id" ]] && { $RUNTIME stop -t 5 "$id" 2>/dev/null || true; success "$svc stopped"; } \
                           || true
        done
    fi

    # ── 4. Web (Next.js) ──────────────────────────────────────────────────────
    step "4/8  Web (Next.js)"
    local web_id; web_id="$(resolve web)"
    [[ -n "$web_id" ]] && stop_service "$web_id" 15 || info "web not running"

    # ── 5. API (FastAPI / uvicorn) ────────────────────────────────────────────
    step "5/8  API (FastAPI)"
    local api_id; api_id="$(resolve api)"
    [[ -n "$api_id" ]] && stop_service "$api_id" 30 || info "api not running"

    # ── 6. PgBouncer ─────────────────────────────────────────────────────────
    step "6/8  PgBouncer"
    local pgb_id; pgb_id="$(resolve pgbouncer)"
    [[ -n "$pgb_id" ]] && stop_service "$pgb_id" 10 || info "pgbouncer not running"

    # ── 7. Redis — flush AOF then stop ───────────────────────────────────────
    step "7/8  Redis"
    local redis_id; redis_id="$(resolve redis)"
    if [[ -n "$redis_id" ]]; then
        flush_redis "$redis_id"
        stop_service "$redis_id" 15
    else
        info "redis not running"
    fi

    # ── 8. PostgreSQL — always last ───────────────────────────────────────────
    step "8/8  PostgreSQL"
    local db_id; db_id="$(resolve db)"
    [[ -n "$db_id" ]] && stop_service "$db_id" 30 || info "db not running"

    echo ""
    success "All Compose services stopped. Data volumes preserved."
    echo -e "  Restart with: ${GREEN}docker compose up -d${NC}"
}

# ── Bare-container shutdown (dev_start.sh mode) ───────────────────────────────
shutdown_bare() {
    step "Bare-container graceful shutdown"

    # ── 1. Redis — flush then stop ────────────────────────────────────────────
    step "1/3  Redis"
    if is_running sb-redis; then
        flush_redis sb-redis
        stop_service sb-redis 15
    else
        info "sb-redis not running"
    fi

    # ── 2. PostgreSQL ─────────────────────────────────────────────────────────
    step "2/3  PostgreSQL (dev)"
    stop_service sb-db 30

    # ── 3. Test PostgreSQL ────────────────────────────────────────────────────
    step "3/3  PostgreSQL (test)"
    stop_service sb-test-db 15

    # Kill any stray uvicorn process bound to port 8000
    if command -v lsof &>/dev/null; then
        local uvicorn_pids
        uvicorn_pids="$(lsof -ti tcp:8000 2>/dev/null || true)"
        if [[ -n "$uvicorn_pids" ]]; then
            info "Stopping uvicorn (PID(s): $uvicorn_pids) ..."
            echo "$uvicorn_pids" | xargs kill -TERM 2>/dev/null || true
            sleep 2
            # Force-kill if still running
            local remaining
            remaining="$(lsof -ti tcp:8000 2>/dev/null || true)"
            [[ -n "$remaining" ]] && echo "$remaining" | xargs kill -KILL 2>/dev/null || true
            success "uvicorn stopped"
        fi
    fi

    echo ""
    success "All bare containers stopped. Data volumes preserved."
    echo -e "  Restart with: ${GREEN}./dev_start.sh${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}StudyBuddy OnDemand — Graceful Shutdown${NC}"
[[ "$FORCE" == "true" ]] && warn "Force mode enabled — skipping task drain"
echo ""

case "$STACK" in
    compose)
        info "Detected: docker-compose stack"
        shutdown_compose
        ;;
    bare)
        info "Detected: bare containers (dev_start.sh mode)"
        shutdown_bare
        ;;
    none)
        info "No running StudyBuddy services detected."
        ;;
esac
