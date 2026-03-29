# StudyBuddy AI — OnDemand Edition

**Backend-powered STEM tutoring platform for students Grades 5–12.**

---

## What This Is

StudyBuddy OnDemand is the next generation of the [StudyBuddy Free](https://github.com/wegofwd2020-hub/studybuddy_free) standalone app.

The Free edition proved the concept — students can navigate a grade-aware STEM curriculum, read AI-generated lesson synopses, take adaptive quizzes, and receive personalised remediation. However, it has fundamental limitations:

| Problem | Root Cause |
|---|---|
| Students must supply their own Anthropic API key | No backend — app calls Claude directly |
| Lesson/quiz load time is 5–10 seconds | Live Claude API call per request on-device |
| Lessons are truncated if too long | Mobile token/timeout ceiling |
| Progress is lost if the app is reinstalled | Stored only in local JSON |
| No teacher or parent visibility | No backend to aggregate data |

**StudyBuddy OnDemand solves all of these** by moving content generation to a backend pipeline and delivering pre-built content to the app on demand.

---

## Core Principles

1. **Students never call the AI directly** — The Anthropic API key lives only in backend environment variables. Students register with email and password.
2. **Content is pre-generated, not live** — A build pipeline runs Claude for every Grade/Subject/Unit and stores the results. Students get instant content from a cache.
3. **Offline-capable** — Downloaded content is stored in local SQLite on the device. Progress events are queued and synced when connectivity resumes.
4. **Progress is durable** — Per-question answers, session scores, and struggle events are recorded server-side. Reinstalling the app loses nothing.
5. **Phased delivery** — Architecture supports a freemium/subscription model via grade-level gating without any app store changes.

---

## Repository Structure

```
StudyBuddy_OnDemand/
  README.md               ← This file
  CLAUDE.md               ← Claude Code instructions (stays with the code)
  backend/                ← FastAPI backend (Phase 1+)
  mobile/                 ← Kivy mobile app — thin client (Phase 1+)
  pipeline/               ← Content generation scripts (Phase 2+)
  data/                   ← Grade curriculum JSON files (shared with Free edition)
```

> **Documentation** has been moved to the [studybuddy-docs](https://github.com/wegofwd2020-hub/studybuddy-docs) repository — architecture, requirements, operations runbooks, and design decisions all live there.
> See [ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md) for the full design and phased plan.

---

## Relationship to StudyBuddy Free

| | Free Edition | OnDemand Edition |
|---|---|---|
| **Repo** | studybuddy_free | StudyBuddy_OnDemand |
| **Claude API** | Student's own key, called from device | Owner's key, called from backend only |
| **Content delivery** | Live generation (slow) | Pre-built cache (instant) |
| **Progress storage** | Local JSON file | PostgreSQL (backend) |
| **Offline** | Not supported | Full offline with sync |
| **Auth** | Name + API key | Email + password + JWT |
| **Multi-device** | Not supported | Supported |

The Free edition remains a useful standalone tool and a reference implementation. The OnDemand edition replaces it as the production-quality platform.

---

## Getting Started

To understand the system before touching code:

1. Read [ARCHITECTURE.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md) — system design, diagrams, API spec
2. Read [AGENTS.md](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/AGENTS.md) — conventions and onboarding for AI-assisted development
3. Review the [phased implementation plan](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/ARCHITECTURE.md#phased-implementation-plan)
