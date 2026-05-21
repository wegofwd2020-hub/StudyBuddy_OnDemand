# External Feedback Tracker

Running log of feedback from external reviewers / prospective users on the
live product, with grounded analysis and tracked action items. One section per
reviewer session. Newest at top.

> Scope note: this tracks **UX / product** feedback on shipped surfaces. Demo
> business signals (GTM, pricing, use-case fit) live in agent memory
> (`project_demo_feedback.md`) and `docs/USE_CASES.md`.

---

## Status legend

| Status | Meaning |
|---|---|
| 🔵 Open | Captured, not yet decided |
| 🟡 Decided | Approach chosen, not yet built |
| 🟢 Done | Shipped |
| ⚪ Won't fix | Considered, deliberately declined (reason noted) |

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
