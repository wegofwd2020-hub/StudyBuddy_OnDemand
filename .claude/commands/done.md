---
description: Fast post-implementation gate — tests + lint + types on changed scope. Target <2min.
---

You just declared a feature implemented. Before moving on, run the fast gate against what actually changed. **Target runtime: under 2 minutes.** Not a substitute for `/ship-ready` — that's the pre-PR gate.

## Step 1 — Identify scope

```bash
git diff --name-only main...HEAD
git status --short
```

Bucket the changes:

| Bucket | Pattern | Triggers |
|---|---|---|
| Backend | `backend/**/*.py`, `pipeline/**/*.py` | backend gates |
| Web | `web/**/*.{ts,tsx}` | web gates |
| Migrations | `backend/alembic/versions/*.py` | migration gates |

If no code files changed, stop — there's nothing to gate.

## Step 2 — Run the applicable gates in parallel

Only run a bucket's gates if that bucket has changes. Use multiple Bash tool calls in a single message for concurrency.

### Backend (if Python changed)

```bash
docker compose exec -T api pytest tests/ -x --tb=short
ruff check backend/ pipeline/
bandit -q -r backend/src/ -ll
```

### Web (if TS/TSX changed)

```bash
cd web && npm run lint
cd web && npm run typecheck
cd web && npm test -- --run
```

### Migrations (if any `backend/alembic/versions/*.py` touched)

```bash
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade -1
docker compose exec -T api alembic upgrade head
```

The three-step upgrade/downgrade/upgrade cycle is pitfall #27 — never skip.

## Step 3 — Report

Single table, one row per gate actually run:

| Gate | Status | Time | Notes |
|---|---|---|---|
| pytest | ✅ / ❌ | ... | ... |
| ruff | ... | ... | ... |

Don't list gates you skipped (only confuses the reader). Do mention the skipped buckets in prose: "Web gates skipped — no TS/TSX changed."

## Step 4 — Declare

- **All green:** `✅ /done — <N> gates passed. Run /ship-ready before opening the PR.`
- **Any red:** `❌ Not done — <N> gate(s) failed.` Enumerate each. Offer to fix the first trivial one; otherwise hand back.

**Do not auto-fix broken tests or lint issues.** Fixing is a conscious follow-up decision — silent fixes hide regressions.

## Deliberately out of scope

Excluded from `/done` to keep runtime fast:
- `npm run build` (1-2min by itself) → in `/ship-ready`
- OpenAPI regen + TS types drift → in `/regen-openapi` or `/ship-ready`
- Doc-drift scans → in `/ship-ready`
- Pitfall checklist read-through → in `/ship-ready`
- Integration tests against real Stripe/Auth0/Anthropic → never automatable here

If any of the above feel load-bearing for a specific PR, run `/ship-ready` instead.
