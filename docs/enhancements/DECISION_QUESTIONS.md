# Enhancement Decision Questions

Answer these before starting implementation. Decisions cascade down.

---

## ⭐ Core Architecture

### Q1: Filter Pattern
**Affects:** EH-004, EH-006, EH-007

**Question:** How should Grade/Subject filters appear?

**Options:**
- **A) Dropdown + side effect**  
  Single dropdowns per filter. Selection immediately reloads table. State in URL query params.
  - Pro: Simple, familiar
  - Con: Multiple clicks for combined filters; page flickers on change

- **B) Sidebar with apply button**  
  Filters in collapsible left panel. "Apply" button triggers data reload.
  - Pro: Batch multiple filters; no flicker; can preview counts
  - Con: Takes screen space; extra click needed

- **C) Tabs + filters**  
  Grade/Subject as tab groups (Grade 8, Grade 9, etc. in tabs). Subject as secondary filter.
  - Pro: Fast grade switching; no UI churn
  - Con: Only works if teacher has ≤3 grades; hard to see "all grades" view

**Decision:** _______________

**Rationale:** _______________

---

### Q2: Default State
**Affects:** All report pages

**Question:** When teacher opens a report, what should they see first?

**Options:**
- **A) Filtered to their assigned class only**  
  Show only the students/units they teach. Must query `teacher_capabilities` on page load.
  
- **B) All data unfiltered, invite to filter**  
  Show everything. UI hint: "Filter by Grade" above the table.

- **C) Smart: if 1 grade, show only that; if multi, show all**  
  Query teacher's classes; if single, pre-filter. If multi, show all with hint.

**Decision:** _______________

**Rationale:** _______________

---

## 📊 Engagement Metrics (EH-003)

### Q3: Time Range
**Question:** Should "Last 30 days" be fixed or configurable?

**Options:**
- **A) Fixed to 30 days**  
  No UI control. Simple API contract. Reports always show same window.
  
- **B) Configurable: 7d, 30d, 90d, All-time**  
  Tab buttons or dropdown above metrics. Remember last selection.

- **C) Rolling: last 30d, month-to-date, year-to-date**  
  Richer context but more complex backend queries.

**Decision:** _______________

**Rationale:** _______________

---

### Q4: "Active Students" Definition
**Question:** What counts as "active (last 30d)"?

**Options:**
- **A) Has ≥1 lesson view**  
  Opened a lesson card. Lowest bar.
  
- **B) Has ≥1 session (lesson, quiz, or tutorial)**  
  Started and attempted content. Middle bar.

- **C) Has ≥1 completed quiz attempt or passed quiz**  
  Only counted if they submitted an answer. Highest bar.

**Decision:** _______________

**Rationale:** _______________

---

## 📋 Report Grouping (EH-004, EH-005)

### Q5: Collapsible Sections — Default State
**Question:** When report loads, which grade/subject sections are expanded?

**Options:**
- **A) All collapsed**  
  User must click to see content. Faster page load.
  
- **B) First grade expanded, rest collapsed**  
  Guidance visible; clean UI.

- **C) All expanded**  
  Everything visible at once. Might be long page.

- **D) Remember from last visit**  
  localStorage tracks open/closed state. Best UX but complex.

**Decision:** _______________

**Rationale:** _______________

---

### Q6: Grouping Hierarchy
**Question:** What's the visual nesting order?

**Options:**
- **A) Grade > Subject > Unit**  
  `Grade 8 — Mathematics > Fractions and Decimals > G8-MATH-001`

- **B) Subject > Grade > Unit**  
  `Mathematics > Grade 8 > Fractions and Decimals > G8-MATH-001`

- **C) Subject only (Grade in label)**  
  `Mathematics (Grade 8, 9, 10) > Fractions...`  
  Reduces nesting depth.

**Decision:** _______________

**Rationale:** _______________

---

### Q7: Zero-Activity Units Display
**Question:** How should "Units with no activity" be presented?

**Options:**
- **A) Comma-separated codes**  
  `G8-MATH-001, G8-MATH-003, G8-MATH-005`  
  Compact; scrollable.

- **B) Grid of badges/chips**  
  Colored boxes per unit. More visual; takes more space.

- **C) Collapsible list (one per line)**  
  `▼ G8-MATH (5 units)`  
  Balanced; still organized.

**Decision:** _______________

**Rationale:** _______________

---

## 📱 Teacher Login (EH-001)

### Q8: Multi-Class Display
**Question:** When a teacher has Grade 8 Math + Grade 9 Physics, what do they see?

**Options:**
- **A) Merged list with Grade filter**  
  One table; Grade 8 and 9 rows mixed. Filter to show one grade.
  
- **B) Separate card per grade**  
  `Grade 8 — Mathematics [enrolled students...]` and `Grade 9 — Physics [...]` as side-by-side cards.

- **C) Tabs: one tab per class**  
  Click "Grade 8 Math" tab to see that roster. Active tab remembered.

**Decision:** _______________

**Rationale:** _______________

---

### Q9: Grade Filter Scope
**Question:** Filter applies to what?

**Options:**
- **A) Student list only**  
  Enrolled students table filters; Logout and other elements stay put.

- **B) Entire page**  
  Grade filter affects all content below (engagement, feedback, etc.).

- **C) No filter (fixed to class)**  
  Teacher sees only their assigned class; no filter needed.

**Decision:** _______________

**Rationale:** _______________

---

## 🎯 Quiz Formatting (EH-002)

### Q10: Table Detection
**Question:** How should the backend know when to render as table vs. text?

**Options:**
- **A) Content type flag in JSON**  
  Quiz schema includes `{type: 'table', ...}`. Pipeline marks during generation.

- **B) Regex heuristic**  
  Renderer detects `Attribute | Value | Value` pattern; converts automatically.

- **C) Manual override in content review**  
  Admin can mark comparison questions as "table" during content review.

**Decision:** _______________

**Rationale:** _______________

---

### Q11: Table Responsiveness
**Question:** How should tables render on mobile (<640px)?

**Options:**
- **A) Horizontal scroll**  
  Table stays wide; user swipes left/right.

- **B) Card stack**  
  Each row becomes a card (e.g., "Row 1: Attribute=X, Ltd=Y, PLC=Z").

- **C) Collapse columns**  
  Show first 2 columns; tap to expand others inline.

**Decision:** _______________

**Rationale:** _______________

---

## 🔗 Data & Backend

### Q12: CSV Export Grouping
**Question:** How should exported CSV be structured?

**Options:**
- **A) Single sheet, all rows grouped**  
  `grade, subject, unit_id, metric_1, metric_2, ...` Sorted by grade/subject.

- **B) Multiple sheets per grade**  
  One sheet named "Grade 8 Math", another "Grade 9 Science", etc.

- **C) Summary + detail sheets**  
  Sheet 1 = totals by grade/subject. Sheet 2 = all rows with filters applied.

**Decision:** _______________

**Rationale:** _______________

---

### Q13: Cache Strategy
**Question:** How long should grouped/filtered report data be cached?

**Options:**
- **A) No cache**  
  Always compute on request. Accurate; may be slow.

- **B) 5-minute cache per grade/subject combo**  
  `CACHE_KEY: f"report:{school_id}:{grade}:{subject}:{end_date}"`

- **C) Materialized view**  
  Database view refreshes nightly. Reports query view directly.

**Decision:** _______________

**Rationale:** _______________

---

## 📅 Rollout & Priorities

### Q14: Phasing
**Question:** Build order and rollout phases?

**Options:**
- **A) Everything at once (Phase 1)**  
  All 7 tickets merged in one PR. Single deploy.

- **B) 3 phases: UX → Metrics → Grouping**  
  Phase 1 (EH-001, EH-002). Phase 2 (EH-003). Phase 3 (EH-004–007).

- **C) Incremental: ship what's ready**  
  EH-001 ASAP (teacher login). EH-003 next. Rest as ready.

**Decision:** _______________

**Rationale:** _______________

---

### Q15: Backward Compatibility
**Question:** Must old content/reports render correctly?

**Options:**
- **A) Strict backward compatibility**  
  Old pipe-delimited quiz questions still work as text fallback.

- **B) One-time migration**  
  Pipeline re-renders old content to new schema on first access. Old schema dropped.

- **C) Dual-path rendering**  
  Frontend detects schema version; uses old or new renderer accordingly.

**Decision:** _______________

**Rationale:** _______________

---

## Notes for Answering

- **Interdependencies:** Q1 cascades to Q5, Q6, Q8, Q9, Q12.
- **Backend effort:** Q12 and Q13 drive backend scope.
- **Scope risk:** Q14 (phasing) determines delivery timeline.
- **UX debt:** Answering Q1–Q11 carefully now prevents rework later.

**Template for each answer:**
```
Decision: [A/B/C]

Rationale: [1-2 sentences. Why is this right for StudyBuddy? Constraints? User research?]

Blockers/assumptions: [Any open questions? Who needs to sign off?]
```

---

## Answer Checklist

- [ ] Q1: Filter pattern
- [ ] Q2: Default state
- [ ] Q3: Time range
- [ ] Q4: "Active" definition
- [ ] Q5: Collapsible default
- [ ] Q6: Hierarchy
- [ ] Q7: Zero-activity display
- [ ] Q8: Multi-class display
- [ ] Q9: Grade filter scope
- [ ] Q10: Table detection
- [ ] Q11: Mobile tables
- [ ] Q12: CSV structure
- [ ] Q13: Cache strategy
- [ ] Q14: Phasing
- [ ] Q15: Backward compat
