#!/usr/bin/env bash
# =============================================================================
# scripts/demo/sync-content.sh — push pre-built content to a demo / staging VPS
#
# What it does (one command, in order):
#   1. Pre-flight — verifies the local trees exist, docker compose is up
#      (for the inject step), and SSH to the target host works.
#   2. Inject G11 visuals — runs scripts/inject_g11_visuals.py inside the
#      celery-pipeline container so the G11 Science tutorials in
#      content_store_data/curricula/default-2026-g11-science/G11-*/ pick up
#      the SVGs from sample_content/g11-science/ + the MP4 references in
#      UNIT_VIDEOS. Idempotent. Skip with --skip-inject.
#   3. Rsync content_store_data/ → /data/content/ on the VPS
#      (TEXT — lesson/quiz/tutorial JSON + GRAPHICS — visuals/_legacy SVGs +
#       audio MP3).
#   4. Rsync web/public/sample-visuals/ → /data/sample-visuals/ on the VPS
#      (VIDEO — 44 tutorial MP4s, ~219 MB; gitignored so this is the only
#       way they land on the box).
#   5. Optional — run smoke.sh against the public URL if --smoke <url> is
#      passed.
#
# Usage:
#   bash scripts/demo/sync-content.sh deploy@staging.studybuddy.app
#   bash scripts/demo/sync-content.sh deploy@demo.studybuddy.app
#   bash scripts/demo/sync-content.sh --dry-run deploy@staging.studybuddy.app
#   bash scripts/demo/sync-content.sh --skip-inject deploy@demo.studybuddy.app
#   bash scripts/demo/sync-content.sh --smoke https://demo.studybuddy.app deploy@demo.studybuddy.app
#
# Exit codes:
#   0 — every step succeeded
#   1 — pre-flight failed
#   2 — inject failed
#   3 — content rsync failed
#   4 — sample-visuals rsync failed
#   5 — smoke check failed
# =============================================================================

set -uo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
DO_INJECT=1
DRY_RUN=0
SMOKE_URL=""
TARGET=""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTENT_LOCAL="$REPO_ROOT/content_store_data"
VISUALS_LOCAL="$REPO_ROOT/web/public/sample-visuals"

# ── Arg parsing ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-inject) DO_INJECT=0; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --smoke)       SMOKE_URL="$2"; shift 2 ;;
    -h|--help)
      cat <<'USAGE'
sync-content.sh — push pre-built demo content to a VPS

Usage:
  bash scripts/demo/sync-content.sh [flags] user@host

Flags:
  --skip-inject     Don't run scripts/inject_g11_visuals.py (use if you've
                    already injected, or you don't have the local stack up)
  --dry-run         Pass --dry-run to both rsyncs (no remote writes)
  --smoke <url>     After both rsyncs succeed, run smoke.sh <url>
  -h, --help        Print this message

Steps performed (in order):
  1. Pre-flight (local trees exist, docker up if injecting, SSH works)
  2. Inject G11 visuals via celery-pipeline (skip with --skip-inject)
  3. rsync content_store_data/        → /data/content/
  4. rsync web/public/sample-visuals/ → /data/sample-visuals/
  5. Optional smoke (only if --smoke <url>)
USAGE
      exit 0 ;;
    -*)
      echo "Unknown flag: $1" >&2
      exit 1 ;;
    *)
      if [[ -n "$TARGET" ]]; then
        echo "Multiple targets specified ($TARGET, $1) — pass exactly one user@host" >&2
        exit 1
      fi
      TARGET="$1"; shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [--skip-inject] [--dry-run] [--smoke <url>] user@host" >&2
  exit 1
fi

# ── Output helpers ──────────────────────────────────────────────────────────
bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"; red="\033[0;31m"; reset="\033[0m"
step() { echo -e "\n${bold}━━ $* ━━${reset}"; }
ok()   { echo -e "  ${green}✓${reset} $*"; }
warn() { echo -e "  ${yellow}!${reset} $*"; }
die()  { local code="$1"; shift; echo -e "  ${red}✗${reset} $*" >&2; exit "$code"; }

# ── Step 1: pre-flight ──────────────────────────────────────────────────────
step "1/5  Pre-flight"

[[ -d "$CONTENT_LOCAL" ]] || die 1 "missing $CONTENT_LOCAL — run pipeline locally first"
ok "found $CONTENT_LOCAL ($(du -sh "$CONTENT_LOCAL" | cut -f1))"

[[ -d "$VISUALS_LOCAL" ]] || die 1 "missing $VISUALS_LOCAL — tutorial videos won't land on the VPS"
ok "found $VISUALS_LOCAL ($(du -sh "$VISUALS_LOCAL" | cut -f1), $(find "$VISUALS_LOCAL" -name '*.mp4' | wc -l) MP4s)"

if [[ "$DO_INJECT" -eq 1 ]]; then
  if ! docker compose ps celery-pipeline 2>/dev/null | grep -q "Up"; then
    die 1 "celery-pipeline isn't running — start the local stack first (./dev_start.sh) or pass --skip-inject"
  fi
  ok "celery-pipeline is up (needed for visual inject)"
fi

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$TARGET" 'true' 2>/dev/null; then
  die 1 "can't SSH to $TARGET — check the host is up, your SSH key is loaded (ssh-add -l), and authorized_keys is set on the box"
fi
ok "SSH to $TARGET works"

# ── Step 2: inject ──────────────────────────────────────────────────────────
if [[ "$DO_INJECT" -eq 1 ]]; then
  step "2/5  Inject G11 visuals into content store"
  if ! docker compose exec -T celery-pipeline python /app/scripts-repo/inject_g11_visuals.py; then
    die 2 "inject_g11_visuals.py failed — see output above"
  fi
  ok "G11 visuals injected"
else
  step "2/5  Inject (skipped via --skip-inject)"
fi

# ── Step 3: rsync content_store_data → /data/content ────────────────────────
step "3/5  Rsync content_store_data/ → /data/content/ on $TARGET"
RSYNC_FLAGS=(-avz --delete --human-readable --info=stats2)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_FLAGS+=(--dry-run)
  warn "DRY-RUN — no bytes will be written remotely"
fi
if ! rsync "${RSYNC_FLAGS[@]}" "$CONTENT_LOCAL/" "$TARGET:/data/content/"; then
  die 3 "content_store_data rsync failed — check that /data/content exists on the VPS (provision.sh step 7) and the deploy user owns it"
fi
ok "content rsync complete"

# ── Step 4: rsync web/public/sample-visuals → /data/sample-visuals ──────────
step "4/5  Rsync web/public/sample-visuals/ → /data/sample-visuals/ on $TARGET"
if ! rsync "${RSYNC_FLAGS[@]}" "$VISUALS_LOCAL/" "$TARGET:/data/sample-visuals/"; then
  die 4 "sample-visuals rsync failed — check that /data/sample-visuals exists on the VPS (provision.sh step 7) and the deploy user owns it"
fi
ok "sample-visuals rsync complete (44 MP4s + supporting SVGs)"

# ── Step 5: optional smoke ──────────────────────────────────────────────────
if [[ -n "$SMOKE_URL" ]]; then
  step "5/5  Smoke check against $SMOKE_URL"
  if ! bash "$REPO_ROOT/scripts/demo/smoke.sh" "$SMOKE_URL"; then
    die 5 "smoke check failed — inspect output above; the 3 static-content HEAD checks tell you which rsync target the VPS can't serve"
  fi
  ok "smoke passed"
else
  step "5/5  Smoke (skipped — pass --smoke <url> to run)"
  echo "    bash $REPO_ROOT/scripts/demo/smoke.sh https://your-host"
fi

echo -e "\n${green}${bold}══ content sync complete ══${reset}"
