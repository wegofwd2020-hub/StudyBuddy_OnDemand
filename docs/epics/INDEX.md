# StudyBuddy OnDemand — Product Epics

Platform roadmap is complete through the Help System (Phases 1–11, A–E, Help).
These epics represent the candidate directions for what comes next.

Add your thoughts directly in each epic file. When an epic is ready to build,
the decision notes become the spec and we develop from there.

---

## Epics

| # | Epic | File | Status |
|---|---|---|---|
| 1 | Multi-Provider LLM Pipeline | [EPIC_01_multi_provider_llm.md](EPIC_01_multi_provider_llm.md) | ✅ Complete (F-1–F-5, 19 tests, migration 0043) |
| 2 | Production Launch & Demo Readiness | [EPIC_02_production_launch.md](EPIC_02_production_launch.md) | 🚧 G-2/G-3/G-5 done; G-1/G-4 blocked on hosting decision |
| 3 | Student Mobile App (Expo / RN) | [EPIC_03_student_mobile.md](EPIC_03_student_mobile.md) | ✅ Path B chosen 2026-04-14; not yet started (parked behind testing + hosting) |
| 4 | Parent Portal | [EPIC_04_parent_portal.md](EPIC_04_parent_portal.md) | 💭 Your call |
| 5 | District Admin | [EPIC_05_district_admin.md](EPIC_05_district_admin.md) | 💭 Your call |
| 6 | Platform Hardening | [EPIC_06_platform_hardening.md](EPIC_06_platform_hardening.md) | 🚧 K-1/K-2/K-3/K-6 done; K-4/K-5 need staging |
| 7 | Self-Serve Demo System | [EPIC_07_self_serve_demo.md](EPIC_07_self_serve_demo.md) | ✅ Complete (Option C guided tour, 15 tests) |
| 8 | Onboarding Completeness (Address & Units) | [EPIC_08_onboarding_completeness.md](EPIC_08_onboarding_completeness.md) | 🚧 H-8/H-9/H-10 (Stream layer + registry) shipped; address + units phases still pending |
| 9 | Accessibility & Personalization | [EPIC_09_accessibility_personalization.md](EPIC_09_accessibility_personalization.md) | 🚧 Umbrella for GitHub issue #189 (3 axe rules disabled in persona e2e suite pending app-side fix) |
| 10 | Curriculum Lifecycle & Governance | [EPIC_10_curriculum_lifecycle.md](EPIC_10_curriculum_lifecycle.md) | 🚧 L-1–L-5 backend shipped (migrations 0046–0048, archive + unarchive + usage endpoints, audit events); L-6 sweeper paused; L-7 super-admin archive view + L-8 school UI + L-9 per-jurisdiction audit + L-10 TTL override pending |
| 11 | Content Presentation & Formatting | [EPIC_11_content_formatting.md](EPIC_11_content_formatting.md) | 🚧 C-1 through C-4, C-6, C-9 shipped; C-5 regen in progress (Grade 11 Commerce done, Grade 11 Science resume in flight); C-7 PDF smoke + C-8 mobile parity pending |

---

## How to use these files

1. Read the **Current state** and **Open questions** sections in each epic.
2. Add your thoughts under **Your decisions / notes** — even rough bullet points are enough to start.
3. When you're ready to build an epic, bring it back and we'll turn your notes into a phased implementation plan.

**Status key:** 💭 Thinking → ✅ Go → ⏸ Parked

---

## Pending discussion topics (parked 2026-04-14)

User is in a testing phase. Resume these conversations afterward, in this order:

1. **Hosting — Production & Demo environments.** Unblocks Epic 2 (G-1, G-4) and
   Epic 6 (K-4, K-5 staging). The single most load-bearing next decision.
2. **Enhanced visual experiments.** Phase 6 shipped basic `ExperimentScreen`;
   open question is whether to invest in interactive simulations (PhET-style
   live manipulation, 3D rendering, lab-bench UI). New epic if pursued.
3. **Pick the next product epic** — Onboarding Completeness (8),
   Accessibility & Personalization (9), Student Mobile (3 — Path B chosen, ready to
   schedule), Parent Portal (4), District Admin (5), or Platform Hardening finish (6).

Already settled, do **not** reopen unless something changes:
- Multi-provider LLM pipeline — shipped as Epic 1 on 2026-04-12.
