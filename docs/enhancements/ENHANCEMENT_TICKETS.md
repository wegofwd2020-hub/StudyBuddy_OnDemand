# Enhancement Tickets

## EH-001: Teacher Login — Student List Columns

**Component:** `web/app/(school)/dashboard`  
**Epic:** UX improvements — teacher portal

### Requirements
- Add `name` + `grade` columns to enrolled students table
- Add Grade filter dropdown for multi-class teachers
- Move Logout to top-right corner (header)
- Add Subject column

### Acceptance Criteria
- [ ] Student name, grade, subject visible in table
- [ ] Grade filter hides irrelevant students
- [ ] Logout button appears in header (not page body)
- [ ] Table sorts/filters without API call (client-side)
- [ ] Mobile responsive (single-column on <768px)

### Dependencies
- Students data must include `name`, `grade`, `subject`
- Teacher JWT decoder identifies multi-class status

---

## EH-002: Quiz Question Formatting — Table Layout

**Component:** `web/app/(school)/quiz` or `backend/src/content/renderer.py`  
**Epic:** Content presentation

### Requirements
- Convert pipe-separated comparison tables to HTML `<table>`
- Example: `Attribute | Ltd | PLC` → 3-column table with borders
- Apply to: business structures, feature comparisons, metric breakdowns

### Acceptance Criteria
- [ ] Pipe-delimited input detected and converted to semantic HTML
- [ ] Table renders with borders, headers, cell padding
- [ ] Responsive: stack on mobile (or horizontal scroll)
- [ ] Markdown parser handles both old and new format
- [ ] No impact on existing text/list questions

### Dependencies
- Content pipeline must generate tables in JSON (not markdown)
- Frontend renderer must handle `{type: 'table', rows: [...]}` schema

---

## EH-003: Teacher Engagement Report — Metrics Update

**Component:** `web/app/(school)/reports/engagement`  
**Epic:** Analytics dashboard

### Requirements
Replace:
```
Active Students: 4
Activity Rate: 57%
Audio Engagement: 0%
```

With:
```
Enrolled Students: 7
Active (last 30d): 57%
Lessons Viewed: 121
Pass Rate: 60%
Quiz Attempts: 41
Unreviewed Feedback: 23
```

### Acceptance Criteria
- [ ] All 6 metrics fetch from backend
- [ ] Time range defaults to "Last 30 days" (configurable)
- [ ] Card layout matches dashboard tile design
- [ ] No API call > 500ms
- [ ] Metrics update on page load + refresh button

### Backend Changes
- `GET /schools/{school_id}/reports/engagement?days=30` returns new shape
- Query: count enrolled, active (has session in range), viewed lessons, quiz pass %, attempts, feedback unreviewed

### Dependencies
- Backend must expose aggregated metrics endpoint
- Database views or materialized views for perf

---

## EH-004: Report Grouping by Grade/STEAM

**Component:** `web/app/(school)/reports/*`  
**Epic:** Data organization — dashboards

### Requirements
- Group all reports by `grade` + `subject_code` hierarchy
- Replace flat lists with collapsible sections per grade/subject
- Apply to: Feedback, CSV Export, Overview, Unit Performance

### Scope
- **Feedback report:** Group feedback rows by grade/subject
- **CSV export:** Add grade/subject column; sort by grade/subject
- **Overview report:** "Units with Struggles" and "Units with no activity" grouped by grade/subject
- **Unit Performance report:** Add Grade/STEAM filter dropdown

### Acceptance Criteria
- [ ] Collapsible sections by grade (e.g., "Grade 8 — Mathematics")
- [ ] Default expanded for grade with most activity
- [ ] Filter dropdown on all four report pages
- [ ] CSV export includes grade/subject columns
- [ ] Term "Units with no activity" used consistently (not "zero activity")

### Backend Changes
- `GET /reports/feedback?group_by=grade_subject` returns grouped data
- `GET /reports/units-zero-activity?grade=8&subject=MATH` for filtering

---

## EH-005: Engagement Zero-Activity Units — Standardize Display

**Component:** `web/app/(school)/reports/engagement/zero-activity`  
**Epic:** Report consistency

### Requirements
- Apply same display format as "Units with zero activity" to all related sections
- Format: "Grade N — Subject Name" headings with unit codes listed below
- Standardize across: Overview Report, Engagement Report, Unit Performance

### Acceptance Criteria
- [ ] All three reports show units in identical format
- [ ] Grade/subject as collapsible headers
- [ ] Unit codes displayed as comma-separated or grid
- [ ] No orphaned unit codes
- [ ] Visual hierarchy clear (grade > subject > units)

### Dependencies
- EH-004 must be merged first (grouping logic)
- Backend returns units structured by grade/subject

---

## EH-006: Admin Overview Report — Add Filters

**Component:** `web/app/(admin)/reports/overview`  
**Epic:** Teacher admin portal

### Requirements
- Add Grade filter dropdown
- Add Subject filter dropdown
- Filter applies to: metric cards, "Units with Struggles", "Units with no activity"
- Remember last selection (localStorage)

### Acceptance Criteria
- [ ] Filters are independent (can select grade only, subject only, both, or all)
- [ ] "All Grades" and "All Subjects" as default options
- [ ] Metrics recalculate on filter change
- [ ] URL query params reflect selection (?grade=8&subject=MATH)
- [ ] Mobile-friendly filter UI

### Backend Changes
- Extend all report endpoints to accept `?grade=N&subject=CODE` params
- Return full dataset if no params (for "all" view)

---

## EH-007: Unit Performance Report — Add Grade/STEAM Filter

**Component:** `web/app/(school)/reports/unit-performance`  
**Epic:** Report consistency

### Requirements
- Add Grade dropdown
- Add Subject dropdown
- Filter persists across page refresh (query params + localStorage)
- Same UX pattern as EH-006

### Acceptance Criteria
- [ ] Grade/Subject filters match EH-006 UI
- [ ] Table rows update on filter change
- [ ] Default: show all
- [ ] Mobile responsive

### Backend Changes
- Extend Unit Performance endpoint to accept grade/subject filters

---

## Summary Table

| Ticket | Feature | Complexity | Dependency |
|--------|---------|------------|------------|
| EH-001 | Teacher login UX | Low | — |
| EH-002 | Quiz table formatting | Medium | Content schema |
| EH-003 | Engagement metrics | Medium | Backend aggregates |
| EH-004 | Grade/STEAM grouping | High | Backend + UI refactor |
| EH-005 | Standardize display | Medium | EH-004 |
| EH-006 | Admin filters | Medium | Backend params |
| EH-007 | Unit perf filters | Low | Backend params |

**Build order:** EH-001 → EH-002 → EH-003 → EH-004 → EH-005 → (EH-006, EH-007 parallel)
