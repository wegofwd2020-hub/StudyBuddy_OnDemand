# Epic 18 — Corporate Compliance Scenario Catalog

> **Purpose:** Track the long-run catalogue of scenario-based compliance training scenarios for the John-Thomas-style corporate L&D wrapper. Two scenarios shipped; this document captures the full domain coverage we want to build out, with seed scenarios per domain and a per-scenario quality bar.
>
> **Companion docs:**
> - **Strategy:** [`EPIC_17_corporate_ld_fork.md`](EPIC_17_corporate_ld_fork.md) — fork-vs-engine-and-wrappers decision (advisor recommended Path A: tenant_type + design-partner pilot, then fork on signed pilot). Epic 18 is the *content* layer either path produces.
> - **Authoring:** [`../SCENARIO_AUTHORING_TEMPLATE.md`](../SCENARIO_AUTHORING_TEMPLATE.md) — the fillable template for creating a new scenario.
> - **Live demo:** http://localhost:3000/jt — gated landing page (`jt2026`) listing the catalog.
> - **Pipeline:** `pipeline/avatar_worker.py` — D-ID `/talks` API integration generating talking-avatar MP4 per dialog turn.
>
> **Trigger:** John Thomas demo feedback, 2026-04-26 (`memory/project_demo_feedback.md`); revived as a catalog effort 2026-05-04 after the user asked broker to re-document the FCPA + adjacent material referenced in earlier turns.

---

## 1. Vision

A library of 30–60 scenario-based compliance training modules across the major corporate-compliance domains (FCPA, AML, GDPR, Export Controls, Code of Conduct, etc.), each playable as a 1–3 minute talking-avatar dialog followed by a graded T/F or MCQ check. Modules are **scoped queries** in the same scoped-retrieval model that powers StudyBuddy:

`(compliance_domain × role_band × jurisdiction × format × real-world framing) → scenario_module`

This is the wrapper-1 vertical of the engine-and-wrappers thesis (Epic 17). Each module is a parametrisation of the same content engine that produces K-12 lessons.

**End-state criteria:**
- A buyer (CCO / CHRO / Compliance Officer) opens the catalog and sees their domain covered with ≥3 scenarios per domain.
- Each scenario is legally accurate, jurisdiction-tagged, and reviewed by domain expertise before publish.
- Adding a new scenario takes a non-technical author <30 minutes (template → broker → ship).
- Avatar style is configurable per scenario (photorealistic for serious tone; Pixar/cartoon for approachable / educational tone).

---

## 2. Build Status — What ships today

Two scenarios live at `/jt` (see http://localhost:3000/jt — passphrase `jt2026`).

| # | Slug | Title | Domain | Status | Notes |
|---|---|---|---|---|---|
| 1 | `contract-law-001` | Subsidiary Contract Routing — Legal or Not? | FCPA / AML — Beneficial Ownership | ✅ Live (3 video turns, T/F quiz) | Shipped 2026-04-27. Vendor / overseas client / unnamed subsidiary triangle. Photorealistic avatars. |
| 2 | `in-office-behavior` | Inappropriate Workplace Talk — Code of Conduct | Code of Conduct — Harassment / Hostile Workplace | ✅ Live (3 video turns, T/F quiz) | Shipped 2026-05-04. Two IT colleagues commenting on a female coworker's dress. Photorealistic avatars (default). |

---

## 3. Domain Coverage Matrix

Nine target domains covering ≈90% of US-listed-company compliance-training surface. **Bold = covered today**; ★ = high-priority next.

| Domain | Why it matters | Status | Seed scenarios (next-up below) |
|---|---|---|---|
| **FCPA / Anti-Bribery** | DOJ enforcement priority; required annual training at most US-listed multinationals | 🟢 1 shipped (`contract-law-001`) | 7 seeds — see §4.1 |
| **AML / KYC / Sanctions** | FinCEN / OFAC; financial services + any cross-border vendor | 🟡 partial (touched by `contract-law-001`) | 5 seeds — see §4.2 ★ |
| **Export Controls (EAR / OFAC / ITAR)** | Bureau of Industry and Security; severe criminal exposure | ⚪ none | 5 seeds — see §4.3 |
| **GDPR / Data Privacy** | EU regulators; hits any EU-touching SaaS | ⚪ none | 5 seeds — see §4.4 ★ |
| **Code of Conduct / Harassment / DEI** | EEOC; hostile-workplace litigation | 🟢 1 shipped (`in-office-behavior`) | 8 seeds — see §4.5 |
| **Insider Trading / Securities** | SEC; public-company employees + vendors with MNPI access | ⚪ none | 4 seeds — see §4.6 |
| **Cybersecurity / Phishing / Social Engineering** | All sectors; CISA-aligned | ⚪ none | 6 seeds — see §4.7 ★ |
| **Antitrust / Competition Law** | DOJ / FTC; trade-association members + sales orgs | ⚪ none | 4 seeds — see §4.8 |
| **Conflicts of Interest** | SOX-adjacent; cross-cuts every domain | ⚪ none | 4 seeds — see §4.9 |

**Total seed catalog:** 2 shipped + 48 candidates = 50 scenarios across 9 domains.

---

## 4. Per-Domain Seed Scenarios

> Each seed below is a one-line concept ready to feed into the [authoring template](../SCENARIO_AUTHORING_TEMPLATE.md). Role-band tag indicates the primary audience (IC = individual contributor, MGR = manager, EXEC = VP/C-suite, BRD = board member). Multi-band scenarios list the strongest fit first.

### 4.1 FCPA / Anti-Bribery

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| **fcpa-001** ✅ | Subsidiary contract routing — beneficial-ownership red flag | IC, MGR | **SHIPPED as `contract-law-001`** |
| fcpa-002 | "Token" gift to foreign government official ($50 vs $500 dinner) | MGR, EXEC | The classic "*nominal value*" boundary case |
| fcpa-003 | Facilitation payment for licence renewal in country X | IC | Carves out FCPA's narrow facilitation exemption — and why most companies still ban it |
| fcpa-004 | Third-party agent / consultant retention — fixer red flags | MGR, EXEC | "He gets things done" + opaque fee structure |
| fcpa-005 | Joint-venture partner's pre-existing FCPA exposure surfaced in due diligence | EXEC, BRD | M&A deal-team scenario |
| fcpa-006 | Charitable donation to a foundation chaired by a foreign official's spouse | EXEC, BRD | Channel-through-charity pattern |
| fcpa-007 | Books-and-records / accounting violation — slush-fund coding | IC (finance), MGR | The non-bribery half of FCPA |
| fcpa-008 | Distributor markup that funds local "promotional support" — payment ring | MGR, EXEC | Indirect-channel risk |

### 4.2 AML / KYC / Sanctions ★

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| aml-001 | Cash deposit structuring (split below $10k reporting threshold) | IC (banking) | The textbook structuring red flag |
| aml-002 | Suspicious Activity Report (SAR) — file or escalate? | MGR (compliance) | Decision-tree scenario |
| aml-003 | Customer-onboarding KYC: shell-company red flags + UBO chain | IC, MGR | Beneficial-ownership identification |
| aml-004 | Politically Exposed Person (PEP) onboarding — enhanced due diligence | MGR, EXEC | EDD trigger thresholds |
| aml-005 | OFAC sanctions screening — name-match false positive vs real hit | IC, MGR | Sanctions-list workflow |

### 4.3 Export Controls (EAR / OFAC / ITAR)

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| exp-001 | Dual-use technology export — encryption + ECCN classification | IC (eng), MGR | "Is our software EAR99 or 5D002?" |
| exp-002 | Sanctioned-country end-user check — distributor in third country | MGR, EXEC | Re-export risk |
| exp-003 | Deemed-export to a foreign-national employee on the engineering team | MGR | The "national working in your office is also an export" surprise |
| exp-004 | ITAR / military-end-use red flag — drone-related component sale | EXEC | Higher-stakes ITAR vs EAR boundary |
| exp-005 | Transhipment red flag — buyer in friendly country with onward-route to embargoed country | MGR, EXEC | Diversion patterns |

### 4.4 GDPR / Data Privacy ★

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| gdpr-001 | Data Subject Access Request (DSAR) — 30-day deadline + scope | IC (support), MGR | What to include, what to redact |
| gdpr-002 | Consent vs legitimate-interest legal basis for marketing | MGR (marketing) | The basis-selection scenario |
| gdpr-003 | Cross-border data transfer post-Schrems II — SCCs + TIA | MGR, EXEC (legal) | EU-US transfer mechanics |
| gdpr-004 | Breach notification — 72-hour clock + supervisory authority | MGR, EXEC | Incident-response decision |
| gdpr-005 | Right-to-erasure conflicts with legal-hold retention | MGR (legal, IT) | The Article 17 collision |

### 4.5 Code of Conduct / Harassment / DEI

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| **coc-001** ✅ | Inappropriate workplace talk — comments on coworker's dress | IC, MGR | **SHIPPED as `in-office-behavior`** |
| coc-002 | Witness to harassment — report channel vs stay-out | IC, MGR | Bystander-intervention training |
| coc-003 | Retaliation after complaint — manager reassigning the reporter | MGR, EXEC | Anti-retaliation laws |
| coc-004 | Microaggression in team meeting — interrupting / dismissing colleague | MGR | DEI / inclusive-leadership slice |
| coc-005 | Substance use at company offsite — manager's response | MGR, EXEC | Duty-of-care + COC |
| coc-006 | Confidential customer data shared in Slack DM with a friend | IC | Confidentiality breach pattern |
| coc-007 | Personal use of company resources — building a side project on company laptop | IC | The IP / resource-use boundary |
| coc-008 | Romantic relationship between manager and direct report — disclosure obligation | MGR, EXEC | Power-dynamic conflict |

### 4.6 Insider Trading / Securities

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| ins-001 | Material non-public information overheard at the gym — trade or not | IC (fin services) | The "tippee liability" classic |
| ins-002 | Tipping a friend who then trades — derivative liability | IC, MGR | Galleon / Newman-style |
| ins-003 | Trading-window violation — selling during blackout for "personal hardship" | IC (employee), MGR | Window enforcement |
| ins-004 | 10b5-1 plan modification timed near earnings announcement | EXEC | The 10b5-1 plan-misuse pattern |

### 4.7 Cybersecurity / Phishing / Social Engineering ★

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| sec-001 | Vendor email asking to change wire-transfer details (Business Email Compromise) | IC (finance), MGR | The classic BEC scenario |
| sec-002 | Password sharing with executive assistant for "convenience" | IC, EXEC | Shared-credential blast radius |
| sec-003 | USB drive in parking lot — plug it in to find the owner? | IC | The drop-attack vector |
| sec-004 | Public-WiFi at airport — open laptop with sensitive deck | IC, EXEC | Working-on-the-go threat model |
| sec-005 | LinkedIn message from "recruiter" asking for resume + project details | IC (eng) | Spear-phishing reconnaissance |
| sec-006 | Voice-clone phone call from "the CEO" requesting urgent gift-card purchase | IC, MGR | Vishing / deepfake-era social engineering |

### 4.8 Antitrust / Competition Law

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| ant-001 | Pricing chat with competitor at trade-association cocktail hour | MGR (sales), EXEC | The conference-bar scenario |
| ant-002 | "Information sharing" call between competing salespeople — territory hint | MGR (sales) | Information-exchange line |
| ant-003 | Market-allocation hint via a third-party consultant | EXEC | Hub-and-spoke conspiracy pattern |
| ant-004 | Tying arrangement — bundling SaaS module the customer doesn't want | MGR (sales), EXEC | Sherman Act §1 / §2 |

### 4.9 Conflicts of Interest

| Seed | Concept | Role band | Notes |
|---|---|---|---|
| coi-001 | Family member at a vendor company you're evaluating | MGR | Disclosure obligation |
| coi-002 | Side business that could compete with employer | IC, MGR | Outside-activity disclosure |
| coi-003 | Gift from supplier exceeding policy threshold | IC, MGR | Gifts & entertainment policy |
| coi-004 | Speaking fee from a regulated entity covered by your day job | EXEC, BRD | Pay-to-play patterns |

---

## 5. Per-Scenario Quality Bar (definition of "shippable")

Every scenario in the catalog must pass these gates before going live on `/jt`:

| Gate | Probe |
|---|---|
| **Legal accuracy** | Reviewed by a qualified attorney or experienced compliance professional in the relevant domain. Citations to specific regulations / case law in the explanation. |
| **Jurisdiction tagged** | `jurisdiction` field set on the scenario JSON (e.g., `US`, `EU`, `UK`, `multi`). Explanations frame the answer in that jurisdiction's law. |
| **Role-band targeted** | `target_role_band` field set (`IC` / `MGR` / `EXEC` / `BRD` or array). Dialog complexity matches the band. |
| **Dialog ≤ 90s of speech** | Sum of `duration_seconds` across video clips ≤ 90s. Long modules lose engagement. |
| **Quiz internally consistent** | Question + correct answer + explanation form a coherent triple (regression after the `in-office-behavior` quiz logic bug we fixed 2026-05-04). |
| **Avatar style chosen** | Photorealistic OR a stylized image-gen portrait pre-generated and hosted. No reliance on the default Alice photo for shipping content. |
| **Cultural sensitivity reviewed** | Names, ethnicities, accents, and social settings reviewed for stereotype risk. |
| **Anti-criterion: no real names / real companies** | Anti: do not reference real living people, identifiable companies, or pending litigation. |
| **Anti-criterion: no graphic content** | Anti: harassment scenarios depict the *pattern*, not graphic dialogue. Code of Conduct content is illustrative without being gratuitous. |

---

## 6. Authoring Pipeline (idea → live)

```
┌─────────────┐    ┌────────────────┐    ┌──────────┐    ┌─────────────┐    ┌──────────┐
│ Pick a seed │ →  │ Fill out       │ →  │ broker   │ →  │ avatar_     │ →  │ Wire to  │
│ from §4     │    │ SCENARIO_      │    │ produces │    │ worker.py   │    │ /jt      │
│ catalog     │    │ AUTHORING_     │    │ scenario │    │ generates   │    │ landing  │
│             │    │ TEMPLATE.md    │    │ JSON +   │    │ MP4 per     │    │ page     │
│             │    │                │    │ portraits│    │ turn        │    │          │
└─────────────┘    └────────────────┘    └──────────┘    └─────────────┘    └──────────┘
   <5 min            ~20-30 min            ~5 min          ~30-60 sec/turn    ~5 min
```

**Total wall-clock per scenario:** ≈45 minutes for a 3-turn EN scenario, plus legal-review time (out of band).

---

## 7. Roadmap

| Phase | Scope | When |
|---|---|---|
| **Phase A — Coverage spike (3 priority domains)** | Ship 1 scenario each in AML, GDPR, Cybersecurity (the ★ marked above). Reaches ≥1 scenario in 5 of 9 domains. | After Epic 17 path-decision (validate-first vs fork) and a trigger event (paid pilot, design partner, or owner direction) |
| **Phase B — Domain breadth (one per remaining domain)** | Reach ≥1 scenario in all 9 domains. | After Phase A signal validates the format |
| **Phase C — Domain depth (3 per domain)** | Get to ≥3 scenarios per domain. Total ~27 scenarios. | After a paid customer signs |
| **Phase D — Catalog at scale (seed catalog)** | All 50 seed scenarios shipped + role-band coverage matrix complete. | Long-run; multi-quarter |
| **Phase E — Personalised paths** | Customer authors their own scenarios via the template + admin UI. | After Phase C, when buyers ask "can we add our own?" |

---

## 8. Cross-References

- **Strategic frame:** `EPIC_17_corporate_ld_fork.md` — fork-vs-engine-and-wrappers, advisor-recommended Path A
- **Authoring template:** `../SCENARIO_AUTHORING_TEMPLATE.md`
- **Scenario data:** `web/data/scenarios/<slug>_en.json` + `web/data/scenarios/index.ts` (registry)
- **Live videos:** `web/public/scenarios/<slug>/turn{N}.mp4`
- **Pipeline:** `pipeline/avatar_worker.py` (D-ID `/talks` integration)
- **Memory:** `memory/project_demo_feedback.md` (John Thomas signal); `memory/project_special_needs_use_case.md` (Silas — different wrapper, same engine); `memory/feedback_validate_before_split.md` (don't fork on a single signal)
- **Routes:** `/jt` (gated landing) · `/jt/<slug>` (player) — passphrase `jt2026`

---

## 9. Out of Scope (for this epic)

- Building the engine-vs-fork architecture decision (Epic 17 owns that)
- Building a SCORM / xAPI exporter (separate epic when first enterprise buyer demands it)
- Building completion-tracking + audit-grade reporting (separate epic — required before any real customer ships)
- Building a customer-self-serve scenario authoring UI (Phase E)
- Integration with corporate LMS systems (Cornerstone, Workday, SAP Litmos)
- Live-action filmed scenarios (D-ID covers everything we need today)
- Branching / decision-tree scenarios (current model is linear-then-quiz)
- Multi-quiz scenarios (current model is one quiz per scenario)

---

## 10. Decisions log

- 2026-05-04: Catalog epic created. 2 scenarios already shipped. Domain coverage map locked at 9 domains. Seed catalogue locked at 50 scenarios. Phase plan A→E sketched but execution gated on Epic 17 path-decision.
- 2026-05-04: Per-scenario quality bar locked (§5). Anti-criteria added: no real names / no graphic content.
- 2026-05-04: `target_role_band` introduced as a planned field (not in shipped JSONs yet — future-pipe through the avatar_worker patch).
