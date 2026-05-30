# Visual Validation Guide — 2026-05-24 + Ashokan feedback fixes

Step-by-step walkthrough to **visually confirm** that the fixes tracked in
[`FEEDBACK_TRACKER.md`](FEEDBACK_TRACKER.md) (items VT-1…VT-5, GG-1, AR-1…AR-3,
SR-1, AP-1…AP-5) actually shipped. All eleven actionable items are merged to
`main` via PRs **#372–#378**.

> This guide is for a human clicking through the running app. For an automated
> artifact, a Playwright screenshot run can capture each surface — ask if you
> want that instead.

---

## Where to validate

Pick one environment:

| Env | URL | Notes |
|---|---|---|
| **Live demo** (recommended) | `https://demo.usestudybuddy.com` | Auto-deploys from `main`, so the fixes are live |
| **Local** | `http://localhost:3000` | Requires the dev stack up (`./dev_start.sh`) |

## Login (Milford High School)

Sign in at `/auth/login`.

| Persona | Email | Password | Use for |
|---|---|---|---|
| **School admin** | `admin@milford-high.edu` | `Milford2026!` | Most checks (needs admin-only nav items) |
| **Teacher** | `john.smith@milford-high.edu` | `Milford2026!` | The "teacher sees fewer items" check (AP-1) |

`first_login = FALSE` — straight in, no forced password reset.

> ⚠️ These Milford accounts are the same demo accounts used elsewhere. If they
> are deleted/purged from the demo site, this walkthrough must be re-seeded
> first (`scripts/demo/seed.sh`).

---

## Checklist — 11 items by surface

### A. Left sidebar nav — `SchoolNav` (AP-1, AP-2, AP-3, AP-4, VT-4, VT-5)

Logged in **as admin**, inspect the left rail. It is now **grouped under
headings** instead of one flat ~21-item list.

| Item | What you should see | Old (broken) behavior |
|---|---|---|
| **AP-1** | Sections **Teach · People · Insights · Administration** (last is collapsible) | 21 flat items |
| **VT-4** | **Reports** (under *Insights*) renders **after Teachers** (under *People*) | Reports before Teachers |
| **VT-5** | **Student Progress** uses a line-chart icon; **Students** uses a people icon — *different* icons | Both used the same `<Users>` icon |
| **AP-2** | "Class Overview" is renamed **"Student Progress"** (route still `/school/class/all`) | Labeled "Class Overview" |
| **AP-4** | **No** Settings / Digest / Customize / Help / Sign-out in the rail; footer shows only a role label ("Admin") | Those 4 were rail items |

Then **sign in as the teacher** (`john.smith`) and confirm the rail is
**shorter** — no "Teachers", no "Reports", and the whole "Administration" group
is gone (all admin-only). This is the core AP-1 win for the teacher persona.

### B. Top bar — `PortalHeader` (AP-3, AP-4)

Look at the **top-right of the header**:

- **AP-4** — an **account menu** (avatar/gear dropdown) with **Settings, Digest
  Settings, Customize, Help, Sign out**. Open it and click through.
- **AP-3** — a **Curriculum menu** in the top bar with the three formerly
  confusing items renamed by the verb each performs:
  - "Catalog" → **"Browse Catalog"** (`/school/catalog`)
  - "Our Library" → **"My Curricula"** (`/school/library`)
  - "Content Library" → **"Lessons & Content"** (`/school/curriculum/content`)
  - (plus Curriculum Builder, Review Queue)

### C. Dashboard — `/school/dashboard` (VT-1, VT-3, AR-1, AR-2)

Land here right after admin login:

- **VT-1** — headline KPIs (active students, content readiness, recent activity)
  visible **in the first viewport, no scrolling**.
- **VT-3** — tighter vertical rhythm; no scrolling past large empty gaps.
- **AR-1 / AR-2** — a **themed/colored hero** and **colored action tiles**, not a
  flat wall of text.

### D. Teacher Management — `/school/teachers` (VT-2)

- **VT-2** — directly under the "Teacher Management" heading there's a **roster
  summary**: a **total teacher count** ("N teachers at this school") **and a
  grade-wise breakdown** (count per grade, plus unassigned).

### E. Fonts — any content page (GG-1)

- **GG-1** — open a lesson/content surface; base content font is **16px** (was
  smaller). Reads comfortably without zooming. (AP-5 said the *typeface* looks
  nice — deliberately **not** changed; only the *size* was bumped.)

### F. Docs-only items — no UI to click (AR-3, SR-1)

- **AR-3** (#377) — open **Help** (`/school/help`) and confirm a teacher FAQ /
  guide section exists.
- **SR-1** (#378) — device-target was documented (responsive scope:
  desktop/tablet-first for the school portal). Nothing to click; a written
  decision.

---

## Fastest path (~5 min)

1. Log in as **admin** → on the **dashboard**, eyeball KPIs-above-fold + colored
   hero (VT-1/VT-3/AR-1/AR-2).
2. Scan the **left rail** for grouped headings + Reports-after-Teachers + the two
   distinct icons (AP-1/VT-4/VT-5/AP-2).
3. Open the **top-right account menu** and **curriculum menu** (AP-3/AP-4).
4. Go to **Teachers** → see the count + grade breakdown (VT-2).
5. Open any **lesson** → readable 16px font (GG-1).
6. **Log out, log in as teacher** → confirm the rail is shorter (AP-1, teacher
   persona).

---

## Item → PR map

| Item(s) | Issue | PR |
|---|---|---|
| GG-1 | #365 | #372 — content font size → 16px |
| AR-1, AR-2 | #366 | #374 — dashboard themed hero + colored action tiles |
| AP-1…AP-4, VT-4, VT-5 | #367 | #373 — school nav IA refresh + account menu |
| VT-1, VT-3 | #368 | #375 — KPIs above the fold + density |
| VT-2 | #369 | #376 — teacher count + grade-wise breakdown |
| AR-3 | #370 | #377 — teacher FAQ on the school guide |
| SR-1 | #371 | #378 — responsive/device target doc |

KV-1 and AP-5 were positive feedback (no action).
