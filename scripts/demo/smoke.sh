#!/usr/bin/env bash
# =============================================================================
# scripts/demo/smoke.sh — post-deploy smoke check
#
# Curl-based infrastructure smoke for a deployed demo environment. Run after
# every deploy (auto-deploy CI calls it; operator can run it manually).
#
# Usage:
#   bash scripts/demo/smoke.sh                             # default: localhost
#   bash scripts/demo/smoke.sh https://demo.usestudybuddy.com
#   bash scripts/demo/smoke.sh https://staging.usestudybuddy.com
#
# Exit codes:
#   0 — every check passed
#   1 — at least one check failed; failure summary printed at the end
#
# Checks performed (~5 seconds total):
#   - GET  /healthz                                                   (200, "status":"ok")
#   - GET  /readyz                                                    (200, db+redis ok)
#   - POST /api/v1/admin/auth/login    (bad creds)                    (401, proves endpoint mounted)
#   - POST /api/v1/auth/universal-login (bad creds)                   (401, proves unified endpoint mounted + RLS-bypass works)
#   - HEAD /content/curricula/default-2026-g11-science/G11-BIO-001/lesson_en.json
#                                              (200, served by nginx alias)
#   - HEAD /sample-visuals/G11-BIO-001/bacteriophage-anatomy.svg      (200, tutorial SVG)
#   - HEAD /sample-visuals/G11-BIO-001/Diversity_TaxonomicHierarchy.mp4
#                                              (200, tutorial MP4 — catches the gitignored
#                                               sample-visuals tree if rsync was skipped)
#   - GET  /                                                          (200, web up, HTML)
#   - GET  /signin                                                    (200, unified sign-in page)
#
# Scope note: auth checks intentionally verify endpoint *shape* (401 on bad
# creds) rather than logging in with seeded credentials. Seeded school-
# provisioned users (Sam Houston, Anya Iyer, etc.) carry first_login=TRUE
# and have passwords rotated on first portal use, so a credentialed check
# cannot pass reliably from CI. End-to-end persona walkthroughs belong in
# the demo runbook (docs/DEMO_LAUNCH_PLAN.md §4), not in the deploy gate.
# =============================================================================

set -uo pipefail   # not -e: we want to collect failures, not abort on first

BASE_URL="${1:-http://localhost:3000}"
API_URL="${BASE_URL%/}/api/v1"

# Deliberately invalid credentials for endpoint-shape checks. The smoke
# expects 401 (auth rejected) — not 404 (route missing) or 5xx (handler
# broken). Email must be syntactically valid (Pydantic EmailStr rejects
# .invalid as a reserved TLD, returning 422 instead of 401). example.com
# is the RFC 2606 reserved domain — guaranteed to never resolve to a real
# mailbox. The "smoke-check" prefix is searchable in API logs.
BAD_EMAIL="smoke-check-nonexistent@example.com"
BAD_PASSWORD="smoke-check-not-a-real-password"

# ── Output helpers ─────────────────────────────────────────────────────────
bold="\033[1m"; green="\033[0;32m"; red="\033[0;31m"; reset="\033[0m"
declare -a FAILURES=()

pass() { echo -e "  ${green}✓${reset} $1"; }
fail() { echo -e "  ${red}✗${reset} $1 — $2"; FAILURES+=("$1: $2"); }

# Curl wrapper: emits HTTP status code + body to stdout (separated by ::status::).
# Times out after 10 seconds.
http_get() {
  local url="$1"
  local extra_args=("${@:2}")
  curl -s -m 10 -w '::status::%{http_code}' "${extra_args[@]}" "$url" 2>&1
}

http_head() {
  local url="$1"
  curl -s -m 10 -o /dev/null -w '%{http_code}' -I "$url" 2>&1
}

http_post() {
  local url="$1"
  local body="$2"
  local extra_args=("${@:3}")
  curl -s -m 10 -w '::status::%{http_code}' -X POST \
    -H "Content-Type: application/json" \
    -d "$body" \
    "${extra_args[@]}" "$url" 2>&1
}

extract_status() { echo "$1" | sed -E 's/.*::status::([0-9]+)$/\1/' ; }
extract_body()   { echo "$1" | sed -E 's/::status::[0-9]+$//' ; }

echo ""
echo "${bold}=== StudyBuddy demo smoke check ===${reset}"
echo "    target: $BASE_URL"
echo ""

# ── Liveness ────────────────────────────────────────────────────────────────
# Note: /healthz and /readyz are mounted at the API root, NOT under /api/v1.
# Hit them via $BASE_URL directly. The previous "$API_URL/../healthz" form
# was sent verbatim by curl (no client-side path normalisation), and Cloudflare/
# nginx routed `/api/v1/../healthz` to the Next.js web container, which 404'd.
echo "Liveness:"
RESP=$(http_get "$BASE_URL/healthz")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qE '"status".*"ok"'; then
  pass "GET /healthz returns 200 with status ok"
else
  fail "GET /healthz" "status=$STATUS body=${BODY:0:80}"
fi

RESP=$(http_get "$BASE_URL/readyz")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -q '"db":"ok"' && echo "$BODY" | grep -q '"redis":"ok"'; then
  pass "GET /readyz returns 200 with db+redis ok"
else
  fail "GET /readyz" "status=$STATUS body=${BODY:0:120}"
fi

# ── Auth endpoint shape ─────────────────────────────────────────────────────
# Verify the two password-based auth endpoints are mounted and reject bad
# credentials with 401. We do NOT attempt to log in with seeded credentials:
# school-provisioned demo users (Sam Houston, Anya Iyer, etc.) carry
# first_login=TRUE and have their passwords rotated on first portal use,
# so any creds we bake in here drift the moment someone uses the demo.
# A 401 proves the endpoint is mounted, the DB/RLS-bypass works, and bcrypt
# runs — which is what a deploy gate needs. End-to-end auth is the demo
# walkthrough's job, not this script's.
echo ""
echo "Auth endpoint shape (bad creds → expect 401):"
RESP=$(http_post "$API_URL/admin/auth/login" \
  "{\"email\":\"$BAD_EMAIL\",\"password\":\"$BAD_PASSWORD\"}")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "401" ]]; then
  pass "POST /admin/auth/login rejects bad creds with 401"
else
  fail "POST /admin/auth/login" "expected 401 got status=$STATUS body=${BODY:0:120}"
fi

RESP=$(http_post "$API_URL/auth/universal-login" \
  "{\"email\":\"$BAD_EMAIL\",\"password\":\"$BAD_PASSWORD\"}")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "401" ]]; then
  pass "POST /auth/universal-login rejects bad creds with 401"
else
  fail "POST /auth/universal-login" "expected 401 got status=$STATUS body=${BODY:0:120}"
fi

# ── Static content delivery (rsync targets) ────────────────────────────────
# Catches:
#   - operator forgot to rsync content_store_data/ (lesson JSON 404)
#   - operator forgot to rsync web/public/sample-visuals/ (tutorial videos 404 —
#     this tree is gitignored so it's NOT in the Docker image)
#   - nginx /content/ or /sample-visuals/ location blocks missing on a fresh box
echo ""
echo "Static content delivery:"

LESSON_URL="$BASE_URL/content/curricula/default-2026-g11-science/G11-BIO-001/lesson_en.json"
STATUS=$(http_head "$LESSON_URL")
if [[ "$STATUS" == "200" ]]; then
  pass "HEAD /content/.../G11-BIO-001/lesson_en.json returns 200"
else
  fail "HEAD lesson_en.json" "status=$STATUS — is content_store_data/ rsync'd to /data/content/?"
fi

SVG_URL="$BASE_URL/sample-visuals/G11-BIO-001/bacteriophage-anatomy.svg"
STATUS=$(http_head "$SVG_URL")
if [[ "$STATUS" == "200" ]]; then
  pass "HEAD /sample-visuals/G11-BIO-001/bacteriophage-anatomy.svg returns 200"
else
  fail "HEAD tutorial SVG" "status=$STATUS — is web/public/sample-visuals/ rsync'd to /data/sample-visuals/?"
fi

MP4_URL="$BASE_URL/sample-visuals/G11-BIO-001/Diversity_TaxonomicHierarchy.mp4"
STATUS=$(http_head "$MP4_URL")
if [[ "$STATUS" == "200" ]]; then
  pass "HEAD /sample-visuals/G11-BIO-001/Diversity_TaxonomicHierarchy.mp4 returns 200"
else
  fail "HEAD tutorial MP4" "status=$STATUS — sample-visuals tree is gitignored; rsync from web/public/sample-visuals/"
fi

# ── Web frontend ────────────────────────────────────────────────────────────
echo ""
echo "Web frontend:"
RESP=$(http_get "$BASE_URL/")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qiE 'studybuddy|<title|html'; then
  pass "GET / returns 200 and HTML"
else
  fail "GET /" "status=$STATUS"
fi

# /signin replaced /demo as the unified sign-in landing in the 2026-05
# universal-login migration (see docs/DEMO_LAUNCH_PLAN.md §1.A). The bare
# /demo path no longer has a page.tsx and 404s; the surviving routes are
# /demo/login, /demo/student-story, /demo/teacher, etc. — none of which
# we want as the canonical "demo is up" signal.
RESP=$(http_get "$BASE_URL/signin")
STATUS=$(extract_status "$RESP")
if [[ "$STATUS" == "200" ]]; then
  pass "GET /signin returns 200"
else
  fail "GET /signin" "status=$STATUS"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo -e "${green}${bold}══ all smoke checks passed ══${reset}"
  exit 0
else
  echo -e "${red}${bold}══ ${#FAILURES[@]} smoke check(s) failed ══${reset}"
  for f in "${FAILURES[@]}"; do
    echo -e "  ${red}•${reset} $f"
  done
  exit 1
fi
