---
description: Run the quiz testing suite against the live local stack. Explicit, ~90s.
---

Run the quiz suite and report the result.

## Step 1 — Run it

```bash
./scripts/quiz_suite.sh
```

## Step 2 — Interpret the exit code

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Everything passed | Report pass, with tier timings. |
| 1 | A genuine test failure | Report which tier and which test. Pull the `correlation_id` from the output and fetch the matching server log: `docker compose logs api --since 10m \| grep <id>`. Do NOT weaken an assertion to make it pass. Note: the content-integrity tier reads REAL on-disk content under `/data/content/curricula`, so an exit 1 there can mean pre-existing broken content on this machine rather than something you just broke — the failure message names the offending unit/file, so check that before assuming your change caused it. |
| 2 | Environment problem | The stack is not running or not healthy. Report that the suite did not run — this is NOT a passing result. Suggest `./dev_start.sh`. |

## Step 3 — On failure

Report the failing tier, the failing test names, and the server-side correlation id.
State plainly whether the quiz path is broken or the suite could not run — never
conflate the two.

Run this whenever `backend/src/progress/`, `backend/src/content/`,
`web/components/content/QuizPlayer.tsx`, or the quiz pages change.
