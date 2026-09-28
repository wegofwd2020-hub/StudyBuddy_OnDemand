#!/bin/bash
# =============================================================================
# Signin Debug Script — Capture browser logs during form submission
#
# This script sets up Playwright and captures console/network logs while
# testing the signin form. Useful for debugging "Sign in" button disabled
# or form submission issues.
#
# Usage:
#   ./scripts/run-signin-debug.sh [URL] [email] [password]
#
# Examples:
#   ./scripts/run-signin-debug.sh                    # Uses defaults
#   ./scripts/run-signin-debug.sh http://localhost/signin
#   ./scripts/run-signin-debug.sh https://demo.usestudybuddy.com/signin test@example.com pass123
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
URL="${1:-http://localhost/signin}"
EMAIL="${2:-student@demo.example.com}"
PASSWORD="${3:-DemoPass123}"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         📊 StudyBuddy Signin Debug Log Capture                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔗 URL:      $URL"
echo "📧 Email:    $EMAIL"
echo "🔒 Password: $(printf '*%.0s' $(seq 1 ${#PASSWORD}))"
echo ""

# Check if node_modules exists
if [ ! -d "$PROJECT_ROOT/node_modules" ]; then
    echo "⚠️  Playwright not installed. Installing..."
    echo ""
    cd "$PROJECT_ROOT"
    npm install playwright
    echo ""
fi

# Check if the capture script exists
if [ ! -f "$SCRIPT_DIR/capture-signin-logs.js" ]; then
    echo "❌ Error: capture-signin-logs.js not found"
    exit 1
fi

echo "🚀 Starting signin debug capture..."
echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# Run the capture script
cd "$PROJECT_ROOT"
node "$SCRIPT_DIR/capture-signin-logs.js" "$URL" "$EMAIL" "$PASSWORD"

echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "✅ Debug capture complete!"
echo ""
echo "📍 Logs saved in current directory as: signin-logs-*.json"
echo ""
echo "📖 Next steps:"
echo "   1. Check the console logs above for [universalLogin] messages"
echo "   2. Look for network requests to /auth/universal-login"
echo "   3. Note any error messages"
echo "   4. Share the JSON file or console output for analysis"
echo ""
