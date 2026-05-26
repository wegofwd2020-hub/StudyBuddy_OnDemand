# ADR-003 — Curriculum Authoring Studio as a Standalone Product (BYO-key, free interactive reader)

**Date:** 2026-05-26
**Status:** Proposed (options with recommendations; two product decisions left open)
**Branch at decision:** `docs/adr-003-standalone-studio`

---

## Context

ADR-002 (Revision 1) surfaced that the Authoring Studio is no longer a feature
inside the school platform but a **separate product**:

- The **Studio** (authoring tool) is the **paid** product — one-time or
  subscription (TBD).
- The **reader** is **free** and downloadable.
- The buyer authors **their own book**, supplying (and paying for) **their own
  Anthropic API key** (BYO-key). Single user.
- Reading must be **interactive** (quizzes), so the "reader" is **an app we
  build**, not a generic EPUB reader (ADR-002 R1).
- No analytics required.

This is the "engine + wrappers" thesis made concrete: the shared engine
(`pipeline/` prompts + providers, the authoring services, the renderer
components) gets a **second wrapper** — an individual, BYO-key, local product —
alongside the existing hosted, multi-tenant school SaaS, which is unchanged.

The decision this ADR makes: **how the standalone Studio + free reader are
built, packaged, and licensed.** It is the fork everything downstream (the
reader, the optional EPUB export) depends on.

### The architectural starting point (and the mismatch)

The Studio we shipped (#383–#393) is built for the **hosted multi-tenant** world:
FastAPI + **Postgres (asyncpg, RLS, Alembic)** + **Redis** + **Celery** (async
analyze/generate on a `pipeline` queue) + Next.js, gated by a `super_admin` JWT.
Almost none of that fits a **single-user local app**: RLS/multi-tenancy is moot,
a distributed task queue is overkill, and `super_admin` auth is the wrong gate (a
purchased license is). So a standalone build is partly a **re-platforming** of
the authoring subsystem onto a lighter, single-user stack — bounded, but real.

---

## Decision Area 1 — Deployment model

| Option | What | For | Against |
|---|---|---|---|
| **A. Local-first desktop** (recommended) | Desktop app (Tauri or Electron) bundling the UI + a lightweight local backend + local data; BYO key in OS keychain; content on the user's disk | Matches "standalone + BYO-key + free auth-free reading + privacy"; **zero per-user hosting cost**; no liability for users' keys; offline | Biggest build: package the stack, port off Postgres/Redis/Celery, desktop signing/auto-update |
| **B. Hosted web app (SaaS)** | We host the backend + database; user logs in (license), enters key (stored encrypted server-side) | Fastest — **reuse the existing stack almost as-is**; no desktop packaging | Contradicts "standalone"; **we hold users' API keys** (liability); recurring hosting cost; inherits the Epic-2 hosting blocker; reading isn't truly auth-free |
| **C. Hybrid** | Local desktop authoring + optional hosted license/sync | Local privacy + optional cloud | Most surfaces to build/maintain |

**Recommendation: Option A (local-first desktop).** It is the only option that
actually delivers what the answers describe (buy → install → BYO key → author
locally → read free). Option B ships faster by reusing the current stack, but
holding users' Anthropic keys and paying per-user hosting are exactly what BYO-key
+ standalone are meant to avoid. If time-to-validate matters more than fit, B is a
defensible **interim**, with A as the real target.

---

## Decision Area 2 — Local stack shape (if Option A)

The single-user local build replaces the hosted-world dependencies:

| Hosted today | Local standalone |
|---|---|
| Postgres + asyncpg + **RLS** + Alembic | **SQLite** (single user → no tenancy, no RLS); keep a thin migration step |
| Redis (cache + Celery broker) | **None** (single-process; in-memory where needed) |
| Celery (`pipeline` queue, async analyze/generate) | **In-process async** (asyncio background task + a local job/status table) |
| `super_admin` JWT gate | **License check** (see Area 4); the owner *is* the user |
| `pipeline/` prompts + providers | **Reused as-is** (BYO key from keychain) |
| `SBMarkdown` / `MermaidDiagram` / quiz components | **Reused as-is** in the reader |

The authoring **service logic** (TOC structuring, flow analysis, generate /
regenerate-with-retry, snapshots, accept, publish) ports largely intact — but it
was written against asyncpg/RLS/Celery, so the DB layer and task dispatch need a
single-user adaptation. This is the bulk of the effort and should be scoped
explicitly. (It also reopens whether to extract the shared engine into installable
packages rather than copy code — see Area 6.)

---

## Decision Area 3 — BYO Anthropic key

Store the user's key in the **OS keychain** (Keychain / Credential Manager /
libsecret), read by the bundled pipeline at call time. The key **never leaves the
machine** (no server, no telemetry). Surface **token/cost visibility** in-app
(they're paying Anthropic directly) and a graceful "key invalid / quota" state.
This sidesteps the key-liability of Option B entirely.

---

## Decision Area 4 — Licensing the purchase (OPEN DECISION)

Reading is free/auth-free; the **Studio** is what's paid. Two models:

- **One-time license (recommended for v1):** a signed license file/key validated
  **offline** (public-key verify in the app). No license server, no recurring
  infra. Simplest; aligns with a desktop app.
- **Subscription:** requires a **lightweight license server** for periodic online
  validation (validates entitlement only — never content, never keys). More infra
  + the renewal/anti-piracy surface, but recurring revenue.

**Left open per your note.** Recommendation: ship **one-time, offline-validated**
for v1 to avoid standing up any server; revisit subscription once there's demand.
Either way, license validation gates **authoring**, not **reading**.

---

## Decision Area 5 — The free reader

A **free, downloadable, interactive reader** that opens authored packages from
local disk and renders them with the **existing** renderer
(`SBMarkdown` + `MermaidDiagram` + KaTeX + the quiz components) — so quizzes stay
interactive, math/diagrams render live. Likely the same desktop shell in a
"read-only" mode, plus a standalone reader build for people who only received a
package. **Optional static EPUB export** (ADR-002) remains for true third-party
e-reader portability, with quizzes flattened to an answer-key appendix.

---

## Decision Area 6 — Repo & code sharing (OPEN-ish)

The standalone product is a **distinct product**, not a branch of the school SaaS.
Prefer **extracting the shared engine** — `pipeline/` (prompts, providers,
schemas), the authoring service logic, and the renderer components — into
reusable packages consumed by both the school platform and the standalone app,
rather than copy-forking. The school platform stays as-is. Whether this is a new
repo or a workspace package in the monorepo is a logistics call (recommend a
separate product surface once the extraction boundary is clear).

---

## Consequences

**Positive**
- Delivers the actual product (buy → BYO key → author locally → read free), opens
  the individual / home-school / professional market (the documented wedges).
- No per-user hosting cost, no liability for users' keys, privacy by default,
  offline.
- Reuses the engine + renderer; the school SaaS is untouched.

**Negative / cost**
- Real re-platforming: port the authoring subsystem off Postgres/RLS/Redis/Celery
  to a single-user local stack; desktop packaging, code signing, auto-update.
- Two products to maintain; pressure to keep the shared engine genuinely shared
  (Area 6) or drift sets in.
- Desktop support burden (users' machines, key setup, Anthropic quota/cost UX).

---

## Open decisions (need your call; everything else has a recommendation)

1. **Desktop framework** — **Tauri** (small binaries, Rust shell, web UI) vs
   **Electron** (larger, mature ecosystem). _Recommendation: Tauri for size/perf
   unless an Electron-only dependency forces it._
2. **Pricing** — **one-time** (no server) vs **subscription** (license server).
   _Recommendation: one-time for v1._
3. **Interim vs target** — ship Option B (hosted, reuse stack) first to validate,
   or go straight to Option A (local desktop)?

---

## Alternatives considered

- **Keep it a hosted feature in the school platform.** Rejected — directly
  contradicts standalone + BYO-key + individual + auth-free reading.
- **Installable PWA (no desktop shell).** Lighter than desktop, but still needs a
  backend somewhere (so not truly local/offline) and OS-keychain access is weaker;
  a reasonable middle path if Option A's desktop packaging proves too heavy.

---

## References

- ADR-002 (Revision 1) — reading-format decision; established the
  interactive-reader-primary pivot and the standalone framing that this ADR resolves.
- Issue #391 — package organization (quiz consolidation + export).
- Authoring Studio PRs #383, #385, #390, #392, #393 — the hosted-world implementation
  this would re-platform for single-user.
- `pipeline/` (prompts, providers, schemas) and `web/components/content/` (renderer)
  — the shared engine + renderer to reuse.
