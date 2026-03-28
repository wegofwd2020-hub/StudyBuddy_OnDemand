#!/usr/bin/env bash
# =============================================================================
# run-tests.sh — StudyBuddy OnDemand Web Frontend Test Runner
# =============================================================================
# Runs the full Vitest unit test suite and (optionally) the Playwright E2E suite.
#
# Usage:
#   ./run-tests.sh                  # run unit tests only
#   ./run-tests.sh --e2e            # run unit tests + E2E tests
#   ./run-tests.sh --unit-only      # explicit unit-only (same as default)
#   ./run-tests.sh --filter <name>  # run a single test file by name pattern
#   ./run-tests.sh --watch          # run unit tests in watch mode
#   ./run-tests.sh --ci             # CI mode: no color, fail fast on first error
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve script location so it can be run from any directory
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
RUN_E2E=false
WATCH_MODE=false
CI_MODE=false
FILTER=""

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --e2e)         RUN_E2E=true ;;
    --unit-only)   RUN_E2E=false ;;
    --watch)       WATCH_MODE=true ;;
    --ci)          CI_MODE=true ;;
    --filter)
      shift
      FILTER="${1:-}"
      ;;
    -h|--help)
      sed -n '3,15p' "$0"   # print the usage block at top of file
      exit 0
      ;;
    *)
      echo "Unknown option: $1  (use --help for usage)" >&2
      exit 1
      ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Colour helpers (suppressed in CI mode)
# ---------------------------------------------------------------------------
if [[ "$CI_MODE" == "true" ]]; then
  bold=""  green=""  yellow=""  red=""  cyan=""  reset=""
else
  bold="\033[1m"
  green="\033[0;32m"
  yellow="\033[0;33m"
  red="\033[0;31m"
  cyan="\033[0;36m"
  reset="\033[0m"
fi

separator() { echo -e "${cyan}$(printf '─%.0s' {1..70})${reset}"; }

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
separator
echo -e "${bold}  StudyBuddy OnDemand — Test Runner${reset}"
echo -e "  Directory : $SCRIPT_DIR"
echo -e "  Date/Time : $(date '+%Y-%m-%d %H:%M:%S')"
separator

# ---------------------------------------------------------------------------
# Check node_modules
# ---------------------------------------------------------------------------
if [[ ! -d "node_modules" ]]; then
  echo -e "${yellow}[!] node_modules not found — running npm install first...${reset}"
  npm install --silent
fi

# ---------------------------------------------------------------------------
# Section 1: Unit tests (Vitest)
# ---------------------------------------------------------------------------
UNIT_EXIT=0

echo ""
echo -e "${bold}[1/2] Unit Tests (Vitest)${reset}"
separator

if [[ "$WATCH_MODE" == "true" ]]; then
  echo -e "${yellow}Running in watch mode — press q to quit${reset}"
  npm run test:watch -- ${FILTER:+$FILTER} || UNIT_EXIT=$?
else
  VITEST_ARGS="--reporter=verbose"
  [[ "$CI_MODE" == "true" ]] && VITEST_ARGS="$VITEST_ARGS --no-color"

  if [[ -n "$FILTER" ]]; then
    echo -e "  Filter    : ${cyan}$FILTER${reset}"
    npm run test -- $FILTER $VITEST_ARGS || UNIT_EXIT=$?
  else
    npm run test -- $VITEST_ARGS || UNIT_EXIT=$?
  fi
fi

if [[ $UNIT_EXIT -eq 0 ]]; then
  echo -e "\n${green}✓ Unit tests passed${reset}"
else
  echo -e "\n${red}✗ Unit tests FAILED (exit $UNIT_EXIT)${reset}"
fi

# ---------------------------------------------------------------------------
# Section 2: E2E tests (Playwright) — opt-in only
# ---------------------------------------------------------------------------
E2E_EXIT=0

echo ""
echo -e "${bold}[2/2] E2E Tests (Playwright)${reset}"
separator

if [[ "$RUN_E2E" == "true" ]]; then
  if ! command -v npx &>/dev/null; then
    echo -e "${red}[!] npx not found — skipping E2E${reset}"
    E2E_EXIT=1
  else
    E2E_ARGS=""
    [[ "$CI_MODE" == "true" ]] && E2E_ARGS="--reporter=list"
    [[ -n "$FILTER" ]] && E2E_ARGS="$E2E_ARGS --grep $FILTER"

    npm run test:e2e -- $E2E_ARGS || E2E_EXIT=$?

    if [[ $E2E_EXIT -eq 0 ]]; then
      echo -e "\n${green}✓ E2E tests passed${reset}"
    else
      echo -e "\n${red}✗ E2E tests FAILED (exit $E2E_EXIT)${reset}"
    fi
  fi
else
  echo -e "  ${yellow}Skipped (pass --e2e to include Playwright tests)${reset}"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
separator
echo -e "${bold}  Summary${reset}"
separator

OVERALL_EXIT=0

if [[ $UNIT_EXIT -eq 0 ]]; then
  echo -e "  Unit tests  : ${green}PASSED${reset}"
else
  echo -e "  Unit tests  : ${red}FAILED${reset}"
  OVERALL_EXIT=1
fi

if [[ "$RUN_E2E" == "true" ]]; then
  if [[ $E2E_EXIT -eq 0 ]]; then
    echo -e "  E2E tests   : ${green}PASSED${reset}"
  else
    echo -e "  E2E tests   : ${red}FAILED${reset}"
    OVERALL_EXIT=1
  fi
else
  echo -e "  E2E tests   : ${yellow}SKIPPED${reset}"
fi

separator
if [[ $OVERALL_EXIT -eq 0 ]]; then
  echo -e "  ${green}${bold}All tests passed ✓${reset}"
else
  echo -e "  ${red}${bold}One or more suites failed ✗${reset}"
fi
separator
echo ""

exit $OVERALL_EXIT
