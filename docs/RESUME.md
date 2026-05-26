# RESUME — where to pick up

A git-tracked checkpoint so work can resume on any machine (Claude Code's local
memory does not travel; this file + GitHub issues do). Last updated: 2026-05-26,
`main` @ `bcd75f4`.

## ▶ Where we left off (2026-05-26) — Authoring Studio shipped, repo-home decided, backup bug fixed, Q content-migration started

### Curriculum Authoring Studio (super-admin) — SHIPPED + merged
TOC paste → LLM structure + advisory flow analysis → editable topic table →
staged platform curriculum → per-topic generate (lesson/tutorial/quiz, Mermaid) →
review + unlimited regenerate-with-reason → snapshots/restore → publish. Gated by
`curriculum:author` (super_admin-only). Migration **0060** (`authoring_*` tables;
extends `curricula.source_type` CHECK with `admin_authored`). Backend
`backend/src/admin/authoring_*` + `pipeline/toc_structurer.py` +
`pipeline/flow_analyzer.py`; web `web/app/(admin)/admin/authoring/**`. PRs
#383 (PR-A intake→materialize), #384/#390/#392/#393 (PR-B generate→publish +
fixes), #395 (publish-UX fix). Policy: stays **super-admin-only** for now — do
not widen the `curriculum:author` grant.

### Repo-home decision — ADR-004 "Q grows up" (the standalone/BYOK direction is StudyBuddy Q)
The standalone "author-your-own-book + free reader, BYO Anthropic key" product
belongs in **StudyBuddy Q** (`StudyBuddy_SelfLearner`), **not** OnDemand. OnDemand
keeps the Authoring Studio only as super-admin platform content-ops. Recorded in
`docs/ADR_004_authoring_studio_home_repo.md` (PR #397, Accepted). OnDemand ADR-002
(PR #394) + ADR-003 (PR #396) **closed without merge** — superseded, recast in Q.
Reuse into Q is **port + vendor, one-way, never cross-import** (Q's ADR-002 rule).
Q-side handoff lives on **Q `main`** (`StudyBuddy_SelfLearner`): `docs/adr/ADR-003-book-authoring.md`,
`docs/PORT_BRIEF.md`, `docs/CONTENT_MIGRATION_CONTEXT_ENGINEERING.md`. **Note the
port is further along than `PORT_BRIEF.md` says** — Q already shipped `/structure`,
`bookStore` (AsyncStorage), and a generate-all loop (Q PRs #11/#13). Phases 2–4 (Q
reader growing to 5 content types) belong in a fresh **Q-rooted** session.

### Backup bug (reported by Venkatesh Thiyagarajan) — FIXED
| Issue | PR | What |
|---|---|---|
| #398 | #399 | `backup_school_task` joined `classroom_packages` on `cl.id`; classrooms PK is `classroom_id` (mig 0038) → every **full** backup failed with `column cl.id does not exist`. Fixed join key + added regression test `test_full_backup_classroom_packages_query` (the path had zero coverage). |

### Content migration to Q — "Context Engineering in the Enterprise" (📌 RESUME HERE)
Move the authored book from the Authoring Studio into Q's local-first reader.
Owner scope = **"Everything"** (lesson + tutorial + 3 quiz sets; no experiments —
`has_lab=FALSE`). **Data copy, not a code port.** Project id
`4134c75c-2e4c-4927-babb-7d8555c624bd` (curriculum `authored-4134c75c-…`).

**State as of pause (2026-05-26): content COMPLETE + all 85 active versions ACCEPTED.**
- Code shipped: OnDemand export (PR #400) · Q reader 5-types (Q PR #15) · Q paste import
  (Q PR #16) · Q **file** import for big books (Q PR #17) · publish completeness gate
  (#401 → PR #402, `main` @ `bcd75f4`).
- The 3 missing lessons (001/004/013) + 2 tutorials (011/012) + 1 quiz (013 quiz_set_1)
  were **generated** (Celery task; I'd raced 3 generators → pruned 2 dup pending versions)
  and you **accepted all**. Export now yields **17/17 topics, 0 warnings** (~1.9 MB).

**📌 To resume tomorrow:**
1. **Re-export** (the `/tmp` copy may not survive a reboot):
   `docker compose exec api python scripts/export_book.py --project-id 4134c75c-2e4c-4927-babb-7d8555c624bd --out /app/book.json`
   then `mv backend/book.json /tmp/context-engineering-book.json`.
2. **Import into Q** (app action): `cd ../StudyBuddy_SelfLearner/mobile && npx expo start`
   → Books → **Import a book → Choose a JSON file** → pick the file → open a topic, verify
   lesson + tutorial + quizzes render.
3. **(Optional) Re-publish in OnDemand** to sync its now-stale content store — it'll pass
   the new completeness gate. Decide `private` vs `catalog` visibility. Not needed for the
   Q import (export reads accepted DB versions, not the content store).
- Plan/contract: Q `docs/CONTENT_MIGRATION_CONTEXT_ENGINEERING.md`.

---

## ▶ Prior checkpoint (2026-05-25) — demo-feedback round shipped + CI greened

A full demo-feedback cycle was triaged, implemented, merged, and CI was brought
green. Everything below is **merged to `main`** unless marked open.

### Demo feedback (2026-05-24 session + Ashokan 2026-05-21) — ALL SHIPPED
Source of record: `docs/feedback/FEEDBACK_TRACKER.md` (UX items, all `🟢 Done`)
and `docs/feedback/STRATEGIC_FEEDBACK.md` (market/strategic, incl. home-schooling
wedge + archived Economist article PDF).

| Issue | PR | What |
|---|---|---|
| #365 | #372 | Content reading-surface font size → 16px (`SBMarkdown`) |
| #366 | #374 | School dashboard themed hero + colored action tiles |
| #367 | #373 | School nav IA refresh — grouped rail, renames, top-bar account menu |
| #368 | #375 | Dashboard KPIs above the fold + tighter density |
| #369 | #376 | Teacher Management total + grade-wise count |
| #370 | #377 | Teacher-focused FAQ on `/school/help` |
| #371 | #378 | `docs/RESPONSIVE_TARGET.md` — desktop/tablet-first; phones → Expo app |

Label changes from #367 to remember: "Class Overview" → **Student Progress**,
"Our Library" → **My Curricula**, "Content Library" → **Lessons & Content**.

### CI greening — CI workflow now fully green
| CI job | State |
|---|---|
| Backend — Lint & Security | ✅ green (#380 — pip-audit ignore, see #379) |
| Frontend — Lint & Typecheck | ✅ green (#364 + #381 + #382 prettierignore) |
| Frontend — Unit Tests | ✅ green (#364; 63 files / 821 tests) |
| Playwright — Student Flow | ✅ green (#364) |
| API Contract — Types in Sync | ✅ green (#382) |
| **Backend — Tests** | ❌ **still red — #356** (4 pre-existing failures) |
| **Deploy — Demo** | ❌ **still red — Epic 2 hosting blocker** (no VPS) |

CI-greening PRs merged this session: **#364** (frontend tests/lint + Prettier
cleanup), **#380** (starlette CVE ignore), **#382** (API Contract export crash +
schema resync + `web/.prettierignore` for generated files). **#353** (older
"unbreak main" PR) was **closed as superseded**. **#381** added a `format:check`
gate to `/done` + `/ship-ready` + `web/AGENTS.md`.

## Open threads (priority order)
- **#379** — adopt `starlette 1.0.1` (fixes PYSEC-2026-161) once
  `prometheus-fastapi-instrumentator` supports starlette ≥1.0. Currently
  `--ignore-vuln`'d in `.github/workflows/test.yml` (the cap blocks the bump; the
  Host-header auth-bypass vector doesn't apply — auth is JWT-header based). Bump
  `prometheus-fastapi-instrumentator` + `starlette` + `fastapi` together, run
  `./dev_start.sh test`, then drop the ignore.
- **#356** — 4 pre-existing backend test failures (Anthropic 401 + RLS). Backend —
  Tests job stays red until fixed.
- **Epic 2 — hosting/deploy** — Deploy — Demo job fails (no VPS). Tracked product backlog.
- **#361** — non-superuser RLS test lane (`studybuddy_rls_tester`); audit done,
  build needs an env where the bootstrap role can `CREATE ROLE`/`DATABASE`.

## Reusable fix patterns established (copy from these)
- **Prettier ≠ ESLint in CI.** `npm run lint` passing does NOT mean format is
  clean — CI runs `npm run format:check` as a separate step. Always run it before
  a frontend PR (now in `/done`, `/ship-ready`, `web/AGENTS.md`). Generated files
  (`openapi.json`, `lib/api/*.gen.ts`) are in `web/.prettierignore` because the
  API Contract job compares raw generator output — don't reformat them.
- **`export_openapi.py`** stubs env before `from main import app`; it now also
  stubs `CONTENT_STORE_PATH` (the app mkdir's `${CONTENT_STORE_PATH}/visuals` at
  import, which crashes on a bare runner). Regenerate the contract in Docker:
  `docker compose exec -T api python scripts/export_openapi.py > web/openapi.json`
  then `cd web && npm run gen:types`.
- **Driving the school portal headlessly** (Playwright/manual): set the
  `sb_dev_session` cookie (base64url `{name,email}`) + `sb_teacher_token` in
  localStorage (base64url JWT `{teacher_id,school_id,role,exp}`), and stub
  `/api/v1/**` or the nav's `getAlerts` 401 triggers the refresh-interceptor redirect.
- React-Query mock incl. `useMutation`/`useQueries`/`useQueryClient` →
  `web/tests/unit/teachers-page.test.tsx`. Copy/href drift → update shared
  `tests/e2e/data/*` `STRINGS` fixtures.

**Run frontend tests:** `cd web && npm test` (vitest) · `npm run format:check` ·
`npm run typecheck`. **Playwright (host only, pitfall #26):** `cd web && npx playwright test`.

## Pick up on a different laptop
Prereqs: Docker/podman, Python 3.11+, Node 20, `gh` CLI.
1. `git clone …` (everything in-repo transfers).
2. **Securely copy** the gitignored secret files over (NOT via git): `./.env` and
   `web/.env.local`. Without them, `dev_start.sh` regenerates infra secrets but
   external keys (Auth0/Anthropic/Stripe/SMTP) are `REPLACE_ME` placeholders.
3. `./dev_start.sh` — builds images, runs migrations (head is **0060**), starts
   the stack. Use `./dev_start.sh test` for the backend suite (it provisions its
   own test Postgres — do **not** hand-craft `TEST_DB_URL` at a host postgres; see
   `gotcha_test_db_topology`).
4. `cd web && npm ci && npx playwright install` for frontend unit + e2e tooling.
5. `gh auth login` for PR work.

Not in git (recreate or copy): `content_store/` (regenerate via pipeline, needs
`ANTHROPIC_API_KEY`), `node_modules/`, local DB data (starts empty), Playwright browsers.
