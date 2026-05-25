# External Feedback Tracker

Running log of feedback from external reviewers / prospective users on the
live product, with grounded analysis and tracked action items. One section per
reviewer session. Newest at top.

> Scope note: this tracks **UX / product** feedback on shipped surfaces. Demo
> business signals (GTM, pricing, use-case fit, market direction, partnership
> leads) live in [`STRATEGIC_FEEDBACK.md`](STRATEGIC_FEEDBACK.md), agent memory
> (`project_demo_feedback.md`), and `docs/USE_CASES.md`.

---

## Status legend

| Status | Meaning |
|---|---|
| 🔵 Open | Captured, not yet decided |
| 🟡 Decided | Approach chosen, not yet built |
| 🟢 Done | Shipped |
| ⚪ Won't fix | Considered, deliberately declined (reason noted) |

---

## 2026-05-24 — Demo review session (5 reviewers) — School portal + content

**Surface:** School/teacher portal (Dashboard, Teacher Management, left nav) and
lesson content surfaces. Source: `~/Downloads/Feedback.txt`.

> Strategic / market-direction feedback from this same session (notably
> Sundararajan Ramanathan's at length) is logged separately in
> [`STRATEGIC_FEEDBACK.md`](STRATEGIC_FEEDBACK.md). This section keeps only the
> actionable UX/product items.

### Items

| # | Reviewer | Item | Status | Severity |
|---|---|---|---|---|
| KV-1 | Kalpana Vinodh | Positive — "cool and excellent", user-friendly, valuable for students & teachers, multilingual | 🟢 N/A | Positive |
| VT-1 | Venkatesh Thiyagarajan | Dashboard (default landing) requires scrolling to see any statistical data — surface key stats above the fold | 🔵 Open | Med |
| VT-2 | Venkatesh Thiyagarajan | Teacher Management should show a teacher **count**, and a **grade-wise** count if possible | 🔵 Open | Med |
| VT-3 | Venkatesh Thiyagarajan | Excess white space per menu item; realign content and avoid unnecessary scroll through remaining content | 🔵 Open | Med |
| VT-4 | Venkatesh Thiyagarajan | Rearrange nav order — e.g. push **Reports** after **Teachers** | 🔵 Open | Low |
| VT-5 | Venkatesh Thiyagarajan | "Student" and "Class Overview" use the **same icon** — use distinct icons | 🔵 Open | Low |
| GG-1 | Gayathri Gowtham | **Fonts too small** to read | 🔵 Open | High — readability/a11y |
| AR-1 | Anuradha Ravikumar | Website looks **basic / text-heavy**; needs more color and images | 🔵 Open | High — first impression |
| AR-2 | Anuradha Ravikumar | "In modern world, website can have images and videos" | 🔵 Open | Med — also strategic (see STRATEGIC_FEEDBACK) |
| AR-3 | Anuradha Ravikumar | More guidance for teachers, provided **separately** | 🔵 Open | Med |
| SR-1 | Sundararajan Ramanathan | Lesson menu & layout fine in **landscape**; clarify intended device target (tablet/laptop/desktop vs mobile phone) | 🔵 Open | Med — responsive scope |

---

### Analysis

#### VT-1 — Dashboard above-the-fold

`/school/dashboard` is the default post-login landing. The first viewport
should carry the headline KPIs (active students, content readiness, recent
activity) without a scroll. Audit the dashboard card order and vertical
rhythm — likely the same white-space issue as VT-3.

#### VT-2 — Teacher count + grade-wise count

`/school/teachers` lists teachers but (per feedback) shows no aggregate count.
Add a total count header and, if assignment data supports it, a grade-wise
breakdown (teachers carry a grade/stream association). Low backend risk —
counts can be derived client-side from the existing roster query, or add a
small summary field to the teachers endpoint.

#### VT-3 — White space / realignment

Each nav-selected page reportedly has large white space and forces scrolling
past empty content. This is a layout-density pass across school portal pages,
not a single component. Pair with VT-1.

#### VT-4 — Nav order (Reports after Teachers)

Confirmed in `web/components/layout/SchoolNav.tsx`: render order is Dashboard ·
Classrooms · Class Overview · **Reports** · Students · **Teachers** · … —
Reports (admin-only) sits *before* Teachers. Moving the Reports item after
Teachers is a one-line array reorder. Note this overlaps Ashokan's AP-1
(nav grouping) — fold into the same "school-nav IA refresh".

#### VT-5 — Duplicate icon (confirmed)

In `SchoolNav.tsx`, **Class Overview** (`/school/class/all`) and **Students**
(`/school/students`) both render `<Users className="h-4 w-4" />`. Pick a
distinct icon for one — e.g. keep `<Users>` for the student roster and use
`<ClipboardList>` / `<LineChart>` for Class Overview (which is a performance
table, per AP-2). Ties into Ashokan's AP-2 rename suggestion.

#### GG-1 — Fonts too small (a11y)

High priority — a reader could not view the content at all. This intersects
known a11y debt **#189** (`color-contrast` etc.). Check base font-size and the
content reading surfaces specifically; WCAG 2.1 AA expects resizable text and
adequate base size. Contrast with Ashokan's AP-5 ("fonts look very nice") —
his comment was on the *typeface*, hers on *size*; both can be true. Treat as
a sizing/scale fix, not a typeface change.

#### AR-1 / AR-2 — Text-heavy, needs color/images/video

This is the recurring "richer media" theme and directly motivates **Epic 11**
(content formatting: tables, KaTeX, attributed quotes) and the **Visual Library**
work (`docs/VISUAL_LIBRARY_SIDECAR.md`, migrations 0056–0057). AR-1 (UI chrome
color/imagery) is a design pass on the portal + content shell; AR-2 (images &
video *in lessons*) is partly shipped (visual library) and partly strategic
(the demo-video / media-generation track — see STRATEGIC_FEEDBACK and
`docs/DESIGN_demo_videos.md`). File the UI-chrome part here; the media-product
direction lives in the strategic doc.

#### AR-3 — Separate teacher guidance

Echoes the competitive theme of "teacher assistant" tooling (see
STRATEGIC_FEEDBACK competitive scan). Near-term UX form: a dedicated teacher
onboarding/help surface distinct from student help. There is already a
`/school/help` route — assess whether it carries teacher-specific guidance or
needs a teacher-guide section.

#### SR-1 — Device target

Layout works in landscape; the open question is the supported device matrix.
Product intent (CLAUDE.md / Epic 3) is web for admin/teacher + Expo/RN for the
student mobile app. Worth stating the responsive target explicitly on the
school portal (desktop/tablet-first) so reviewers aren't testing on phones and
reading it as a bug.

---

### Proposed next step

Most items (VT-1, VT-3, VT-4, VT-5, GG-1, AR-1) are a **school-portal
density + IA + readability pass** on `SchoolNav.tsx` + dashboard/page layouts —
no migrations, low backend risk. They merge cleanly with Ashokan's nav refresh
(AP-1…AP-4). VT-2 needs a small count addition. GG-1 (font size) is the
highest-severity standalone fix and overlaps a11y #189. Awaiting user decision
on whether to bundle these into one "school portal UX refresh" change.

---

## 2026-05-21 — Ashokan Pitchai — School/Teacher portal nav

**Surface:** School portal, left sidebar (logged in as a school admin/teacher;
screenshot was the "Class Overview" page).
**Screenshot:** `~/Downloads/ap_screen_comment.jpeg`

### Verbatim feedback

> The left menu has too many items.
> 1. Is Class overview related to a particular classroom?
> 2. Whats the difference between Catalog and Library?
>
> Settings/Digest settings should probably be on the top bar.
>
> The fonts look very nice.

### Items

| # | Item | Status | Severity |
|---|---|---|---|
| AP-1 | Left menu has too many items | 🔵 Open | High — first-impression clutter |
| AP-2 | "Class Overview" scope unclear (per-classroom?) | 🔵 Open | Med — label/IA |
| AP-3 | "Catalog" vs "Library" indistinguishable (actually 3 overlapping items) | 🔵 Open | High — core IA confusion |
| AP-4 | Settings / Digest Settings belong on the top bar | 🔵 Open | Med — IA convention |
| AP-5 | Fonts look very nice | 🟢 N/A | Positive — keep current type system |

---

### Analysis

Nav is rendered by `web/components/layout/SchoolNav.tsx` (items array lines
42–140). It carries **21 items**, **12 of them admin-only**. Ashokan was logged
in as an admin, so he saw the full set — which is exactly the clutter he flagged.

#### AP-1 — Too many items

Current full list (admin view), in render order:

Dashboard · Classrooms · Class Overview · Reports* · Curriculum · Catalog ·
Our Library · Review Queue* · Content Library · Students · Teachers* · Alerts ·
Digest Settings · Subscription* · Storage* · Visual Library* · Content
Retention* · Backups* · Settings · Customize · Help
*(\* = admin-only)*

The list mixes **daily-use teacher tasks** (Dashboard, Class Overview, Alerts)
with **occasional admin config** (Backups, Storage, Retention, Subscription) and
**content-management** (Catalog, Our Library, Content Library, Curriculum,
Review Queue) at a single flat level. No grouping, no separation of frequency.

**Recommendation:** group into labelled sections rather than one flat list, e.g.

- **Teach** — Dashboard, Class Overview, Classrooms, Alerts
- **Content** — Catalog, Our Library, Content Library, Curriculum, Review Queue
- **People** — Students, Teachers
- **Admin** (collapsible, admin-only) — Subscription, Storage, Backups,
  Content Retention, Visual Library, Reports
- Move **Settings, Digest Settings, Customize, Help** off the rail (see AP-4).

This alone drops the visible top-level count for a teacher from ~13 to ~8.

#### AP-2 — "Class Overview" scope

Route: `/school/class/all` (`web/app/(school)/school/class/[class_id]/page.tsx`).
It is **school-wide, not per-classroom** — a flat sortable table of every student
with a "My students / All school" scope toggle and a Grade filter (visible in the
screenshot). The name reads like it should be tied to one class, which is the
confusion.

Distinct from neighbours:
- **Dashboard** = aggregate KPI summary.
- **Classrooms** = per-classroom roster + package management (this is the
  actual per-class view).
- **Class Overview** = per-**student** performance across the school.

**Recommendation:** rename to **"Students"** or **"Student Progress"** /
**"Performance"** — it is a student roster with metrics, not a class view. Note
there is already a separate "Students" item (admin management of accounts), so
disambiguate: e.g. "Student Progress" (this analytics table) vs "Manage
Students" (account admin). Folding both under a **People** group would resolve
the collision.

#### AP-3 — Catalog vs Library (the sharpest one)

There are **three** content items that all sound like "a library", and their
names don't convey the difference. They are actually a **sequential pipeline**:

| Nav label | Route | What it really is |
|---|---|---|
| **Catalog** | `/school/catalog` | Browse **platform** packages the school does *not* yet own; admin adopts one into the library. *(the shop window)* |
| **Our Library** | `/school/library` | Packages the school **has adopted**; manage active/inactive, import & customize. *(owned inventory)* |
| **Content Library** | `/school/curriculum/content` | The **generated AI lesson/quiz/tutorial files** inside owned packages; view & review. *(the actual content)* |

Flow: **Catalog → (adopt) → Our Library → (import/customize) → Content Library.**

**Recommendation:** rename for the verb each performs, and nest them so the
relationship is visible:
- Catalog → **"Browse Catalog"** or **"Add Curricula"**
- Our Library → **"My Curricula"** or **"Adopted Curricula"**
- Content Library → **"Lessons & Content"** or **"Generated Content"**

Better still, collapse under one **Content** parent with the three as children,
so a teacher sees one entry until they expand. Curriculum and Review Queue also
belong in that group.

#### AP-4 — Settings / Digest on the top bar

Convention agreement: per-user/account config (Settings, Digest Settings,
Customize, Help) conventionally lives in a **top-right account menu / gear**, not
the primary nav rail. Currently all four are rail items at the bottom.

Routes today: Settings `/school/settings`, Digest `/school/digest`, Customize
`/school/settings/customize`, Help `/school/help`.

**Recommendation:** move these four into a top-bar avatar/gear dropdown. Frees
four rail slots and matches user expectation. Help could stay as a "?" icon in
the top bar too. Requires a `PortalHeader` account menu for the school portal
(check whether one already exists for students).

#### AP-5 — Fonts (positive)

Type system is well received. **Do not change** the current font stack /
sizing as part of any nav rework. Carry the same type treatment into the
top-bar account menu.

---

### Proposed next step

These are all IA/labelling changes on one component (`SchoolNav.tsx`) plus a
top-bar account menu. Low backend risk, no migrations. Suggest a single
"school-nav IA refresh" change: grouping + renames + move config to top bar.
Awaiting user decision on labels before building.
