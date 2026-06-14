# StudyBuddy OnDemand — Compliance & Content-Quality One-Pager

**Audience:** School / district procurement, IT security, and privacy reviewers.
**Purpose:** Map StudyBuddy's enforced content-quality and privacy gates onto the standards
your checklist asks about — COPPA, FERPA, WCAG, and related state/EU laws.
**Last updated:** 2026-06-14 · maintained alongside `web/lib/compliance.ts` (the source of
truth for standard-by-standard status) and the public summary at `/quality`.

> **How to read the status column.** **Compliant** = enforced in the product today.
> **Target** = we build to the standard and verify continuously, with an audit still in
> progress. We label honestly rather than blanket-claim. Items marked *Target* below are
> noted explicitly so your reviewers aren't surprised.

---

## 1. The one-sentence summary

> Every piece of student content passes a fixed set of gates — automated structure and
> inclusive-language checks, then an explicit human approve/publish step — and is then served
> under database-enforced privacy rules that keep each school's records isolated and block
> under-13 access until parental consent is on file.

---

## 2. Content quality gates (every lesson, quiz, tutorial, experiment)

| Gate | What it enforces | Stage |
|---|---|---|
| **Schema validation** | Content must match a strict per-type structure or it is regenerated; malformed content is never written or served. | Generation |
| **Inclusive-language scan (AlexJS)** | Automated scan for non-inclusive language; flagged items must be cleared before approval. | Generation |
| **Format/structure checks** | Tables, formulae, and required sections are present for the subject (e.g. a balance-sheet section actually contains a table). | Generation |
| **Age-appropriate scope** | Restricted to academic topics for Grades 5–12; student-facing errors are non-technical. | Generation |
| **Reading-level targeting** *(Target)* | Generated to read 1–2 grade levels below the student's grade. *Prompt-targeted, not yet measured by an automated readability gate.* | Generation |
| **Human approval gate** | Content is `pending` until a reviewer explicitly approves and publishes. Reject / block / rollback supported; warnings must be resolved before approval. | Review |
| **Versioned & auditable** | Every revision is an append-only version with word-level diff and per-section reviewer notes; published versions can be rolled back. | Review |
| **AI-content transparency** | Each lesson/quiz/tutorial/experiment carries an AI-generated disclosure (EU AI Act Art. 50). | Serve |

---

## 3. Standard-by-standard mapping

### COPPA — Children's Online Privacy Protection Act *(Compliant)*
- **Verifiable parental consent** required before an under-13 account is activated; content
  access is **blocked** until `account_status = 'active'`.
- **Data minimization:** only name, email, grade, and locale are collected.
- **No tracking** of minors: no location data, device IDs, or behavioural fingerprinting.
- **No targeted advertising** and no advertising identifiers anywhere in the product.

### FERPA — Family Educational Rights and Privacy Act *(Compliant)*
- Progress records, quiz scores, and lesson-view history are treated as **educational records**.
- **Cross-institution isolation is enforced at the database layer** (PostgreSQL Row-Level
  Security): a teacher or admin from one school cannot query another school's records — the rows
  are invisible, not merely hidden by application code.
- **Separate auth domains** for students, teachers, and internal staff so roles cannot be forged
  or crossed.
- Records are scoped to the student's own institution on every teacher/admin endpoint.

### WCAG 2.1 / 2.2 Level AA — Web Accessibility *(Target)*
- Built to WCAG 2.1 AA across student-facing interfaces and **verified automatically on every
  build** with axe-core (WCAG2A + WCAG2AA + best-practice rule sets).
- Implemented today: keyboard navigation with visible focus, screen-reader/ARIA support, forced-
  colors / high-contrast mode, dyslexia-friendly font option, skip-to-content, consistent help
  placement (WCAG 2.2 SC 3.2.6).
- **In-progress (disclosed):** a small number of colour-contrast, `html-has-lang`, and
  `document-title` checks are still being closed out under an active a11y audit. We report these
  as *Target*, not *Compliant*, until the audit completes.
- **Exceeds** Section 508 (US federal procurement) and satisfies EN 301 549 (EU) and AODA
  (Ontario), all of which reference WCAG AA.

### Other standards covered (see `/quality` for full text)
| Standard | Status |
|---|---|
| GDPR Right to Erasure (anonymise within 30 days) | Compliant |
| SOPIPA (CA) — no student-data advertising/profiling/sale | Compliant |
| CCPA / CPRA — know / delete / opt-out; no sale or sharing | Compliant |
| PCI DSS SAQ-A (Stripe redirect; no card data touches our servers) | Compliant |
| EU AI Act Art. 50 — AI-content transparency | Compliant |
| Multi-language EN/FR/ES (built per language, not machine-translated) | Compliant |

---

## 4. Security & data handling (quick facts)

- **Secrets** are environment-injected, never hardcoded; the service fails fast if a required
  secret is missing.
- **Payments:** Stripe Checkout redirect model — no card data on our servers (PCI scope = SAQ-A).
- **Webhook integrity:** Stripe webhooks are signature-verified and idempotent.
- **Rate limiting** on public/auth endpoints to resist abuse.
- **Sub-processors** are limited to those necessary to deliver the service; no student data is
  sold or shared for advertising.

---

## 5. What we will not claim

In the interest of an honest review:
- We do **not** claim automated reading-level *verification* — reading level is targeted at
  generation, not yet measured by a readability gate.
- We report WCAG 2.1/2.2 AA as a **Target** (continuously verified, audit in progress), not as
  fully certified compliance, until the remaining axe findings are closed.

---

## 6. Where to verify these claims

| Claim area | Public reference |
|---|---|
| Full standards list with status | `/quality` and `/about` |
| Accessibility statement + feedback channel | `/accessibility` |
| Privacy practices (COPPA, FERPA, SOPIPA, CCPA) | `/privacy` |
| Per-standard source of truth (engineering) | `web/lib/compliance.ts` |
| Content gate mechanics (engineering) | `CLAUDE.md` → Content Rules, Content Review Workflow |

**Contact:** reach us via `/contact` for the security questionnaire, DPA, or a walkthrough of
any gate or standard above.
