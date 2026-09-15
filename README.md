<p align="center">
  <img src="web/public/assets/home_banner-readme.jpg" alt="StudyBuddy OnDemand" width="720">
</p>

# StudyBuddy AI — OnDemand Edition

**Lessons, always current.**

AI-powered lessons, quizzes, and tutorials for Grades 5–12 — a bridge from the
classroom to a world that won't sit still. Schools provision their students;
students get instant pre-generated content in English, French, and Spanish with
no API key of their own.

**Live demo → [demo.usestudybuddy.com](https://demo.usestudybuddy.com/)**

---

## What this is

Content generation happens **offline, in a pipeline** — not on the student's
device. A build run asks Claude for every Grade / Subject / Unit, validates the
result, and writes it to a content store. The app then serves that content from
cache, instantly.

That one decision is what makes the rest possible:

| | Consequence |
|---|---|
| **No key on the client** | The Anthropic key lives only in backend env vars. Students sign in with email and password. |
| **Instant content** | Cache hit, not a live model call — no 5–10s wait, no truncation from a mobile token ceiling. |
| **Durable progress** | Per-question answers, session scores and struggle signals are recorded server-side. |
| **Teacher visibility** | Because progress is server-side, it can be aggregated into reports, alerts and a weekly digest. |
| **Offline-capable** | Downloaded content is cached on-device; progress events queue and sync on reconnect. |

### The engineering mental model

Every generation is a **scoped query** against the model, parametrised by six
dimensions — topic, grade, language, curriculum context, format, and a real-world
framing. The model is the commodity; the **scoping layer is the product**. A
library is curated by selection and goes stale; a search engine is curated by
query and re-runs. This is the second kind, which is why "always current" is a
structural claim rather than a slogan.

Full positioning, and which framing to use for which audience, is in
[`CLAUDE.md`](CLAUDE.md#positioning).

---

## Getting started

```bash
./dev_start.sh          # Postgres, Redis, migrations, API, Celery, web — all hot-reload
./dev_start.sh test     # backend suite (no API key or Auth0 needed)
./dev_start.sh stop     # stop background containers
./dev_start.sh reset    # wipe the database and start fresh
```

Then read, in this order:

1. **[`CLAUDE.md`](CLAUDE.md)** — the working contract for this repo: layer rules,
   conventions, migration procedure, the pitfalls list, and the non-negotiable
   performance / security / content rules. Read it before writing code.
2. **[`docs/PROGRESS.md`](docs/PROGRESS.md)** — living status per epic,
   regenerated nightly from `docs/epics/` and git history.
3. **[`docs/epics/INDEX.md`](docs/epics/INDEX.md)** — the product backlog.

Architecture, requirements, operations runbooks and the API contract live in the
companion **[studybuddy-docs](https://github.com/wegofwd2020-hub/studybuddy-docs)**
repository — start with
[ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md),
then [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md).
[`CLAUDE.md`](CLAUDE.md#document-map) has the full map of which document answers
which question.

---

## Decisions of record

Architecture decisions live in this repo, next to the code they govern:

| ADR | Decides |
|---|---|
| [ADR-001](docs/ADR_001_tenancy_and_subscription_model.md) | Tenancy, subscriptions, school-as-primary-entity |
| [ADR-004](docs/ADR_004_authoring_studio_home_repo.md) | Where the standalone authoring studio lives |
| [ADR-005](docs/ADR_005_school_roles_and_uniqueness.md) | School roles (`school_admin` ⊃ teacher), email uniqueness, soft delete |
| [ADR-006](docs/ADR_006_multi_provider_llm.md) | Multi-provider LLM pipeline and the provider abstraction |
| [ADR-007](docs/ADR_007_academic_calendar.md) | Academic calendar, terms, per-school grading scales, promotion gating |
| [ADR-008](docs/ADR_008_delivery_calibration.md) | How institutions tune delivery of a fixed syllabus year over year |

Other frequently-needed documents:
[`PENDING_DECISIONS.md`](docs/PENDING_DECISIONS.md) ·
[`PROJECT_WISDOM.md`](docs/PROJECT_WISDOM.md) ·
[`SCHOOL_USER_MANAGEMENT.md`](docs/SCHOOL_USER_MANAGEMENT.md) ·
[`COMPLIANCE_ONE_PAGER.md`](docs/COMPLIANCE_ONE_PAGER.md) ·
[`COMPETITIVE_kolibri.md`](docs/COMPETITIVE_kolibri.md)

---

## Repository structure

```
StudyBuddy_OnDemand/
  README.md          ← this file
  CLAUDE.md          ← working contract: conventions, layer rules, pitfalls
  dev_start.sh       ← one command to bring the whole stack up

  backend/           ← FastAPI + asyncpg + Redis. Auth, content, progress,
                       reports, school/admin APIs. Alembic migrations, pytest.
  web/               ← Next.js 15 app: public site, student portal,
                       school/teacher portal, admin console. Vitest + Playwright.
  pipeline/          ← Offline content generation (Claude / OpenAI / Gemini),
                       TTS, prompt builders. Runs as CLI or Celery task.
  data/              ← Grade curriculum JSON — source of truth for the
                       default curricula.

  docs/              ← ADRs, design docs, epics, progress chart
  scripts/           ← operator tooling (doc audit, demo ops, quiz suite)
  infra/             ← nginx, pgbouncer and related deployment config
  TICKETS/           ← per-ticket working notes
  mobile/            ← legacy Kivy client. Superseded: Epic 3 selected
                       Expo/React Native and is parked behind hosting.
                       Kept for reference, not under active development.
```

---

## Testing

```bash
./dev_start.sh test                                   # backend (pytest, all externals mocked)
docker compose exec -T web npx vitest run             # web unit tests
cd web && npx playwright test                         # E2E (run from the host, not the container)
./scripts/quiz_suite.sh                               # live-stack quiz suite, explicit
```

CI never touches a live database, live Redis, or any external API. The quiz
suite is the deliberate exception — it runs against a real local stack, is
excluded from every normal run, and must be invoked explicitly. See the Testing
section of [`CLAUDE.md`](CLAUDE.md#testing) for why.

---

## Relationship to StudyBuddy Free

The Free edition (private repo, `studybuddy_free`) proved the concept: a
grade-aware curriculum, AI-generated lessons, adaptive quizzes. It called Claude
directly from the device with the student's own key, which capped what it could
be.

| | Free Edition | OnDemand Edition |
|---|---|---|
| **Claude API** | Student's own key, called from device | Owner's key, backend only |
| **Content delivery** | Live generation (slow, truncation-prone) | Pre-built cache (instant) |
| **Progress storage** | Local JSON file | PostgreSQL, server-side |
| **Offline** | Not supported | Cached content + queued sync |
| **Auth** | Name + API key | Email + password + JWT |
| **Multi-device** | Not supported | Supported |
| **Teacher visibility** | None | Reports, alerts, weekly digest |

Free remains a useful standalone tool and reference implementation. OnDemand
replaces it as the production platform.

> **Sibling projects:** the standalone, non-school products moved to **Mentible**
> (`StudyBuddy_SelfLearner`). The home-schooling wedge stays here.
