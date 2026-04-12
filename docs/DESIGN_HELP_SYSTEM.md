# StudyBuddy OnDemand — Contextual Help System Design

**Status:** Design exploration — not yet scheduled  
**Date:** 2026-04-12  
**Scope:** In-app dynamic help delivery + supporting content library

---

## 1. The Core Idea

The help system is a **two-layer architecture**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  LAYER 2 — DELIVERY  (dynamic, AI-generated)                        │
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
│  • Use-case flows (SVG)       — what the system can do              │
│  • Design documentation (HTML)— how the system works                │
│  • Step-by-step procedures    — canonical task sequences            │
│  • Persona glossaries         — role-specific terminology           │
│  • UI screenshots / annotated diagrams                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

The library exists independently of the delivery layer. It is:
- Useful on its own as a static documentation site
- The ground truth that the AI delivery layer draws from
- Versioned alongside the application code

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
**HTML + SVG**, not markdown, for the reasons described in the SVG discussion:

```
docs-site/
  help/
    school-admin/
      getting-started.html          — school setup checklist
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
  design/
    architecture.html               — system design for technical readers
    data-model.html                 — entity relationships
    auth-tracks.html                — three auth tracks (Auth0, local, admin)
```

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

This is a new feature layer — nothing existing changes:

```
                    existing                      new
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  School portal               │   │  Help widget                 │
│  (/school/*)                 │   │  (floating button, all pages) │
│                              │   │                              │
│  Teacher portal              │   │  POST /help/ask              │
│  (/teacher/*)                │◄──│    { question, page, role }  │
│                              │   │  ← { steps, related }        │
│  Student portal              │   │                              │
│  (/student/*)                │   │  Content library site        │
│                              │   │  (static, separate deploy)   │
└──────────────────────────────┘   └──────────────────────────────┘
                                              │
                                              ▼
                                   pgvector index (existing DB)
                                   Claude Haiku API
```

The help widget is a React component dropped into the school/teacher/student portal
layouts. It reads the JWT and current route — no extra props required. The `POST
/help/ask` backend endpoint handles retrieval + LLM call + response formatting.

---

## 8. What the Library Enables Beyond In-App Help

The same content library, once built, supports:

| Use | How |
|---|---|
| Static documentation site | Serve the HTML files directly — no AI required |
| Onboarding email sequences | Pull canonical steps from the library into email templates |
| Support ticket deflection | Link to the exact library page from the ticket form |
| Admin escalation context | Attach the relevant flow diagram to a support ticket |
| Localisation | Translate the library HTML — the AI delivery layer inherits it |

---

## 9. Phasing Recommendation

| Phase | Scope | Dependency |
|---|---|---|
| **Lib-A** | Author content library for School Admin persona (highest support volume) | None — can start immediately |
| **Lib-B** | Extend to Teacher persona | Lib-A complete |
| **Lib-C** | Extend to Student persona | Lib-B complete |
| **Deliver-1** | Build `POST /help/ask` endpoint + pgvector index + Haiku call | Lib-A complete |
| **Deliver-2** | Build help widget React component (floating button + response card) | Deliver-1 complete |
| **Deliver-3** | Add context signals (page state, account state) | Deliver-2 complete |
| **Deliver-4** | Analytics — which questions are asked, which answers are unhelpful | Deliver-2 complete |

Lib-A and Deliver-1 can be built in parallel by different people once the chunk
format and API contract are agreed.

---

## 10. Open Questions

1. **Feedback loop:** Should users be able to rate an answer (👍/👎)? If yes, negative
   ratings should flag the library chunk for review — not retrain the model.

2. **Escalation path:** If the AI cannot find a relevant answer (low retrieval
   confidence score), what happens? Options: show a "Contact support" link; surface
   the most relevant static library page; say "I don't know" explicitly.

3. **Multi-language:** The portal is already multi-language (EN/FR/ES). Does the help
   system need to respond in the user's locale? The library would need translated
   versions of every chunk.

4. **Streaming:** Should the response stream token-by-token (faster perceived response)
   or appear all at once (avoids layout jank)? Streaming requires SSE on the backend.

5. **Privacy:** Questions are sent to the Claude API. Does the school's DPA
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

*Document created: 2026-04-12*  
*Status: Design exploration — not scheduled. Begin with Lib-A when the school portal
feature set stabilises after Phase E (Pipeline Billing).*
