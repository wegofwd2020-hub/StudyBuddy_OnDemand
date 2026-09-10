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
#   3. Rsync content_store_data/ → /data/content/ on the VPS. ADD/UPDATE only:
#      deletion is opt-in via --prune, because the VPS legitimately holds
#      content this repo never had (school-uploaded visuals above all), and
#      visuals/ is protected from deletion even then.
#      (TEXT — lesson/quiz/tutorial JSON + GRAPHICS — visuals/_legacy SVGs +
#       audio MP3).
#   4. Rsync web/public/sample-visuals/ → /data/sample-visuals/ on the VPS
#      (VIDEO — 44 tutorial MP4s, ~219 MB; gitignored so this is the only
#       way they land on the box).
#   5. Invalidate the VPS's Redis content cache. Without this the box keeps
#      serving the PREVIOUS content JSON for up to CONTENT_TTL (3600s) after
#      the rsync, so a sync "succeeds" and changes nothing a student can see —
#      and half the units flip while the other half stay stale as keys expire
#      at different times. Performance rule #7 in CLAUDE.md.
#   6. Optional — run smoke.sh against the public URL if --smoke <url> is
#      passed.
#
# Usage:
#   bash scripts/demo/sync-content.sh deploy@staging.usestudybuddy.com
#   bash scripts/demo/sync-content.sh deploy@demo.usestudybuddy.com
#   bash scripts/demo/sync-content.sh --dry-run deploy@staging.usestudybuddy.com
#   bash scripts/demo/sync-content.sh --skip-inject deploy@demo.usestudybuddy.com
#   bash scripts/demo/sync-content.sh --skip-invalidate deploy@demo.usestudybuddy.com
#   bash scripts/demo/sync-content.sh --prune deploy@demo.usestudybuddy.com
#   bash scripts/demo/sync-content.sh --smoke https://demo.usestudybuddy.com deploy@demo.usestudybuddy.com
#
# Exit codes:
#   0 — every step succeeded
#   1 — pre-flight failed
#   2 — inject failed
#   3 — content rsync failed
#   4 — sample-visuals rsync failed
#   5 — cache invalidation failed (content IS on the box but may serve stale)
#   6 — smoke check failed
# =============================================================================

set -uo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
DO_INJECT=1
DO_INVALIDATE=1
DRY_RUN=0
PRUNE=0
SMOKE_URL=""
TARGET=""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTENT_LOCAL="$REPO_ROOT/content_store_data"
VISUALS_LOCAL="$REPO_ROOT/web/public/sample-visuals"

# ── Arg parsing ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-inject) DO_INJECT=0; shift ;;
    --skip-invalidate) DO_INVALIDATE=0; shift ;;
    --prune)       PRUNE=1; shift ;;
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
  --skip-invalidate Don't clear the VPS Redis content cache after syncing.
                    Only safe if you know nothing changed — otherwise the box
                    serves the old JSON until the keys expire (up to 1 hour).
  --prune           Also DELETE remote files that no longer exist locally.
                    Off by default: the VPS legitimately holds content this
                    repo never had -- school-uploaded visuals above all. Even
                    with --prune, visuals/ is protected and never removed.
  --dry-run         Pass --dry-run to both rsyncs (no remote writes)
  --smoke <url>     After both rsyncs succeed, run smoke.sh <url>
  -h, --help        Print this message

Steps performed (in order):
  1. Pre-flight (local trees exist, docker up if injecting, SSH works)
  2. Inject G11 visuals via celery-pipeline (skip with --skip-inject)
  3. rsync content_store_data/        → /data/content/
  4. rsync web/public/sample-visuals/ → /data/sample-visuals/
  5. Invalidate the VPS Redis content cache (skip with --skip-invalidate)
  6. Optional smoke (only if --smoke <url>)
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
  echo "Usage: $0 [--skip-inject] [--skip-invalidate] [--prune] [--dry-run] [--smoke <url>] user@host" >&2
  exit 1
fi

# ── Output helpers ──────────────────────────────────────────────────────────
bold="\033[1m"; green="\033[0;32m"; yellow="\033[0;33m"; red="\033[0;31m"; reset="\033[0m"
step() { echo -e "\n${bold}━━ $* ━━${reset}"; }
ok()   { echo -e "  ${green}✓${reset} $*"; }
warn() { echo -e "  ${yellow}!${reset} $*"; }
die()  { local code="$1"; shift; echo -e "  ${red}✗${reset} $*" >&2; exit "$code"; }

# ── Step 1: pre-flight ──────────────────────────────────────────────────────
step "1/6  Pre-flight"

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
  step "2/6  Inject G11 visuals into content store"
  if ! docker compose exec -T celery-pipeline python /app/scripts-repo/inject_g11_visuals.py; then
    die 2 "inject_g11_visuals.py failed — see output above"
  fi
  ok "G11 visuals injected"
else
  step "2/6  Inject (skipped via --skip-inject)"
fi

# ── Step 3: rsync content_store_data → /data/content ────────────────────────
step "3/6  Rsync content_store_data/ → /data/content/ on $TARGET"
RSYNC_FLAGS=(-avz --human-readable --info=stats2)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_FLAGS+=(--dry-run)
  warn "DRY-RUN — no bytes will be written remotely"
fi

# `--delete` is OPT-IN, and it used to be the default. Measured against the live
# demo, the default would have removed:
#
#   visuals/<school_id>/.../screenshot-2026-06-14-201008.png   (2 schools' uploads)
#   curricula/default-2026-g10/G10-MATH-001/lesson_fr.json
#   141 files under curricula/default-2026-g8.old
#
# The visuals are uploaded THROUGH THE PRODUCT on the box — `content_store_data/
# visuals/` here holds only `_legacy`, so there is no local copy and the delete
# is one-way loss of user data on a live demo. A content sync should add and
# update; removing is a separate, deliberate act.
CONTENT_FLAGS=("${RSYNC_FLAGS[@]}")
if [[ "$PRUNE" -eq 1 ]]; then
  CONTENT_FLAGS+=(--delete)
  warn "--prune: remote files absent locally WILL be deleted (visuals/ still protected)"
fi
# Protect unconditionally, not just under --prune, so a future edit that adds
# --delete back cannot quietly take the uploads with it. `***` covers the
# directory and everything under it.
CONTENT_FLAGS+=(--filter='protect visuals/***')

if ! rsync "${CONTENT_FLAGS[@]}" "$CONTENT_LOCAL/" "$TARGET:/data/content/"; then
  die 3 "content_store_data rsync failed — check that /data/content exists on the VPS (provision.sh step 7) and the deploy user owns it"
fi
ok "content rsync complete"

# ── Step 4: rsync web/public/sample-visuals → /data/sample-visuals ──────────
step "4/6  Rsync web/public/sample-visuals/ → /data/sample-visuals/ on $TARGET"
VISUALS_FLAGS=("${RSYNC_FLAGS[@]}")
[[ "$PRUNE" -eq 1 ]] && VISUALS_FLAGS+=(--delete)
if ! rsync "${VISUALS_FLAGS[@]}" "$VISUALS_LOCAL/" "$TARGET:/data/sample-visuals/"; then
  die 4 "sample-visuals rsync failed — check that /data/sample-visuals exists on the VPS (provision.sh step 7) and the deploy user owns it"
fi
ok "sample-visuals rsync complete (44 MP4s + supporting SVGs)"

# ── Step 5: invalidate the VPS Redis content cache ──────────────────────────
#
# `get_content_file` caches every content JSON under
#   content:{curriculum_id}:{unit_id}:{filename}   TTL 3600
# so an rsync alone changes nothing a student sees until those keys expire —
# and they expire one by one, so the box serves a MIX of old and new for up to
# an hour. That is performance rule #7, and this script did not do it.
#
# Deletes the `content:*` prefix ONLY. Never FLUSHDB: the same Redis holds
# student sessions, rate-limit counters, entitlement/curriculum resolution and
# the per-session quiz-set pins that server-side grading depends on (pitfall
# #35) — flushing it would log every student out and misgrade quizzes in
# flight.
if [[ "$DO_INVALIDATE" -eq 1 && "$DRY_RUN" -eq 0 ]]; then
  step "5/6  Invalidate Redis content cache on $TARGET"

  # Runs on the VPS. The password is read from .env.demo there and never
  # leaves the box or appears in this script's output.
  DELETED=$(ssh "$TARGET" 'bash -s' <<'REMOTE' 2>/dev/null
set -uo pipefail
cd /opt/studybuddy 2>/dev/null || { echo "ERR_NO_DIR"; exit 1; }
PW=$(grep -m1 "^REDIS_PASSWORD=" .env.demo 2>/dev/null | cut -d= -f2- | tr -d "\"'"'"'")
[ -n "$PW" ] || { echo "ERR_NO_PW"; exit 1; }
DC=(sudo /usr/bin/docker compose -f docker-compose.yml -f docker-compose.demo.yml --env-file .env.demo)
# --scan is cursor-based, so this does not block Redis the way KEYS would.
KEYS=$("${DC[@]}" exec -T redis redis-cli -a "$PW" --no-auth-warning --scan --pattern "content:*" 2>/dev/null | tr -d "\r")
if [ -z "$KEYS" ]; then echo "0"; exit 0; fi
echo "$KEYS" | xargs -r -n 200 "${DC[@]}" exec -T redis redis-cli -a "$PW" --no-auth-warning DEL >/dev/null 2>&1
echo "$KEYS" | wc -l
REMOTE
  ) || true

  case "$DELETED" in
    ERR_NO_DIR) die 5 "/opt/studybuddy not found on $TARGET — is this the right host?" ;;
    ERR_NO_PW)  die 5 "couldn't read REDIS_PASSWORD from /opt/studybuddy/.env.demo on $TARGET" ;;
    ''|*[!0-9]*)
      die 5 "cache invalidation failed on $TARGET. The content IS synced but the box may serve stale JSON for up to an hour. Clear it by hand:
       ssh $TARGET
       cd /opt/studybuddy && PW=\$(grep -m1 ^REDIS_PASSWORD= .env.demo | cut -d= -f2-)
       sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml --env-file .env.demo \\
         exec -T redis redis-cli -a \"\$PW\" --no-auth-warning --scan --pattern 'content:*' \\
         | xargs -r -n 200 sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml \\
           --env-file .env.demo exec -T redis redis-cli -a \"\$PW\" --no-auth-warning DEL" ;;
    *) ok "cleared $DELETED cached content key(s) — students see the new JSON immediately" ;;
  esac
elif [[ "$DRY_RUN" -eq 1 ]]; then
  step "5/6  Invalidate Redis content cache (skipped — dry run)"
else
  step "5/6  Invalidate Redis content cache (skipped via --skip-invalidate)"
  warn "the VPS will serve the PREVIOUS content JSON until its keys expire (up to 1 hour)"
fi

# ── Step 6: optional smoke ──────────────────────────────────────────────────
if [[ -n "$SMOKE_URL" ]]; then
  step "6/6  Smoke check against $SMOKE_URL"
  if ! bash "$REPO_ROOT/scripts/demo/smoke.sh" "$SMOKE_URL"; then
    die 6 "smoke check failed — inspect output above; the 3 static-content HEAD checks tell you which rsync target the VPS can't serve"
  fi
  ok "smoke passed"
else
  step "6/6  Smoke (skipped — pass --smoke <url> to run)"
  echo "    bash $REPO_ROOT/scripts/demo/smoke.sh https://your-host"
fi

echo -e "\n${green}${bold}══ content sync complete ══${reset}"
