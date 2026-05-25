---
description: Thorough pre-PR gate — full tests + build + contract drift + doc drift + pitfalls. Target <10min.
---

Comprehensive gate before the PR goes up. Runs everything `/done` runs plus the slow checks that catch cross-cutting issues. **Target runtime: under 10 minutes.** Run once, right before `gh pr create`.

## Step 1 — Confirm branch state

```bash
git status
git log main..HEAD --oneline
```

- **Uncommitted changes?** Abort. Commit them first (they won't be in the PR otherwise).
- **HEAD == main?** Abort — nothing to ship.
- **Branch name generic** (`feat`, `wip`, etc.)? Warn — reviewers scan by branch name.

## Step 2 — Full gate suite (parallel where possible)

Launch these groups concurrently via multiple Bash tool calls in a single message. Each group serializes internally.

### Group A — Backend full test suite + security
```bash
docker compose exec -T api pytest tests/ --tb=short
ruff check backend/ pipeline/
bandit -q -r backend/src/ -ll
```
No `-x` here — we want the complete failure list, not the first one.

### Group B — Web full build
```bash
cd web && npm run format:check && npm run lint && npm run typecheck && npm test -- --run && npm run build
```
`format:check` (`prettier --check .`) is a **separate** CI step from ESLint — `npm run lint` passing does not imply formatting is clean, and a Prettier miss reds the whole "Frontend — Lint & Typecheck" job. Fix with `npm run format`. Production build catches type issues that `tsc --noEmit` misses (e.g., Next.js route-level static-analysis errors).

### Group C — API contract drift
```bash
docker compose exec -T api python scripts/export_openapi.py > web/openapi.json
cd web && npm run gen:types
git diff --stat web/openapi.json web/lib/api/types.gen.ts
```
If the diff is non-empty and **was not produced in this branch's commits**, that's unintentional drift — a pydantic model changed without `/regen-openapi`. Flag it.

### Group D — Migration graph integrity
```bash
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade -1
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic check
```

### Group E — Doc drift (Rule #16)
Find functions/classes/exports renamed or deleted in this branch:
```bash
git diff main...HEAD -- '*.py' '*.ts' '*.tsx' \
  | grep -E '^-[[:space:]]*(def |class |export (function|const|class) |async def )' \
  | sed -E 's/^-[[:space:]]*(def|class|async def|export function|export const|export class) ([A-Za-z_][A-Za-z0-9_]*).*/\2/' \
  | sort -u
```
For each name in the output, grep `CLAUDE.md`, `docs/`, `README.md` for references. Any hits = stale doc → flag.

### Group F — Hardcoded secrets spot-check
```bash
grep -rnE '(api[_-]?key|secret|password|token)[[:space:]]*=[[:space:]]*["'\''][A-Za-z0-9/+_-]{16,}' \
  backend/src/ pipeline/ web/app/ web/lib/ \
  --include='*.py' --include='*.ts' --include='*.tsx' \
  | grep -vE '(test_|_test\.|conftest\.|\.env\.example)'
```
Any hit is a 🔴 block finding.

## Step 3 — Pitfall checklist read-through

No automation here — scan this PR's diff manually against the high-probability pitfalls:

- [ ] Mobile/web does NOT call Anthropic or Stripe directly (pitfall #1, #10)
- [ ] Async event loop not blocked — bcrypt/CPU work in `run_in_executor` (pitfall #2)
- [ ] Audio via pre-signed URL, not streamed through FastAPI if touched (pitfall #3)
- [ ] Progress/analytics writes are fire-and-forget via Celery (pitfall #4)
- [ ] Stripe webhook still verifies signature + dedupes by `stripe_event_id` (pitfall #8, #9)
- [ ] Idempotency key support on new POST endpoints (Rule #5)
- [ ] `attempt_number` computed server-side (pitfall #12)
- [ ] Auth track not mixed — student JWT can't hit teacher/admin endpoints (pitfall #13)
- [ ] RLS bypass only where required (login lookup — pitfall #23); tests use `studybuddy_rls_tester`
- [ ] New migration: full downgrade→upgrade cycle proven (pitfall #27)
- [ ] `unit_name NOT NULL` respected if migration touches `curriculum_units` (pitfall #20)
- [ ] CLAUDE.md migrations table updated if new migration file shipped

Report any that tripped as findings.

## Step 4 — Report

Consolidated table:

| Group | Gate | Status | Time | Notes |
|---|---|---|---|---|
| A | pytest | ✅ / ❌ | ... | ... |
| A | ruff | ... | ... | ... |
| A | bandit | ... | ... | ... |
| B | npm build | ... | ... | ... |
| C | OpenAPI drift | ✅ none / ❌ unintentional / ✨ intentional | ... | ... |
| D | alembic cycle | ... | ... | ... |
| E | doc drift | ... | ... | list of stale refs |
| F | secrets scan | ... | ... | ... |
| — | pitfall checklist | ... | ... | list of trips |

## Step 5 — Declare

- **All green + pitfall scan clean:** `🚀 Ship-ready — <N> gates passed. Open PR with /pr-description.`
- **Any red:** `🚧 Not ship-ready.` Enumerate each failure. Do not auto-fix.

## Deliberately out of scope

- Integration tests hitting real Stripe / Auth0 / Anthropic — not automatable, run manually before ship for webhook/auth-critical PRs
- Load / performance tests — separate Epic 6 workflow
- Cross-browser Playwright full matrix — slow (~30min); run manually for UX-significant PRs
- Accessibility axe scan beyond the persona spec a11y debt (#189) — separate workflow

If any of these feel load-bearing for this specific PR, run them by hand and note the result in the PR description under "Test plan."
