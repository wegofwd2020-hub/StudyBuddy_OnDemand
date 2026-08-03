#!/usr/bin/env bash
# =============================================================================
# scripts/quiz_suite.sh — the quiz testing suite (see
# docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md)
#
#   ./scripts/quiz_suite.sh              # everything
#   ./scripts/quiz_suite.sh --api-only
#   ./scripts/quiz_suite.sh --browser-only
#   ./scripts/quiz_suite.sh --keep       # leave the fixture in place
#
# Exit codes: 0 pass · 1 test failure · 2 environment problem.
# =============================================================================
set -uo pipefail

API_ONLY=0; BROWSER_ONLY=0; KEEP=0; VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --api-only) API_ONLY=1 ;;
    --browser-only) BROWSER_ONLY=1 ;;
    --keep) KEEP=1 ;;
    -v|--verbose) VERBOSE=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
FIXTURE_WEB="web/tests/e2e/quiz-suite/.fixture.json"
# NO -e TEST_DB_URL= here. backend/tests/conftest.py downgrades to base at
# session end; blanking TEST_DB_URL points that at the DEV database and drops
# every table. The suite lives outside backend/tests/ so that conftest never
# applies, and seed.py reads DATABASE_URL, which is already the dev database.
DC_EXEC=(docker compose exec -T api)

RUN_START=$SECONDS
WARMUP_RESULT="skipped"

# ── Preflight ────────────────────────────────────────────────────────────────
# A suite that can't tell "your code is broken" from "your stack isn't running"
# costs more than it saves.
echo "→ preflight"
if ! docker compose ps --status running --services 2>/dev/null | grep -qx api; then
  echo "✗ the 'api' container is not running. Start the stack first:" >&2
  echo "    ./dev_start.sh" >&2
  exit 2
fi
if ! "${DC_EXEC[@]}" python -c "
import sys, urllib.request
try:
    urllib.request.urlopen('http://localhost:8000/readyz', timeout=5)
except Exception as exc:
    print(exc, file=sys.stderr); sys.exit(1)
" >/dev/null 2>&1; then
  echo "✗ the api container is up but /readyz reports the DB or Redis unreachable." >&2
  echo "    docker compose logs api --since 5m" >&2
  exit 2
fi
if [ "$API_ONLY" -eq 0 ]; then
  if ! docker compose ps --status running --services 2>/dev/null | grep -qx web; then
    echo "✗ the 'web' container is not running (needed for the browser tier)." >&2
    echo "    ./dev_start.sh   — or re-run with --api-only" >&2
    exit 2
  fi
  # Warm the quiz route. The web dev server's FIRST compile of
  # /quiz/[unit_id] is a Turbopack cold compile that can take MINUTES on a
  # slow filesystem — confirmed with a bare unauthenticated curl during
  # Task 7. Without this, the browser tier's 90s budget gets blown by the
  # compile, not by a real problem, and the run looks flaky instead of cold.
  # A plain unauthenticated GET is enough to trigger compilation; it doesn't
  # need to succeed (a redirect to /signin is expected), just force the
  # build. Any curl failure here (e.g. connection refused) is a real
  # environment problem, not a warm-up nicety, so it's fatal.
  echo "→ warming /quiz/[unit_id] (first Turbopack compile can take minutes)"
  warm_start=$SECONDS
  if warm_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 300 \
      "http://localhost:3000/quiz/__quiz_suite_warmup__"); then
    warm_elapsed=$((SECONDS - warm_start))
    WARMUP_RESULT="${warm_code} (${warm_elapsed}s)"
    echo "  ok — ${warm_code} in ${warm_elapsed}s"
  else
    echo "✗ could not reach the web dev server at http://localhost:3000 to warm the quiz route." >&2
    echo "    docker compose logs web --since 5m" >&2
    exit 2
  fi
fi
echo "  ok"

# ── Teardown always runs ─────────────────────────────────────────────────────
cleanup() {
  if [ "$KEEP" -eq 1 ]; then
    echo "→ --keep: leaving the fixture in place"
    return
  fi
  echo "→ teardown"
  "${DC_EXEC[@]}" python -m quiz_suite.seed teardown >/dev/null 2>&1 \
    || echo "  ⚠ teardown reported a problem; re-run with --keep and inspect"
  rm -f "$FIXTURE_WEB"
}
trap cleanup EXIT INT TERM

# ── Seed ─────────────────────────────────────────────────────────────────────
echo "→ seed"
if ! "${DC_EXEC[@]}" python -m quiz_suite.seed seed; then
  echo "✗ seeding failed" >&2
  exit 2
fi
mkdir -p "$(dirname "$FIXTURE_WEB")"
if ! docker compose cp api:/app/quiz_suite/.fixture.json "$FIXTURE_WEB" >/dev/null; then
  echo "✗ could not copy the fixture out of the api container — the browser tier" >&2
  echo "  would fail on a missing .fixture.json and misreport as a test failure." >&2
  echo "    docker compose logs api --since 5m" >&2
  exit 2
fi

API_RESULT="skipped"; BROWSER_RESULT="skipped"; FAILED=0
PYTEST_FLAGS="-q -rs"
[ "$VERBOSE" -eq 1 ] && PYTEST_FLAGS="-v -rs"

# ── API tier ─────────────────────────────────────────────────────────────────
if [ "$BROWSER_ONLY" -eq 0 ]; then
  echo "→ API tier"
  start=$SECONDS
  if "${DC_EXEC[@]}" python -m pytest quiz_suite -m quiz_live $PYTEST_FLAGS; then
    API_RESULT="pass ($((SECONDS - start))s)"
  else
    API_RESULT="FAIL ($((SECONDS - start))s)"; FAILED=1
  fi
fi

# ── Browser tier ─────────────────────────────────────────────────────────────
# QUIZ_SUITE=1 and --project=quiz-suite are ALWAYS passed together.
# `workers` in web/playwright.config.ts is a global config value keyed off
# QUIZ_SUITE — set it without the project filter and every other project
# (chromium, persona-*) would get serialised to one worker too.
if [ "$API_ONLY" -eq 0 ]; then
  echo "→ browser tier"
  start=$SECONDS
  # --reporter=line overrides (not merges with) the HTML+list reporters in
  # playwright.config.ts for THIS invocation only — chromium/persona-* runs
  # go through the config unchanged. Needed because web/playwright-report/
  # is root-owned on this host: the HTML reporter's EACCES write failure
  # otherwise dumps an unhandled Node stack trace into green output, which
  # defeats the whole point of a script whose exit code should be trustable
  # without eyeballing the output for red text.
  if (cd web && QUIZ_SUITE=1 npx playwright test --project=quiz-suite --reporter=line); then
    BROWSER_RESULT="pass ($((SECONDS - start))s)"
  else
    BROWSER_RESULT="FAIL ($((SECONDS - start))s)"; FAILED=1
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
TOTAL_ELAPSED=$((SECONDS - RUN_START))
echo
echo "──────────────────────────────────────────────"
printf "  Warm-up       %s\n" "$WARMUP_RESULT"
printf "  API tier      %s\n" "$API_RESULT"
printf "  Browser tier  %s\n" "$BROWSER_RESULT"
echo "──────────────────────────────────────────────"
printf "  Total         %ss" "$TOTAL_ELAPSED"
if [ "$TOTAL_ELAPSED" -gt 90 ]; then
  printf " (target is 90s — over budget, see breakdown above)\n"
else
  printf " (target is 90s — within budget)\n"
fi
echo "──────────────────────────────────────────────"
if [ "$FAILED" -eq 1 ]; then
  echo "  ✗ quiz suite FAILED"
  echo "    correlation ids in the output map to: docker compose logs api --since 10m"
  exit 1
fi
echo "  ✓ quiz suite passed"
exit 0
