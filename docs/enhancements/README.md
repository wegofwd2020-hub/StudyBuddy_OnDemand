# Enhancement Tickets — Teacher Portal + Reports

## Overview

7 tickets derived from QA feedback PDF. Core theme: **reduce clutter, add grouping, standardize reports**.

| Ticket | Scope | Est. Days | Status |
|--------|-------|-----------|--------|
| EH-001 | Teacher login UX | 2–3 | — |
| EH-002 | Quiz table format | 3–5 | — |
| EH-003 | Engagement metrics | 2–3 | — |
| EH-004 | Grade/STEAM grouping (core) | 5–7 | — |
| EH-005 | Standardize display | 2–3 | — |
| EH-006 | Admin filters | 3–4 | — |
| EH-007 | Unit perf filters | 2–3 | — |

**Critical path:** EH-004 blocks EH-005. All others independent after dependencies resolved.

---

## Quick Start

### For Product/Design
1. Open `DECISION_QUESTIONS.md`
2. Answer Q1–Q15 (see checklist at end)
3. Share answers with team for alignment

### For Engineering
1. Read `ENHANCEMENT_TICKETS.md` for requirements
2. Wait for decision answers ⬆️
3. Build in order: EH-001 → EH-002 → EH-003 → EH-004 → EH-005 → (EH-006 ∥ EH-007)

### For QA
1. Reference `ENHANCEMENT_TICKETS.md` Acceptance Criteria per ticket
2. Test in order of deployment
3. Flag regressions in existing reports during EH-004 refactor

---

## Key Decisions Needed

| Question | Impact | Owner |
|----------|--------|-------|
| Filter pattern (Q1) | All 4 report pages | Design |
| Time range configurable (Q3) | Backend API shape | Product |
| Grouping hierarchy (Q6) | Report layout | Design |
| Phasing (Q14) | Timeline + resources | Product/Eng |

---

## Known Constraints

- **CLAUDE.md pitfalls apply:** migrations, connection pools, CDN invalidation
- **RLS:** Filters must respect teacher's assigned grades/subjects
- **Mobile:** All new pages must work at <640px (no overflow tables)
- **CSV export:** Must include grade/subject columns for grouping compliance

---

## Files

- **ENHANCEMENT_TICKETS.md** — Detailed requirements, AC, dependencies
- **DECISION_QUESTIONS.md** — 15 architectural/UX decisions (answer before building)
- **README.md** — This file

---

## Next Steps

1. **Product review:** Answer DECISION_QUESTIONS
2. **Design review:** Sketch filter UI pattern + report layouts
3. **Eng estimate:** Break EH-004 into subtasks (most complex)
4. **Sprint plan:** Decide phasing; create GitHub issues from tickets
