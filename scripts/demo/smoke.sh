#!/usr/bin/env bash
# =============================================================================
# scripts/demo/smoke.sh — post-deploy smoke check
#
# Curl-based end-to-end smoke for a deployed demo environment. Run after
# every deploy (auto-deploy CI calls it; operator can run it manually).
#
# Usage:
#   bash scripts/demo/smoke.sh                             # default: localhost
#   bash scripts/demo/smoke.sh https://demo.studybuddy.app
#   bash scripts/demo/smoke.sh https://staging.studybuddy.app
#
# Exit codes:
#   0 — every check passed
#   1 — at least one check failed; failure summary printed at the end
#
# Checks performed (~10 seconds total):
#   - GET /healthz                                                    (200, db+redis ok)
#   - GET /readyz                                                     (200)
#   - POST /api/v1/admin/auth/login   (super admin)                   (200, returns token)
#   - POST /api/v1/auth/teacher/login (Sam Houston / school admin)    (200, returns token)
#   - POST /api/v1/auth/login         (Anya Iyer / G11 Commerce)      (200, returns token)
#   - GET  /api/v1/content/G8-MATH-001/lesson  (with student token)   (200, has sections)
#   - GET  /api/v1/content/G8-MATH-001/quiz/1  (with student token)   (200, has questions)
#   - GET  /                                                          (200, web up)
#   - GET  /demo                                                      (200, demo route)
#
# Credentials match DEMO_WALKTHROUGH.md §0; if the seed.sh script used a
# different password set, update the constants below.
# =============================================================================

set -uo pipefail   # not -e: we want to collect failures, not abort on first

BASE_URL="${1:-http://localhost:3000}"
API_URL="${BASE_URL%/}/api/v1"

# ── Persona credentials (must match seed scripts + DEMO_WALKTHROUGH §0) ────
ADMIN_EMAIL="wegofwd2020@gmail.com"
ADMIN_PASSWORD="Admin1234!"

TEACHER_EMAIL="sam.houston@milfordwaterford.edu"
TEACHER_PASSWORD="MWTeacher-Sam-2026!"

STUDENT_EMAIL="anya.iyer@milfordwaterford.edu"
STUDENT_PASSWORD="MWStudent-Anya-2026!"

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
echo "Liveness:"
RESP=$(http_get "$API_URL/../healthz")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qiE '"db".*"ok"|db.*ok'; then
  pass "GET /healthz returns 200 with db ok"
else
  fail "GET /healthz" "status=$STATUS body=${BODY:0:80}"
fi

RESP=$(http_get "$API_URL/../readyz")
STATUS=$(extract_status "$RESP")
if [[ "$STATUS" == "200" ]]; then
  pass "GET /readyz returns 200"
else
  fail "GET /readyz" "status=$STATUS"
fi

# ── Login: super admin ──────────────────────────────────────────────────────
echo ""
echo "Auth — super admin:"
RESP=$(http_post "$API_URL/admin/auth/login" \
  "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
ADMIN_TOKEN=""
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -q '"token"'; then
  ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
  pass "POST /admin/auth/login returns token (admin: $ADMIN_EMAIL)"
else
  fail "POST /admin/auth/login" "status=$STATUS body=${BODY:0:120}"
fi

# ── Login: school-admin teacher ─────────────────────────────────────────────
echo ""
echo "Auth — school-admin teacher (Sam Houston):"
RESP=$(http_post "$API_URL/auth/teacher/login" \
  "{\"email\":\"$TEACHER_EMAIL\",\"password\":\"$TEACHER_PASSWORD\"}")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qE '"token"|"access_token"'; then
  pass "POST /auth/teacher/login returns token ($TEACHER_EMAIL)"
else
  fail "POST /auth/teacher/login" "status=$STATUS body=${BODY:0:120}"
fi

# ── Login: student (G11 Commerce) ───────────────────────────────────────────
echo ""
echo "Auth — student (Anya Iyer / G11 Commerce):"
RESP=$(http_post "$API_URL/demo/auth/login" \
  "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"$STUDENT_PASSWORD\"}")
STATUS=$(extract_status "$RESP")
BODY=$(extract_body "$RESP")
STUDENT_TOKEN=""
if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qE '"token"|"access_token"'; then
  STUDENT_TOKEN=$(echo "$BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('access_token') or d.get('token'))
" 2>/dev/null)
  pass "POST /demo/auth/login returns token ($STUDENT_EMAIL)"
else
  fail "POST /demo/auth/login" "status=$STATUS body=${BODY:0:120}"
fi

# ── Content fetch (using student token) ─────────────────────────────────────
echo ""
echo "Content (with student token):"
if [[ -n "$STUDENT_TOKEN" ]]; then
  RESP=$(http_get "$API_URL/content/G8-MATH-001/lesson" \
    -H "Authorization: Bearer $STUDENT_TOKEN")
  STATUS=$(extract_status "$RESP")
  BODY=$(extract_body "$RESP")
  if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -qE '"sections"|"learning_objectives"'; then
    pass "GET /content/G8-MATH-001/lesson returns lesson body"
  else
    fail "GET /content/G8-MATH-001/lesson" "status=$STATUS body=${BODY:0:120}"
  fi

  RESP=$(http_get "$API_URL/content/G8-MATH-001/quiz/1" \
    -H "Authorization: Bearer $STUDENT_TOKEN")
  STATUS=$(extract_status "$RESP")
  BODY=$(extract_body "$RESP")
  if [[ "$STATUS" == "200" ]] && echo "$BODY" | grep -q '"questions"'; then
    pass "GET /content/G8-MATH-001/quiz/1 returns quiz body"
  else
    fail "GET /content/G8-MATH-001/quiz/1" "status=$STATUS body=${BODY:0:120}"
  fi
else
  fail "content fetch" "no student token (login above failed)"
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

RESP=$(http_get "$BASE_URL/demo")
STATUS=$(extract_status "$RESP")
if [[ "$STATUS" == "200" ]]; then
  pass "GET /demo returns 200"
else
  fail "GET /demo" "status=$STATUS"
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
