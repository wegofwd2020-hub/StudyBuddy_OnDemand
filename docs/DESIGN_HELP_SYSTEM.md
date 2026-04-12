# StudyBuddy OnDemand — Contextual Help System Design

**Status:** Design exploration — not yet scheduled  
**Date:** 2026-04-12 (revised 2026-04-12 — Layer 0 Discovery added)  
**Scope:** Pre-auth product tour + in-app dynamic help delivery + supporting content library

---

## 1. The Core Idea

The help system is a **three-layer architecture**. Each layer serves a distinct user
state — before login, just after registration, and during everyday use:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  LAYER 0 — DISCOVERY  (pre-auth, public site)                       │
│                                                                     │
│  Visitor asks: "What can I actually do with this?"                  │
│                                                                     │
│  No JWT. No account. Goal is exploration, not task completion.      │
│  Role selector → interactive capability tour per persona.           │
│  CTA at the end of each tour path → registration.                   │
│                                                                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │  converts to
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  LAYER 1.5 — SETUP CHECKLIST  (post-registration, zero-state)       │
│                                                                     │
│  New school admin just registered. School has:                      │
│    • 0 teachers provisioned                                         │
│    • 0 students enrolled                                            │
│    • 0 curriculum assigned                                          │
│                                                                     │
│  Triggered by: setup_complete=false (derived from account state).   │
│  Dismissed permanently once all checklist items are done.           │
│  Centre-stage component — not hidden inside the help widget.        │
│                                                                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │  graduates to
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  LAYER 2 — DELIVERY  (dynamic, AI-generated, authenticated)         │
│                                                                     │
│  User asks: "How do I add a student to a classroom?"               │
│                                                                     │
│  System knows:                                                      │
│    • Who they are   → School Admin                                  │
│    • Where they are → /school/classrooms                            │
│    • What they have → 2 classrooms, 0 students enrolled             │
│                                                                     │
│  Generates: step-by-step instructions tailored to that context     │
│                                                                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │  draws from
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  LAYER 1 — LIBRARY  (static, human-authored)                        │
│                                                                     │
│  • Capability overviews (per persona) — what the system can do      │
│  • Use-case flows (SVG)               — end-to-end sequences        │
│  • Design documentation (HTML)        — how the system works        │
│  • Step-by-step procedures            — canonical task sequences    │
│  • Persona glossaries                 — role-specific terminology   │
│  • UI screenshots / annotated diagrams                              │
│                                                                     │
│  Shared source of truth for all three layers above.                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**What each layer answers:**

| Layer | User state | Question answered |
|---|---|---|
| 0 — Discovery | No account | "What can I do if I sign up?" |
| 1.5 — Setup Checklist | Registered, zero setup | "What do I do first?" |
| 2 — Delivery | Active user, daily use | "How do I do X right now?" |
| 1 — Library | Any | Ground truth for all layers |

The layers are **separate components** that share the same authored content library.
They are not a single widget with modes — keeping them separate prevents each from
being compromised by the constraints of the others.

The delivery layer is not a chatbot. It is a **contextual guide generator** — given a
question and context, it produces a numbered, role-appropriate task walkthrough.

---

## 2. Personas and Role Context

Three personas, each with different vocabulary, permissions, and journeys:

```
┌─────────────────┬──────────────────────────────────────────────────┐
│ Persona         │ Typical questions                                │
├─────────────────┼──────────────────────────────────────────────────┤
│ School Admin    │ "How do I add a teacher?"                        │
│                 │ "Why can't my student see the curriculum?"       │
│                 │ "How do I approve a curriculum build?"           │
│                 │ "What does 'archived' mean for a classroom?"     │
├─────────────────┼──────────────────────────────────────────────────┤
│ Teacher         │ "How do I create a classroom?"                   │
│                 │ "How do I assign content to my students?"        │
│                 │ "What is a curriculum package?"                  │
│                 │ "How do I see which students are at risk?"       │
├─────────────────┼──────────────────────────────────────────────────┤
│ Student         │ "How do I start a quiz?"                         │
│                 │ "Where is my lesson for today?"                  │
│                 │ "What happens if I don't finish?"                │
│                 │ "How do I change my password?"                   │
└─────────────────┴──────────────────────────────────────────────────┘
```

The same underlying question ("how do I see my curriculum?") produces a different
answer depending on who asks:
- **School Admin** → sees the curriculum assignment dashboard, build status, grade mappings
- **Teacher** → sees the classroom packages assigned to their classroom
- **Student** → sees the unit list inside their classroom's merged content view

The delivery layer must know the persona before generating a response. This is read
from the authenticated JWT — never asked of the user.

---

## 2a. Layer 0 — Discovery (Pre-Auth Product Tour)

### Purpose

A prospective school admin, teacher, or student lands on the public site and wants
to understand what they can do before committing to registration. This is a
**conversion surface**, not a support surface. The goal is to show capability
confidently and end with a clear call to action.

### User journey

```
Public landing page
        │
        ▼
"Explore the platform" CTA
        │
        ▼
Role selector  ┌─────────────────┬──────────────────┬───────────────┐
               │  School Admin   │    Teacher        │    Student    │
               └────────┬────────┴────────┬──────────┴──────┬────────┘
                        │                 │                  │
                        ▼                 ▼                  ▼
               Capability tour    Capability tour    Capability tour
               (admin persona)    (teacher persona)  (student persona)
                        │
                        ▼
               "Ready to get started?" → Register your school
```

### Tour format

Each persona tour is a **linear, screen-by-screen walkthrough** — not a free-form
explorer. Each screen shows:

1. **What you can do** — a single capability, named and described in plain language
2. **What it looks like** — an annotated screenshot or an SVG flow diagram from the library
3. **Why it matters** — one sentence connecting the capability to an outcome the user cares about

The tour is role-scoped. A visitor who selects "School Admin" sees admin capabilities
only — not teacher or student views.

### School Admin tour — capability sequence

```
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  1  │   │  Register your school                                   │
│     │   │  One sign-up gives your whole school access.            │
│     │   │  No per-teacher or per-student account needed to start. │
└─────┘   └─────────────────────────────────────────────────────────┘
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  2  │   │  Provision teachers                                      │
│     │   │  Add your teaching staff by email. They receive a       │
│     │   │  default password and are prompted to reset it on       │
│     │   │  first login — no separate invite email workflow.       │
└─────┘   └─────────────────────────────────────────────────────────┘
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  3  │   │  Enrol students                                          │
│     │   │  Upload a roster or add individually by email + grade.  │
│     │   │  Assign each student to a teacher and classroom.        │
└─────┘   └─────────────────────────────────────────────────────────┘
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  4  │   │  Build a custom curriculum                               │
│     │   │  Define subjects and units, submit for review, and      │
│     │   │  trigger an AI-generated content build — lessons,        │
│     │   │  quizzes, tutorials, and audio — per grade and language. │
└─────┘   └─────────────────────────────────────────────────────────┘
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  5  │   │  Assign content to classrooms                            │
│     │   │  Attach curriculum packages to classrooms. Students     │
│     │   │  see only the content assigned to their classroom.      │
└─────┘   └─────────────────────────────────────────────────────────┘
┌─────┐   ┌─────────────────────────────────────────────────────────┐
│  6  │   │  Track progress and at-risk students                     │
│     │   │  Per-student completion rates, quiz scores, and a       │
│     │   │  teacher-facing at-risk flag for students falling behind.│
└─────┘   └─────────────────────────────────────────────────────────┘

           ✦  "Ready to get started? Register your school →"
```

### Teacher tour — capability sequence

```
1. Accept your school's invitation
2. Create classrooms and assign students
3. Attach curriculum packages to your classrooms
4. View student progress and at-risk flags
5. Build a custom curriculum definition (submitted to admin for approval)
6. Download class reports

   ✦  "Already have a school code? Log in here →"
```

### Student tour — capability sequence

```
1. Receive your school login
2. Access your personalised lesson and quiz content
3. Work through units at your own pace (offline supported)
4. See your progress and streaks
5. Take quizzes and get instant feedback

   ✦  "Your teacher will send you a login. Ask them for your school code →"
```

### Technical constraints

- **No JWT, no API calls.** The tour is pure static HTML + CSS + JavaScript. It can
  be deployed independently of the backend.
- **Content is drawn from the Library** — capability descriptions and SVG flows are
  not written twice. The tour references the same source content the AI delivery
  layer uses.
- **No help widget.** The floating help button is for authenticated users. The tour
  replaces it for the pre-auth surface.
- **Handoff point.** The final screen of each tour links to the registration page
  (admin/teacher) or shows a "contact your school" message (student — who cannot
  self-register).

### Route

Lives under `/(public)/tour` in the Next.js app router:

```
/(public)/tour/page.tsx          — role selector
/(public)/tour/school-admin/     — admin capability screens
/(public)/tour/teacher/          — teacher capability screens
/(public)/tour/student/          — student capability screens
```

No auth required. No `LocalAuthGuard` wrapper.

---

## 2b. Layer 1.5 — Setup Checklist (Post-Registration, Zero-State)

### Purpose

A school admin who has just registered has an account but an empty school. They have
a JWT and a role — but no teachers, no students, no curriculum, no classrooms. The
contextual help widget (Layer 2) is not useful here: there is nothing to help with
yet. What this user needs is a **guided first-run sequence** that walks them through
the minimum viable school setup.

This is distinct from both the public tour (no account) and the help widget (active
use). It is centre-stage, not a floating widget.

### Trigger condition

```python
setup_complete = (
    teacher_count > 0
    and student_count > 0
    and classroom_count > 0
    and curriculum_assigned
)
```

Computed on the school portal layout load from a lightweight `GET
/schools/{id}/setup-status` endpoint. Cached in React Query with a 30-second TTL.
Once `setup_complete = true`, the checklist is permanently dismissed and never shown
again.

### Checklist layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Welcome to StudyBuddy OnDemand — let's set up your school          │
│  Complete these steps to get your first classroom running.          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ☐  1. Add at least one teacher                                     │
│       → Go to Teachers                                              │
│                                                                     │
│  ☐  2. Enrol your first students                                    │
│       → Go to Students                                              │
│                                                                     │
│  ☐  3. Create a classroom and assign students                       │
│       → Go to Classrooms                                            │
│                                                                     │
│  ☐  4. Assign a curriculum package to the classroom                 │
│       → Browse the Catalog                                          │
│                                                                     │
│  ── Optional ────────────────────────────────────────────────────   │
│                                                                     │
│  ○  Build a custom curriculum for your grade                        │
│       → Define a curriculum                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

Checked items are computed from live account state — not stored as user preferences.
"Teacher added" is true when `teacher_count > 0`, not when the user clicked a checkbox.

### Placement

- Shown as a **banner or panel at the top of the school dashboard**, above all other
  content, when `setup_complete = false`
- It is NOT inside the help widget drawer
- It is NOT a modal (modals block navigation; the user needs to navigate to complete steps)
- Each step is a direct link to the relevant page — no intermediate screens

### Relationship to the public tour

The checklist is the authenticated continuation of the admin capability tour:

```
Public tour (Layer 0)        →    Registration    →    Setup checklist (Layer 1.5)
"Here's what you can do"          (account)            "Now do it — step by step"
```

The capability overview that the tour showed in step 1–6 becomes the task list the
checklist walks through in the same order.

### Dismissal

The checklist disappears automatically when all four required steps are complete. It
does not require a "dismiss" button — it is never shown again once `setup_complete = true`.

If a school admin deliberately wants to skip setup (e.g., exploring before committing),
they can navigate away. The checklist returns on every dashboard visit until setup is
complete. There is no permanent dismiss-without-completing option.

---

## 3. Context Signals

Beyond persona, the delivery layer uses context signals to sharpen the response:

| Signal | Source | Example use |
|---|---|---|
| Current page / route | URL / React context | On `/school/classrooms` → skip "navigate to Classrooms" step |
| Current page state | React Query cache | "You have 2 classrooms" → skip creation if one already fits |
| User's school subscription plan | JWT / API | On Starter plan → note that custom builds require upgrade |
| `first_login` flag | JWT | On first login → prepend "First, set your permanent password" |
| Incomplete setup state | API call | No curriculum assigned → offer that as the next step |

Context signals reduce irrelevant steps and avoid instructions for things the user
has already done. The goal is a response that reads as if a colleague is watching
their screen and advising them in real time.

---

## 4. Output Format

The delivery layer always generates structured output — never a wall of text:

```
┌─────────────────────────────────────────────────────────────────────┐
│  📋  Adding a student to a classroom                                │
│  Role: School Admin · Page: Classrooms                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Open the classroom you want to enrol the student into.          │
│     → Click Manage next to "Grade 8 — Section A"                   │
│                                                                     │
│  2. Scroll to the Students section at the bottom of the page.       │
│                                                                     │
│  3. Enter the student's ID in the "Enrol a student" box.            │
│     → Find student IDs on the Students page (sidebar → Students)   │
│                                                                     │
│  4. Click Enrol.                                                    │
│                                                                     │
│  ✓  The student will appear in the list immediately.               │
│     They can now access all curriculum packages in this classroom.  │
│                                                                     │
│  Related: Removing a student · Assigning a curriculum package       │
└─────────────────────────────────────────────────────────────────────┘
```

Output rules:
- Always numbered steps — never bullet-point prose
- Steps reference actual UI labels (button names, nav items) verbatim
- Each step is one action, not a compound instruction
- A "✓ Result" line confirms what success looks like
- "Related" links surface 2–3 adjacent topics (not a full index)
- Maximum 7 steps — if a task requires more, split into sub-tasks

---

## 5. Content Library Structure

The library is a separate site (or a section of the docs repo). It is authored in
**HTML + SVG**, not markdown, for the reasons described in the SVG discussion.

The library now has a top-level `overview/` section that feeds Layer 0 (the public
tour) and is also available to authenticated users who want a capability reference:

```
docs-site/
  overview/                         ← NEW — feeds Layer 0 public tour
    school-admin.html               — all admin capabilities, one page
    teacher.html                    — all teacher capabilities, one page
    student.html                    — all student capabilities, one page

  help/
    school-admin/
      getting-started.html          — setup checklist walkthrough
      classrooms.html               — classroom lifecycle
      teachers.html                 — provisioning + password reset
      students.html                 — provisioning + classroom assignment
      curriculum.html               — catalog vs custom, pipeline billing
      subscription.html             — plans, upgrades, storage
    teacher/
      classrooms.html
      curriculum.html
      reports.html
      at-risk-students.html
    student/
      getting-started.html
      lessons.html
      quizzes.html
      account.html

  flows/
    school-registration-flow.svg    — end-to-end school setup sequence
    curriculum-lifecycle-flow.svg   — definition → approval → build → assign
    student-enrolment-flow.svg      — provisioning → classroom → content access
    first-login-flow.svg            — default password → forced reset → portal
    billing-flow.svg                — subscription → pipeline charge → build
    tour-admin-flow.svg             ← NEW — admin capability tour sequence (Layer 0)
    tour-teacher-flow.svg           ← NEW — teacher capability tour sequence (Layer 0)
    tour-student-flow.svg           ← NEW — student capability tour sequence (Layer 0)

  design/
    architecture.html               — system design for technical readers
    data-model.html                 — entity relationships
    auth-tracks.html                — three auth tracks (Auth0, local, admin)
```

### What the `overview/` pages contain

Each `overview/{persona}.html` page lists every capability for that persona in the
same order as the public tour (Layer 0). Structure per capability:

```html
<section class="capability" data-tour-step="1">
  <h2>Register your school</h2>
  <p class="outcome">One sign-up gives your whole school access.</p>
  <p class="detail">…</p>
  <figure><img src="../flows/school-registration-flow.svg" …></figure>
  <a href="../help/school-admin/getting-started.html">Full setup guide →</a>
</section>
```

The `data-tour-step` attribute is read by the Layer 0 tour JavaScript to sequence
the screens. The same HTML fragment is also embedded (via `<iframe>` or server-side
render) on each tour screen in the Next.js public pages — no content is authored
twice.

### Why HTML + SVG for the library

| Requirement | Why HTML+SVG |
|---|---|
| Diagrams that explain flows | Inline SVG — click a step to highlight it |
| Role-specific content visible | CSS classes show/hide sections per persona |
| Step references that match the AI output | Authored canonical step text that the AI quotes verbatim |
| Searchable | HTML text is fully indexed; SVG `<title>` / `<desc>` tags too |
| Embeddable in the portal | `<iframe>` or server-side rendered into React pages |
| Printable / PDF export | CSS `@media print` — no separate tooling |

### SVG diagrams: what to build

Each SVG flow diagram is authored once and used in two places:
1. As a static illustration in the library HTML page
2. As a reference the delivery layer can cite ("see the Curriculum Lifecycle diagram")

SVG diagrams for the help system use a constrained visual language:
- Rounded rectangles = user actions
- Diamonds = decision points
- Solid arrows = happy path
- Dashed arrows = error or alternative path
- Role-coloured borders (purple = admin, blue = teacher, green = student)

---

## 6. Technical Architecture

### Delivery layer — how the AI generates guidance

```
User types question
        │
        ▼
Context collector
  • JWT  → persona, school_id, first_login
  • URL  → current page
  • API  → relevant account state (optional, async)
        │
        ▼
Query builder
  Constructs a structured prompt:
  "You are a help assistant for StudyBuddy OnDemand.
   Persona: School Admin. Current page: /school/classrooms.
   Question: {user_question}
   Use only the following reference content to answer: {retrieved_chunks}
   Format the answer as numbered steps. Maximum 7 steps."
        │
        ▼
Retrieval (RAG)
  Vector search over the content library chunks
  Returns: top-3 most relevant procedure sections
        │
        ▼
LLM call (Claude)
  Model: claude-haiku-4-5 (fast, cheap — help responses are short)
  Temperature: 0 (deterministic — same question → same answer)
  Max tokens: 400
        │
        ▼
Response renderer
  Parses numbered list + result line + related links
  Renders as the structured card UI (Section 4 above)
```

### Why RAG over fine-tuning

The content library will evolve as the product evolves. RAG means:
- No retraining when a new feature ships — update the library, re-index
- Answers are grounded in authored content — hallucination risk is low
- The library is the audit trail for every AI answer

### Why Haiku, not Sonnet

Help responses are short, structured, and drawn from retrieved context. Haiku is
fast enough that the response feels instant (< 1s). Sonnet's reasoning capability
is not needed when the retrieval has already done the hard work.

### Embedding and indexing

Content library chunks are embedded at build time:
- Each `<section>` in a library HTML page becomes one chunk
- Each SVG flow diagram step becomes one chunk (extracted from `<desc>` tags)
- Chunks are stored in a vector DB (pgvector extension on the existing PostgreSQL —
  no new infrastructure required for initial implementation)
- Re-indexing triggered by CI when library content changes

---

## 7. Relationship to Existing Codebase

Three new components, none of which change existing code:

```
         existing                         new (this design)
┌────────────────────────┐    ┌──────────────────────────────────────────────┐
│  Public site           │    │  Layer 0 — Discovery tour                    │
│  (/(public)/*)         │◄───│  /(public)/tour/*                            │
│                        │    │  Static HTML+JS, no auth, no API calls       │
└────────────────────────┘    └──────────────────────────────────────────────┘

┌────────────────────────┐    ┌──────────────────────────────────────────────┐
│  School portal         │    │  Layer 1.5 — Setup checklist                 │
│  (/school/dashboard)   │◄───│  <SetupChecklist> banner component           │
│                        │    │  GET /schools/{id}/setup-status              │
│                        │    │  Shown until setup_complete=true             │
└────────────────────────┘    └──────────────────────────────────────────────┘

┌────────────────────────┐    ┌──────────────────────────────────────────────┐
│  School portal         │    │  Layer 2 — Help widget                       │
│  (/school/*)           │◄───│  <HelpWidget> floating button, all pages     │
│                        │    │  POST /help/ask                              │
│  Teacher portal        │    │    { question, page, role }                  │
│  (/teacher/*)          │◄───│  ← { steps, related }                        │
│                        │    │                                              │
│  Student portal        │    │  Content library site                        │
│  (/student/*)          │◄───│  (static, separate deploy)                   │
└────────────────────────┘    └──────────────────────────────────────────────┘
                                              │
                                              ▼
                                   pgvector index (existing DB)
                                   Claude Haiku API
```

**Layer 0** requires no backend changes — it is a set of static Next.js pages under
`/(public)/tour/` that read from the content library. No JWT. No API calls.

**Layer 1.5** requires one new backend endpoint: `GET /schools/{id}/setup-status`
returning `{teacher_count, student_count, classroom_count, curriculum_assigned,
setup_complete}`. The frontend `<SetupChecklist>` component is dropped into the
school portal dashboard layout, conditional on `setup_complete = false`.

**Layer 2** (the help widget) is a React component dropped into the school/teacher/
student portal layouts. It reads the JWT and current route — no extra props required.
The `POST /help/ask` backend endpoint handles retrieval + LLM call + response formatting.

---

## 8. What the Library Enables Beyond In-App Help

The same content library, once built, supports:

| Use | How |
|---|---|
| Static documentation site | Serve the HTML files directly — no AI required |
| Layer 0 public tour | `overview/` pages embedded in `/(public)/tour/*` — no content authored twice |
| Onboarding email sequences | Pull canonical steps from the library into email templates |
| Support ticket deflection | Link to the exact library page from the ticket form |
| Admin escalation context | Attach the relevant flow diagram to a support ticket |
| Localisation | Translate the library HTML — the AI delivery layer inherits it |

---

## 9. Phasing Recommendation

| Phase | Layer | Scope | Dependency |
|---|---|---|---|
| **Lib-A** | 1 | Author content library — School Admin persona (overview + procedures) | None |
| **Tour-A** | 0 | Build `/(public)/tour/school-admin/` — admin capability tour pages | Lib-A overview section complete |
| **Checklist** | 1.5 | `GET /schools/{id}/setup-status` endpoint + `<SetupChecklist>` dashboard component | None — independent of library |
| **Lib-B** | 1 | Extend library to Teacher persona | Lib-A complete |
| **Tour-B** | 0 | Teacher tour pages | Lib-B overview section complete |
| **Lib-C** | 1 | Extend library to Student persona | Lib-B complete |
| **Tour-C** | 0 | Student tour pages | Lib-C overview section complete |
| **Deliver-1** | 2 | `POST /help/ask` endpoint + pgvector index + Haiku call | Lib-A complete |
| **Deliver-2** | 2 | Help widget React component (floating button + response card) | Deliver-1 complete |
| **Deliver-3** | 2 | Context signals — page state, account state | Deliver-2 complete |
| **Deliver-4** | 2 | Analytics — questions asked, unhelpful answers flagged | Deliver-2 complete |

**Recommended build order for a single developer:**
`Lib-A → Checklist → Tour-A → Deliver-1 → Deliver-2 → Lib-B → Tour-B → Deliver-3 → Lib-C → Tour-C → Deliver-4`

Rationale: Checklist has no library dependency and delivers immediate value to new
school admins. Tour-A is a conversion surface — done early so it can be used in
sales/demo contexts. Deliver-1 and Deliver-2 unlock the core in-app help experience.
Remaining personas follow once the pipeline is proven.

---

## 10. Open Questions

**Layer 0 — Discovery**

1. **Tour analytics:** Should we track which capability screens visitors view and
   where they drop off? This data directly informs which features to lead with in
   the tour and on the landing page. A lightweight event (page + step + role, no PII)
   sent to the analytics endpoint is sufficient — no third-party tracking required.

2. **Student tour CTA:** Students cannot self-register — they receive a login from
   their school. The student tour ends with "Ask your teacher for your school login."
   Should there be a parallel path for parents, who may be the actual decision-maker
   for private enrolment scenarios?

**Layer 1.5 — Setup Checklist**

3. **Checklist scope:** The four required steps cover the minimum to get a classroom
   running. Should "build a custom curriculum" be a required step or remain optional?
   Leaving it optional is correct for schools that use platform packages exclusively,
   but schools with a custom curriculum contract may need to be prompted more strongly.

4. **Re-entry after partial completion:** If an admin completes steps 1–2, then stops
   for a week, the checklist must remember their progress accurately on return.
   Since progress is computed from live account state (not stored preferences), this
   works automatically — but it means the checklist can never show "you were here"
   progress markers, only current state.

**Layer 2 — Delivery (existing questions)**

5. **Feedback loop:** Should users be able to rate an answer (👍/👎)? If yes, negative
   ratings should flag the library chunk for review — not retrain the model.

6. **Escalation path:** If the AI cannot find a relevant answer (low retrieval
   confidence score), what happens? Options: show a "Contact support" link; surface
   the most relevant static library page; say "I don't know" explicitly.

7. **Multi-language:** The portal is already multi-language (EN/FR/ES). Does the help
   system need to respond in the user's locale? The library would need translated
   versions of every chunk. The tour (Layer 0) has the same requirement.

8. **Streaming:** Should the response stream token-by-token (faster perceived response)
   or appear all at once (avoids layout jank)? Streaming requires SSE on the backend.

9. **Privacy:** Questions are sent to the Claude API. Does the school's DPA
   acknowledgement cover this, or does it require a separate disclosure? The question
   text should never contain student PII — enforce at the API boundary.

---

## Related Documents

- `docs/DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md` — multi-provider pipeline (the MCP
  admin assistant concept in Section "Where MCP / Agent Tooling Could Fit" is related)
- `docs/REGISTRATION_DESIGN_ANALYSIS.md` — use-case flows that will seed the library
- `ARCHITECTURE.md` (studybuddy-docs repo) — system design reference for the library's
  design documentation section
- `CLAUDE.md` → Typography & Accessibility Standards — library HTML must follow the
  3-font system and support OpenDyslexic mode

---

*Document created: 2026-04-12. Layer 0 + Layer 1.5 added: 2026-04-12.*  
*Status: Design exploration — not scheduled. School portal feature set has now
stabilised (Phase E complete). Ready to begin with Lib-A + Checklist in parallel.*
