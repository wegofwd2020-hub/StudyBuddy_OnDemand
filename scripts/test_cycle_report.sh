#!/usr/bin/env bash
# Draft section 1 of a test-cycle report — a Markdown table of [Feedback] issues
# and their state. Add the fixing PR # to each row by hand (see the closed issue).
#
# Usage:
#   scripts/test_cycle_report.sh                 # all [Feedback] issues
#   scripts/test_cycle_report.sh cycle:2026-06-13  # scoped to a cycle label or milestone
#
# Requires: gh (authenticated). See docs/test-cycles/README.md for the full process.
set -euo pipefail

REPO="${REPO:-wegofwd2020-hub/StudyBuddy_OnDemand}"
SCOPE="${1:-}"

# Build the gh search query: always match the [Feedback] title prefix; optionally
# AND a label/milestone scope (e.g. cycle:2026-06-13 or milestone:"Cycle 2026-06-13").
SEARCH='[Feedback] in:title'
if [ -n "$SCOPE" ]; then
  case "$SCOPE" in
    label:*|milestone:*) SEARCH="$SEARCH $SCOPE" ;;
    *)                   SEARCH="$SEARCH label:$SCOPE" ;;
  esac
fi

echo "<!-- generated from: gh issue list --search \"$SEARCH\" -->"
echo
echo "| # | Status | Issue | Fix / Notes |"
echo "|---|---|---|---|"
gh issue list --repo "$REPO" --state all --search "$SEARCH" --limit 300 \
  --json number,state,title \
  -q 'sort_by(.number)[]
      | "| #\(.number) | \(if .state=="CLOSED" then "✅/⚠️ CLOSED" else "🟡 OPEN" end) | \(.title | sub("^\\[Feedback\\] ";"")) | _(fill in: PR # / why)_ |"'
