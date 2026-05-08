# Epic 17 — Corporate L&D Fork

> **Status: CONTESTED.** Advisor commitment-boundary call (Rule 2) returned a strong recommendation **against** forking now. See §0 — Critical Counterpoint. The fork plan below stands as the alternative; user picks the path.
> **Trigger:** John Thomas demo feedback, 2026-04-26 (`memory/project_demo_feedback.md`).
> **ISA:** `~/.claude/PAI/MEMORY/WORK/corporate-ld-fork/ISA.md`
> **Companion ADR (if user picks fork):** ADR-002 in this repo, written at fork-execution time.

---

## 0. Critical Counterpoint (Advisor — Rule 2)

The Advisor (`bun ~/.claude/PAI/TOOLS/Inference.ts --mode advisor`) was called at the BUILD/EXECUTE commitment boundary and **recommends NOT forking yet**. The strongest points:

1. **Three demo signals being conflated.** John Thomas (corporate L&D), Venkit P (teacher-authored UI), Sridhar (B2C / GTM cost) were three separate inputs. **None of them said "build a separate product."** Forking on one demo conversation is reading a data point as a mandate.
2. **Scoped-retrieval model generalises.** Per `memory/project_scoped_retrieval_model.md`, the IP is `(topic × grade × language × context × format × framing)`. Corporate L&D is just `grade → role/seniority`, `topic → policy/regulation`, `framing → compliance vs upskilling`. **This is a tenant/config dimension, not a fork.** Forking hard-codes what should be a parameter.
3. **The reuse argument is weaker than it looks.** Stripe primitives are B2C-school-shaped (Checkout, freemium); enterprise needs per-seat MSAs, POs, NET-30, procurement, SSO, BAAs. You'd rip most of it out anyway. RLS bug class (`feedback_rls_get_school_sub.md`) will rot in one fork while the other is fixed.
<!-- doc-audit:ignore -->
4. **Repo-split work is unfinished.** `memory/project_repo_split.md` shows web/mobile/backend splits *pending with blockers*. Adding another fork before finishing the planned split multiplies unresolved structural debt.
5. **"Scenario quizzes" is a feature, not a wedge.** Articulate Rise, Synthesia, Sana, Uplimit, Arist already ship LLM-driven scenario learning. Compliance training is a red ocean (Cornerstone, SAP Litmos, Workday, 360Learning, Absorb). Differentiation on "we have an LLM" lasts ~9 months.
6. **Naming before positioning is a founder trap.** Brand shortlist work (§3 below) eats time and locks in a frame before the frame is validated.
7. **Enterprise compliance posture is missing.** SOC 2 Type II, ISO 27001, GDPR DPA, regulator-grade audit logs, e-signature, SCORM/xAPI export — none are in the codebase. First enterprise buyer's security questionnaire kills the deal.
8. **Failure mode in 6 months:** maintenance tax + no SOC 2 + branding churn + StudyBuddy loses focus → both products stagnate. Re-converging post-fork is painful.

### Advisor's recommended alternative

Don't fork. Don't pick a brand yet. Instead, this week:

1. Add a `tenant_type` enum (`school` | `corporate`) to the existing schema as a feature-flag spine.
2. Build **one** corporate-L&D scenario quiz inside StudyBuddy_OnDemand, gated by that flag, for John Thomas as a design partner.
3. Get a verbal LOI or paid pilot ($) before any fork or rebrand.
4. Park the brand shortlist in `memory/project_parked_topics.md` until step 3 closes.

If a paid pilot lands and the corporate code paths genuinely can't coexist, *then* fork — with revenue justifying maintenance tax and a real customer shaping schema.

> **Verdict not silently switched.** Per Algorithm Rule 3, the conflict between the original fork plan and the advisor recommendation is surfaced for user judgment, not auto-resolved. The fork plan below remains the alternative if the user explicitly chooses momentum over validation.

---

## 1. The Original Decision (if fork is chosen)

**Fork StudyBuddy_OnDemand into a new repository for the corporate L&D / compliance-training product, preserving git history via `git push --mirror`. Keep the multi-provider LLM pipeline, content-review queue, RLS multi-tenancy, and Stripe billing. Strip the K-12 brand, schema, and compliance posture. Reframe the domain language. Defer shared-core monorepo extraction by 6–12 months.**

## 2. Why fork (and not the alternatives)

Three options were considered:

| Option | What it does | Why we did NOT pick it |
|---|---|---|
| **A. Fork (selected)** | Clone StudyBuddy_OnDemand into a new repo, strip K-12, reframe domain, build corporate L&D forward | (Selected — see below.) |
| **B. Monorepo / shared core** | Extract `pipeline/`, `pipeline/providers/`, `core/`, RLS scaffolding into a shared package; both products consume it | Pre-PMF rule: shared-core extraction kills velocity in both products. Optimise for product-decision velocity, not code reuse. Revisit in 6–12 months. |
| **C. Inheritance via `owner_type='corporate'`** | Stay in StudyBuddy, add a new owner type, layer corporate features on top | Domain-language collision (`grade`/`curriculum`/`student` everywhere). Brand-positioning collision (StudyBuddy on enterprise sales decks). Compliance-posture collision (COPPA wired in for K-12 vs SOC 2 demands for enterprise). Forces a brand fork later anyway, but with entangled history. |

**Why fork wins on first principles.** A "product" is defined by six axes: buyer, value proposition, interaction model, compliance posture, sales motion, mental model. Corporate L&D differs from StudyBuddy on **all six**:

| Axis | StudyBuddy | Corporate L&D |
|---|---|---|
| Buyer | School admin / K-12 teacher / parent | CCO / CHRO / L&D manager |
| Value prop | "Always-current learning aligned to curriculum" | "Scenario-based training that holds up to regulators" |
| Interaction | Student progresses through grades over years | Employee completes annual certification |
| Compliance | COPPA + FERPA | SOC 2 + GDPR (sometimes HIPAA) |
| Sales motion | District / school / parent freemium | Enterprise pilot → MSA |
| Mental model | Curriculum library | Audit-evidence + completion tracking |

Six-for-six on differentiation → it's a different product, not a feature.

## 3. Brand Decision — **BriefCase** (picked 2026-05-04)

**Brand selected:** **BriefCase** (user pick, 2026-05-04). Evokes compliance / legal / corporate-document carrying — strong domain fit. The shortlist below is preserved for the historical record but is superseded.

**Trademark + domain check is still pending** — see the user-action checklist at the end of this section. Path A/B/C from Epic 17 still controls *when* the fork (if any) executes; the brand pick stands regardless.

### Considered shortlist (superseded by BriefCase)

### Selection criteria

Each candidate is scored on two axes:

- **Positioning fit** (1–5) — does it evoke compliance / scenario judgment / corporate gravitas?
- **Memorability** (1–5) — short, distinctive, easy to say + spell?

A third gate runs *after* a candidate is picked but before any repo creation:

- **Availability gate** — trademark search (USPTO TESS), domain availability check (.com first; .ai / .training / .work as fallback), GitHub-org name availability, social-handle availability.

### Candidates (considered, not picked)

Spans three stylistic directions: **judicial** (decision/judgment language), **navigational** (compass/posture metaphors), **principle** (values/standards). User chose a fourth direction — **possession/professional-tool metaphor** — with **BriefCase**.

| # | Name | Direction | Why it fits | Positioning Fit | Memorability |
|---|---|---|---|---|---|
| 1 | **Standpoint** | Judicial | Scenario quizzes are literally "what's your standpoint when X happens" — direct fit. Professional, grown-up feel. | 5 | 4 |
| 2 | **Reckon** | Judicial | Punchy single syllable. "When the moment hits, can your team reckon?" Verb form is a tagline gift. | 4 | 5 |
| 3 | **Bearing** | Navigational | Professional-bearing-under-load. Nautical metaphor extends to "off-course → audit risk." Has poetry. | 4 | 4 |
| 4 | **Verdict** | Judicial | Final-answer connotation; on-the-nose for legal/compliance content; risk = a bit prosecutorial. | 4 | 5 |
| 5 | **Tenet** | Principle | Principle/belief; tenets-of-compliance angle. Clean and short. Risk = unfortunate Christopher Nolan film association. | 3 | 4 |
| 6 | **Caliber** | Principle | "The standard you operate at"; "caliber of judgment." Slightly martial undertone may help or hurt. | 4 | 4 |

### broker's earlier top recommendation (now historical)

broker had recommended **Standpoint** (positioning fit 5/5) with **Reckon** as the hedge. User overrode with **BriefCase** — a different stylistic direction (possession/professional-tool metaphor) that broker hadn't proposed. The pick lands cleanly in the compliance/legal/corporate-tool domain and is more visually concrete than the judicial-language alternatives.

### User-action checklist (still open after the brand pick)

- [x] Pick brand → **BriefCase** ✅ 2026-05-04
- [ ] Run USPTO TESS search for trademark conflicts in Class 41 (educational services) and Class 42 (SaaS) for "BriefCase" or "Brief Case"
- [ ] Check `briefcase.com` (almost certainly taken — common word), `briefcase.ai`, `briefcase.training`, `briefcase.work`, `getbriefcase.com`, `usebriefcase.com`, `briefcase.app`, `briefcase.io`
- [ ] If primary domains taken, decide on a stylised variant (e.g. `getbriefcase.*`, `briefcase.training`)
- [ ] Check GitHub-org availability or confirm reuse of `wegofwd2020-hub`
- [ ] Confirm GitHub-org choice (existing org vs new corporate-L&D org) — only relevant if Path B (fork) is chosen later

## 4. Carry-Forward Set (what stays from StudyBuddy)

These are the highest-value reusable assets — the IP that justifies forking instead of building from scratch.

| Asset | Path | Why it carries |
|---|---|---|
| Multi-provider LLM pipeline | `pipeline/` | Epic 1, migration 0043 — provider-agnostic generation is core to a multi-tenant SaaS |
| Provider abstraction | `pipeline/providers/` | `LLMProvider` ABC + Anthropic/OpenAI/Gemini implementations |
| Content-review queue | `web/app/(admin)/content-review/` + `backend/src/admin/` | Generated content needs human review in compliance domain too — even more so |
| Admin console scaffolding | `web/app/(admin)/` | RBAC, JWT-gated layout, AdminNav, version diff UI |
| Multi-tenant RLS pattern | `backend/alembic/0028_*.py` + per-conn `app.current_school_id` setting | Enterprise multi-tenant isolation is the same shape (org instead of school) |
| Stripe billing primitives | `backend/src/subscription/` | Webhook signature verification, idempotency on `stripe_event_id`, Connect accounts |
| Pipeline cost-cap, idempotency, schema validation | `pipeline/build_grade.py`, `pipeline/build_unit.py`, `pipeline/config.py` | Spend governance + safe regen + JSON schema validation |
| Backup / restore | `src/backup/` (Epic 15) | Compliance products MUST have audit-grade backups |
| Multi-provider school config | `school_llm_config` table + `GET/PUT /schools/{id}/llm-config` | BYOK / DPA model translates 1:1 to enterprise customers |

## 5. Strip Set (what goes)

| Asset | Path | Why it goes |
|---|---|---|
| K-12 curriculum data | `data/grade*_stem.json` | Purely K-12 content seed |
| COPPA / under-13 consent | `parental_consents` table + flow | Wrong compliance posture; corporate users are adults |
| School-onboarding flows | `POST /schools/register`, school provisioning UI | Replaced by enterprise-onboarding flow (org + admin invite) |
| Demo student/teacher flows | `backend/src/demo/`, `web/app/(admin)/demo-*`, `web/components/demo/` | Replace with corporate-buyer demo (different fixture data) |
| StudyBuddy branding/tagline copy | `BRANDING_TAGLINE_OPTIONS.md`, hero copy | "Information bridge"/"always current" don't fit compliance |
| Public site (K-12 framing) | `web/app/(public)/`, `for-schools` page | Replace with enterprise positioning landing |

## 6. Reframe Set (rename mappings)

These run as a codemod across DB schema, code, routes, copy. **Do this as a single codemod commit per rename pair**, not piecemeal — Alembic + grep-and-replace + test-suite-runs-green per pair.

| StudyBuddy term | Corporate L&D term | Rationale |
|---|---|---|
| `curriculum` | `training_program` | "Curriculum" is K-12-coded; "training program" is HR/L&D vernacular |
| `grade` | `role_band` | Replace age-grade with seniority band (IC / manager / exec) |
| `subject` | `compliance_domain` | "Subject" → topical coverage area (FCPA, GDPR, export controls, …) |
| `student` | `learner` | Industry-standard L&D term; respects adult learners |
| `school` | `organization` | Enterprise multi-tenant unit |
| `lesson` | `module` | "Module" is universal in corporate L&D |

## 7. v1 New Work — `dialog_scenario` Content Type

The first new content type unique to this product. Sketch (full spec is a separate epic):

- **Schema:** `{ scenario_id, role_band, compliance_domain, dialog: [{ speaker, line }], stem: string, options: [{ id, text }], correct: id, rationale: string }`
- **Prompt builder:** new `build_dialog_scenario_prompt()` in `pipeline/prompts.py` — emits the dialog + stem + options as JSON conforming to the schema
- **Renderer:** new `<DialogScenario />` component in `web/components/content/` — renders the dialog as a styled transcript, then the stem + radio-button options, then the rationale on submit
- **Provider:** reuse the multi-provider abstraction; same generation surface as quizzes
- **Validation:** JSON schema validation; reject + retry on malformed output (already a pattern)

### Seed lists

**Compliance domains (v1, ≥5):**
1. FCPA (Foreign Corrupt Practices Act)
2. GDPR (data privacy)
3. Export controls (EAR / OFAC)
4. AML (anti-money laundering)
5. Code of conduct / harassment / DEI

**Role bands (v1, ≥3):**
1. Individual contributor
2. Manager
3. Executive (VP / C-suite)
4. Board member (optional v1.1)

## 8. Risk Register

| Risk | Mitigation |
|---|---|
| Maintenance duplication (two repos) | Accepted cost. Re-evaluate at 6 months for shared-core extraction. |
| Brand collision (`Standpoint` taken in education space) | Trademark + domain check before fork executes (gate). |
| Premature abstraction | Ban shared-core work for 6 months. Re-evaluate when both products have ≥10 paying customers. |
| John Thomas walks away → orphan repo | Acceptable: the repo can be archived; nothing in StudyBuddy is harmed. |
| Codemod breaks tests | Run codemod per rename pair; require green test suite per pair. |
| RLS / migration drift | Re-baseline migrations on the new repo (renumber starting from 0001) to break implicit ordering links to StudyBuddy. |
| User loses GitHub history → repo provenance | Use `git push --mirror` (NOT `git clone` + new init); preserves all branches, tags, refs. |

## 9. Anti-Criteria (what MUST NOT happen)

- **Anti-1:** Lose StudyBuddy git history during the fork (use `--mirror`).
- **Anti-2:** Couple K-12 compliance posture (COPPA, FERPA) into the corporate product.
- **Anti-3:** Pre-commit to a final product name in this turn (must surface shortlist for user pick).
- **Anti-4:** Execute irreversible repo mutations without user approval.
- **Anti-5:** Begin shared-core extraction before both products have shipped MVP.

## 10. Antecedents (preconditions before fork executes)

- **Ant-1:** User picks a brand name from the shortlist (or rejects + iterates).
- **Ant-2:** User confirms GitHub org choice.
- **Ant-3:** Trademark and domain availability checks pass for the picked name.

## 11. Executable Fork Checklist (gated on user approval)

```bash
# 0. PRE-FORK (user actions; this turn ends here)
#    [ ] Pick brand from shortlist:                      <CHOSEN_NAME>
#    [ ] Confirm GitHub org:                             <ORG>
#    [ ] Trademark search clean (USPTO TESS Class 41+42)
#    [ ] Domain available (.com first preferred)
#    [ ] Confirm: green-light fork

# 1. CLONE WITH FULL HISTORY
cd /tmp
git clone --bare git@github.com:wegofwd2020-hub/StudyBuddy_OnDemand.git
cd StudyBuddy_OnDemand.git

# 2. CREATE NEW REPO (REPLACE PLACEHOLDERS)
gh repo create <ORG>/<CHOSEN_NAME> --private --description "Corporate L&D — scenario-based compliance training"

# 3. PUSH MIRROR (preserves all branches, tags, refs)
git push --mirror git@github.com:<ORG>/<CHOSEN_NAME>.git

# 4. WORKING CLONE
cd ~/Documents/code/projects/AIStuff
git clone git@github.com:<ORG>/<CHOSEN_NAME>.git
cd <CHOSEN_NAME>
git checkout -b corporate-fork-bootstrap

# 5. STRIP — DELETE K-12-SPECIFIC SURFACE
rm -rf data/grade*_stem.json
rm -rf backend/src/demo
rm -rf web/app/\(public\)
rm -rf web/components/demo
# Strip parental_consents schema (write a clean migration; do not just drop)
# Strip school-onboarding routes (replace with org-onboarding placeholder)

# 6. REFRAME — CODEMOD PER RENAME PAIR
# (Run each rename + test suite + commit before next rename)
# Example: curriculum → training_program
#   - Alembic migration renames tables/columns
#   - Grep-and-replace in backend/, web/, pipeline/
#   - Run pytest + npm test
#   - Commit
# Repeat for: grade→role_band, subject→compliance_domain,
# student→learner, school→organization, lesson→module

# 7. RE-BRAND
# Replace README.md, CLAUDE.md (corporate version), top-level positioning copy
# Drop StudyBuddy hero/landing; replace with enterprise placeholder

# 8. SCAFFOLD NEW PRODUCT ARTIFACTS
# - Add ISA.md at repo root (project-ISA per Algorithm v6.2.0+)
# - Add ADR-002 capturing the fork decision (link back to this epic)
# - Re-baseline Alembic migrations (renumber from 0001)

# 9. VERIFY
docker compose up -d
alembic upgrade head
pytest backend/tests
npm --prefix web test
# Expect ~80% pass on first codemod run; iterate

# 10. PUSH bootstrap branch; open PR for review
git push -u origin corporate-fork-bootstrap
```

## 12. Acceptance Criteria (post-fork)

These map to the ISA's ISCs and verify the fork landed cleanly. Tracked in the new repo's project ISA, not here.

- All carry-forward subsystems load without K-12 references in code or DB
- All 6 reframe renames complete with green test suite per pair
- New repo's `pytest` + `npm test` are green
- ADR-002 references this epic
- `git log --all` on the new repo shows StudyBuddy_OnDemand history pre-fork

## 13. Out-of-Scope for this Epic

- Building `dialog_scenario` content type (separate epic — 17.1 or 18)
- Enterprise SSO (SAML / OIDC) — separate epic
- SCORM / xAPI integration — separate epic
- Audit-trail reporting for regulators — separate epic
- SOC 2 compliance program — separate workstream
- Shared-core monorepo extraction — deferred 6–12 months

## 14. Decision Gate (this epic ends here until user responds)

**This is a Y-fork, not a checklist.** The advisor's pushback is real. The user picks the path:

### Path A — Validate first (advisor's recommendation)
1. Add `tenant_type` enum to existing schema (1 migration)
2. Build one scenario-quiz for John Thomas as a design-partner trial inside StudyBuddy_OnDemand
3. Park the brand shortlist
4. Re-evaluate fork after a paid pilot or signed LOI lands

### Path B — Fork now (original plan)
1. **Brand**: ✅ **BriefCase** (picked 2026-05-04)
2. **GitHub org**: `wegofwd2020-hub` or new — still open
3. **Green-light to execute the fork checklist** in section 11 — still open

### Path C — Hybrid
- Pick the brand now (cheap, useful even if Path A wins)
- Run Path A validation track
- Fork on day 1 of a signed pilot

Once you pick a path, broker executes the next steps.
