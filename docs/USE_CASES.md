# StudyBuddy OnDemand — Use Cases & User Stories

_Last updated: 2026-04-26. Derived from CLAUDE.md status, docs/PROGRESS_epics.csv, and docs/epics/._

**Legend:** ✅ Done · 🚧 In progress · ⏸ Paused/Blocked · 🔲 Pending · 💭 Your call

---

## Student

| # | Name | Description | Status | When |
|---|---|---|---|---|
| S-01 | Student self-registration & login | Auth0 + local school-provisioned login, JWT auth, password reset, first-login forced reset | ✅ Done | Pre-Apr 2026 |
| S-02 | Browse curriculum & subjects | Curriculum tree by grade/subject/unit, school-enrolled vs. default routing | ✅ Done | Pre-Apr 2026 |
| S-03 | View lesson content | Pre-generated lesson JSON served from Content Store, L1/L2 cache warm path | ✅ Done | Pre-Apr 2026 |
| S-04 | Take quizzes | MCQ quiz delivery, answer submission, results, attempt tracking | ✅ Done | Pre-Apr 2026 |
| S-05 | Listen to audio lessons | CDN-hosted MP3s via pre-signed URL; never proxied through API | ✅ Done | Pre-Apr 2026 |
| S-06 | View experiment / lab content | Experiment JSON with materials + steps; experiment viewer screen | ✅ Done | Pre-Apr 2026 |
| S-07 | Progress tracking & streak | Session recording, answer history, streak counter, Celery fire-and-forget writes | ✅ Done | Pre-Apr 2026 |
| S-08 | Offline-first sync | SQLite event queue, SyncManager flush on foreground/network restore, UUID dedup | ✅ Done | Pre-Apr 2026 |
| S-09 | Multi-language content | EN/FR/ES pipeline, locale from JWT only, fallback chain | ✅ Done | Pre-Apr 2026 |
| S-10 | Submit feedback | Student feedback form, rate-limited (5/hr), admin-reviewable | ✅ Done | Pre-Apr 2026 |
| S-11 | KaTeX maths + Mermaid diagrams in lessons | Shared `<SBMarkdown>` renderer; `remark-math` + `rehype-katex`; Mermaid fences | ✅ Done | 2026-04-15 |

---

## Teacher

| # | Name | Description | Status | When |
|---|---|---|---|---|
| T-01 | School + teacher registration & login | Teacher provisioning, school auth track, local password, first-login gate | ✅ Done | Pre-Apr 2026 |
| T-02 | Upload custom curriculum | XLSX/JSON upload triggers async pipeline job, returns `job_id` | ✅ Done | Pre-Apr 2026 |
| T-03 | Class analytics & teacher reports | 6 report types (completion, at-risk, usage, engagement, feedback, weekly digest), CSV export | ✅ Done | Pre-Apr 2026 |
| T-04 | Create and manage classrooms | Classroom CRUD, assign curriculum packages, add students (migration 0038) | ✅ Done | Apr 2026 (Phase B) |
| T-05 | Submit custom curriculum for review | 4-step curriculum definition form, approval queue, definition detail page | ✅ Done | Apr 2026 (Phase D) |
| T-06 | Stream assignment on curriculum | Stream picker on upload form; teacher/student stream field | ✅ Done | 2026-04-14 |

---

## School Admin

| # | Name | Description | Status | When |
|---|---|---|---|---|
| A-01 | School self-registration | Local auth registration with password ≥12 chars, `first_login` gate | ✅ Done | Apr 2026 (Phase A) |
| A-02 | Provision teachers & students | Teacher/student creation with auto-generated passwords; email delivery; `first_login=TRUE` | ✅ Done | Apr 2026 (Phase A) |
| A-03 | Browse platform curriculum catalog | `GET /curricula/catalog`, per-subject readiness bar, `/school/catalog` browser | ✅ Done | Apr 2026 (Phase C) |
| A-04 | Build and submit custom curriculum | 4-step definition form, cost estimate before trigger, Stripe-gated pipeline fire | ✅ Done | Apr 2026 (Phase D/E) |
| A-05 | Configure LLM provider per school | Per-school Anthropic/OpenAI/Gemini config with DPA acknowledgements | ✅ Done | 2026-04-12 (Epic 1) |
| A-06 | Archive own curriculum | `POST /schools/{id}/curricula/{id}/archive` — blocked if in active use; audit logged | ✅ Done | 2026-04-15 (Epic 10) |
| A-07 | School address & measurement units | Address fields on registration/settings; imperial vs. metric unit-system context | 🔲 Pending | Epic 8 H-1..H-7 |

---

## Platform Admin (Internal)

| # | Name | Description | Status | When |
|---|---|---|---|---|
| P-01 | Content review queue | Approve / reject / publish / rollback content versions; inline annotations | ✅ Done | Pre-Apr 2026 |
| P-02 | Pipeline job management | Trigger, monitor, and cancel pipeline jobs; job detail + payload size tracking | ✅ Done | Pre-Apr 2026 |
| P-03 | Demo teacher request system | Demo lead form, approval, JWT-scoped tour URLs, geo-block CRUD | ✅ Done | Pre-Apr 2026 (Epic 7) |
| P-04 | Multi-provider LLM pipeline | Anthropic / OpenAI / Gemini providers; `--provider` CLI flag; comparison builds | ✅ Done | 2026-04-12 (Epic 1) |
| P-05 | Streams registry (admin CRUD) | Soft stream registry, merge/archive, upsert-on-upload, `/admin/streams` pages | ✅ Done | 2026-04-15 (Epic 8 H-10) |
| P-06 | Archive curricula + audit trail | Archive/unarchive endpoints, usage gate, `curriculum.archive` audit events | ✅ Done | 2026-04-15 (Epic 10) |
| P-07 | Content formatting pipeline (tables + math) | Universal + per-subject prompt rules; GFM tables, KaTeX `$...$`, attributed quotes | ✅ Done | 2026-04-15 (Epic 11) |
| P-08 | Branding refresh | New tagline / sub-headline; `en.json` + school portal + backend copy updated | ✅ Done | 2026-04-21 (Epic 13) |
| P-09 | Super-admin archive view | `/admin/archive/curricula` — list all archived rows with audit trail, filters | 🔲 Pending | Epic 10 L-7 |
| P-10 | Per-jurisdiction audit mode | Log every read of platform content by a specific school (SOC-2/FERPA) | 🔲 Pending | Epic 10 L-9 |
| P-11 | TTL override for archived curricula | `PATCH /admin/curricula/{id}/expiry` — extend/shorten archive TTL with reason | 🔲 Pending | Epic 10 L-10 |

---

## Platform / Cross-cutting

| # | Name | Description | Status | When |
|---|---|---|---|---|
| X-01 | Subscription billing (Stripe) | School Stripe checkout, webhook idempotency, entitlement gating | ✅ Done | Pre-Apr 2026 |
| X-02 | Row-level security (multi-tenant) | RLS on 7+ tables; `app.current_school_id` session var; bypass for admin/pipeline | ✅ Done | Pre-Apr 2026 |
| X-03 | Auth rate limiting & hardening | slowapi rate limits on auth endpoints; CORS LAN allowlist; notification coverage | ✅ Done | 2026-04-22 |
| X-04 | CI hardening (Bandit, pip/npm audit, COPPA/FERPA tests) | K-1, K-3, K-6 — security scans + Stripe webhook tests + compliance assertions | ✅ Done | 2026-04-12 (Epic 6) |
| X-05 | Content regen — Grade 11 Commerce + Science (C-5) | Re-run pipeline with new table+math prompts; Grade 11 Science in flight | 🚧 In progress | Epic 11 C-5 |
| X-06 | TTL sweeper (archived curricula) | Celery Beat daily job hard-deletes rows past 1-year TTL | ⏸ Paused | Epic 10 L-6 |
| X-07 | PDF smoke check for tables + math | Verify Commerce + Maths lesson survives PDF export; no production feature | 🔲 Pending | Epic 11 C-7 |
| X-08 | Load testing + SLO alerting | k6 scripts; p95 < 200ms; error rate < 0.1%; Grafana dashboards | ⏸ Blocked (needs hosting) | Epic 6 K-4/K-5 |

---

## Major Upcoming Epics (Not Started)

| # | Name | Description | Status | When |
|---|---|---|---|---|
| E-01 | Production deployment | Docker hardening, managed Postgres/Redis, CI/CD deploy pipeline | ⏸ Blocked — hosting decision | Epic 2 |
| E-02 | Student mobile app (React Native / Expo) | 24-ticket Expo SDK 52 app — auth, lesson/quiz/experiment viewers, offline-first, EAS build | 🔲 Pending — parked behind hosting | Epic 3 (M-1..M-24) |
| E-03 | Accessibility & personalization | Multi-language UX, theme picker, dyslexia toggle, reduced-motion, text-size slider | 🔲 Pending | Epic 9 |
| E-04 | Parent portal | Parent provisioning, student progress view, at-risk email notifications, FERPA self-serve | 💭 Your call | Epic 4 |
| E-05 | District admin portal | District schema, cross-school analytics, district curriculum assignment, unified billing | 💭 Your call | Epic 5 |
| E-06 | School address & measurement units | Address on registration, imperial/metric unit system context, `<Measurement>` component | 🔲 Pending | Epic 8 H-1..H-7 |
| E-07 | School archive view + UI treatment | School admin sees "archived" banner; archived rows hidden from library but served to prior enrollees | 🔲 Pending | Epic 10 L-8 |
| E-08 | Mobile renderer parity for math + diagrams | Ensure Epic 3 Expo component handles KaTeX + GFM tables (coord with C-8) | 🔲 Pending (waits Epic 3) | Epic 11 C-8 |
