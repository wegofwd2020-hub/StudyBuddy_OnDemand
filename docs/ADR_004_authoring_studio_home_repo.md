# ADR-004 — Home repo for the standalone authoring + reader: StudyBuddy Q, not OnDemand

**Date:** 2026-05-26
**Status:** Accepted (D5 resolved 2026-05-26 — "Q grows up": book authoring)
**Branch at decision:** `docs/adr-004-studio-repo-home`

---

## Context

Today's **Curriculum Authoring Studio** (this repo, PRs #383–#393) was built as a
**super-admin feature of the school platform**: author platform/OOB curricula
(`owner_type='platform'`, `super_admin` gate, Postgres/RLS/Celery, "publish to
school catalog").

Over the same session the product framing shifted (ADR-002 Rev 1, ADR-003): the
desired product is **standalone**, **BYO Anthropic key**, for an **individual**
who authors **their own book** and reads it in a **free interactive reader** —
explicitly *not* school plumbing.

A separate repo already embodies that exact product: **`StudyBuddy_SelfLearner`
(brand: StudyBuddy Q)** — *"a purpose-built Anthropic client for self-learners…
adults paste their own Anthropic key (BYOK)."* Its locked charter:

- BYOK, keys never stored (its **ADR-001 — BYOK security model**).
- **Adults only — no COPPA/FERPA, no school logic.**
- Single-tenant FastAPI + RN/Expo mobile (already a renderer/reader) + a
  **vendored** `pipeline/` (prompts/providers).
- Its **ADR-002 — repo structure & vendoring:** *never import from
  `StudyBuddy_OnDemand`; share prompt IP one-way via vendoring only.*
- Sister-project stance: *"They share IP (prompts), not customers."*

So the standalone direction (ADR-002 R1 / ADR-003) **is** StudyBuddy Q. ADR-003's
"re-platform onto a single-user BYOK stack" is already Q's architecture. Q is a
**pre-MVP skeleton, dormant since ~2026-04-30.**

This ADR records where each piece of today's work lives and dispositions the two
ADRs drafted today.

---

## Decision

### D1 — The standalone / BYOK / individual authoring + reader product is owned by StudyBuddy Q

Do **not** build the desktop/EPUB/standalone-reader product in this (school)
repo. It is StudyBuddy Q's domain: Q already has the BYOK, adult-only,
single-tenant foundation and a mobile renderer/reader.

### D2 — OnDemand retains the super-admin platform-curricula authoring (the merged work stays)

The Authoring Studio merged in #383–#393 stays in OnDemand as **internal
content-ops** for the B2B school product (a super-admin authoring OOB curricula
that schools adopt). It is done, green, and harmless. We do **not** retroactively
rip it out. We simply **stop pursuing the *standalone* direction here.**

### D3 — ADR-002 and ADR-003 (this repo) are superseded; their substance relocates to Q

ADR-002 (EPUB/reading format) and ADR-003 (standalone packaging + BYO-key) describe
**Q's product, not OnDemand's**. They are superseded by this ADR in the OnDemand
context. Their substance should be **recast as StudyBuddy Q ADRs**, reconciled with
Q's existing ADR-001 (BYOK) and ADR-002 (vendoring). The OnDemand PRs that carry
them (**#394** for ADR-002, **#396** for ADR-003) should be **closed without
merging** — kept in branch history as the analysis trail — rather than landing as
OnDemand decisions.

### D4 — Reuse is by vendoring / port, never cross-import

Honor Q's one-way-vendoring rule. Porting to Q means **re-implementing** the
authoring service logic in Q's single-tenant/BYOK stack and **vendoring** the
prompt/pipeline IP — never `import`-ing from this repo. (Convenient: ADR-003's
re-platform target — SQLite / in-process async / license gate instead of
Postgres-RLS / Celery / super_admin — is already Q's stack, so Q is a better
foundation than re-platforming OnDemand's version.)

### D5 — GATING OPEN DECISION: Q's scope (single-artefact vs book authoring)

Q's charter today is *"one well-scoped query → one good artefact… not a course
platform."* The Authoring Studio is heavier — *a TOC → a multi-topic book with
flow analysis, versioning, snapshots, publish.* Re-homing it **expands Q's scope**
beyond "one artefact." Decide in Q, before porting:

- **Q grows up** → self-learners author personal study **books**; the Authoring
  Studio becomes Q's flagship feature (recommended — it's a natural maturation and
  reuses Q's foundation), accepting that "not a course platform" is relaxed; **or**
- **Q stays minimal** (single-artefact client) → personal book-authoring is a
  *third* product, not Q.

_This is the one decision everything downstream hangs on; left to the owner._

**RESOLVED (2026-05-26): "Q grows up."** StudyBuddy Q expands from
single-artefact to **multi-topic book authoring**; the Authoring Studio becomes
**Q's flagship feature**, ported into Q's BYOK/single-tenant stack (vendoring the
prompt IP, per D4). Q's prior "not a course platform" line is relaxed to cover
personal book authoring for the individual self-learner. The Authoring Studio's
ADR-002/003 substance is recast as StudyBuddy Q ADRs.

---

## Disposition summary

| Item | Disposition |
|---|---|
| Authoring Studio backend + UI (#383–#393, merged to OnDemand `main`) | **Keep** in OnDemand as super-admin platform content-ops |
| Standalone / desktop / EPUB / free-reader direction | **Build in StudyBuddy Q** (not OnDemand) |
| ADR-002 (OnDemand, PR #394) | **Supersede;** recast in Q. Close #394 without merge |
| ADR-003 (OnDemand, PR #396) | **Supersede;** recast in Q. Close #396 without merge |
| Publish UX fix (PR #395) | **Independent** of this decision — merge on its own merit |
| Prompt / pipeline IP | **Vendor** into Q (one-way), as Q already does |
| OnDemand Authoring Studio | May serve as a working **prototype** to demo the concept while Q is built |

---

## Consequences

**Positive**
- Preserves the deliberate sister-product separation (shared IP, not customers;
  school FERPA/COPPA isolation intact).
- OnDemand stays focused on the B2B school product; Q becomes the individual/BYOK
  surface it was created to be.
- Avoids duplicating a BYOK/standalone product inside the multi-tenant school stack.

**Negative / cost**
- Reviving Q (pre-MVP, dormant) and stewarding **two** repos.
- Porting (not importing) the authoring subsystem into Q's stack — real work,
  though aligned with Q's existing architecture.
- The OnDemand Authoring Studio becomes somewhat orphaned in ambition (kept only
  for platform content-ops); accept that, or later trim it.

---

## Alternatives considered

- **Build the standalone product in OnDemand.** Rejected — duplicates Q, wrong
  audience/compliance/stack, and contradicts Q's deliberate separation.
- **A third repo.** Rejected — Q already *is* the individual BYOK product.
- **Merge Q into OnDemand.** Rejected — deliberate separation; FERPA/COPPA
  isolation; no shared customers by design.
- **Literally move the code OnDemand → Q.** Rejected — Q's ADR-002 forbids
  cross-import; architectures differ. It is a port + vendor, not a transplant.

---

## References

- This repo: ADR-002 (EPUB/reading), ADR-003 (standalone packaging) — superseded here.
- StudyBuddy Q (`StudyBuddy_SelfLearner`): README / SCOPE.md, ADR-001 (BYOK security),
  ADR-002 (repo structure & vendoring).
- Issue #391 — package organization (quiz consolidation + export).
- Authoring Studio PRs #383, #385, #390, #392, #393 (the merged OnDemand work).
