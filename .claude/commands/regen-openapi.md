---
description: Regenerate OpenAPI schema + TypeScript types; flag drift.
---

Regenerate the API contract artefacts and surface any drift for review.

## Step 1 — Export the FastAPI schema

```bash
docker compose exec -T api python scripts/export_openapi.py > web/openapi.json
```

If the `api` container is not running, fall back to:
```bash
cd backend && python scripts/export_openapi.py > ../web/openapi.json && cd ..
```
(requires the backend Python env with deps installed on host — rare; prefer the container path).

## Step 2 — Regenerate TypeScript types

```bash
cd web && npm run gen:types && cd ..
```

This runs `openapi-typescript openapi.json -o lib/api/types.gen.ts`.

## Step 3 — Report drift

Show:
```bash
git diff --stat web/openapi.json web/lib/api/types.gen.ts
```

Then for each file with changes, show a compact diff summary (added/removed paths, not full content). Group by:
- **Intentional drift** — matches the endpoint change you just made
- **Unintentional drift** — schema changes you didn't make (often indicates a pydantic model change in a module you didn't touch)

## Step 4 — Decide

Ask me:
- If drift matches intent → I'll say "stage it" and you add both files to the current commit.
- If drift is unintentional → stop, surface the unexpected paths, and don't stage anything. Most likely cause: another module's pydantic model was changed without regen, and CI was going to catch it anyway.

## Step 5 — DO NOT auto-commit

Regen artefacts belong with the commit that caused them. Let me bundle them into the right commit myself.

## Known gotcha

If the export fails with "missing required env var," the Settings class is complaining about a secret that's stubbed in `export_openapi.py`. Check the stub list at the top of that script — add any new required field there before re-running.
