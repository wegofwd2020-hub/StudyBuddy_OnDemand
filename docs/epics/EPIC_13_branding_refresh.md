# Epic 13 — Branding Refresh: STEM → Education Enhancement

**Status:** 🚧 Scope locked 2026-04-21; execution tickets pending

---

## What it is

Rebrand StudyBuddy OnDemand from a **"STEM tutoring platform"** to an
**AI-powered education enhancement tool** — the "information bridge" between a
student's classroom lessons and the current world, scoped to their grade,
subject, and language.

Two framings that will live side by side:

| Framing | Audience | Where it surfaces |
|---|---|---|
| **Information bridge** (consumer) | Parents, students, teachers, school admins | Landing page, emails, help widget, marketing |
| **Scoped retrieval over the world of knowledge** (engineering) | Developers, architects, pitch decks | CLAUDE.md, ARCHITECTURE.md, technical pitch material |

Both are correct; they serve different audiences. See
[BRANDING_TAGLINE_OPTIONS.md](../BRANDING_TAGLINE_OPTIONS.md) for the full
decision log.

---

## Decisions (locked 2026-04-21)

### Canonical copy

- **Tagline (H1):** *"Your bridge from lessons to a world that's always current."*
- **Sub-headline:** *"An AI study buddy that connects your lessons to the world — and keeps learning alongside you."*

### Why "current" and not "today's"

"Today's" anchors to a specific date (a snapshot). **"Current" anchors to
"whenever the student is using the product"** (an evergreen property). The
tagline has to cover three product phases:

1. **Now** — pre-generated content per curriculum
2. **Soon** — teachers generate more content as a course progresses
3. **Roadmap** — AI Agent where students query and learn more on demand

"Today's world" breaks the moment Phase 2/3 ships. "Current world" is the
agent's actual promise.

### Engineering mental model — "scoped retrieval"

> StudyBuddy is a sophisticated search engine where every query is scoped by
> (topic × grade × language × curriculum context × format × real-world framing)
> before it goes out to the LLM / world of knowledge.

| Scope dimension | What it enforces |
|---|---|
| Topic / subject / unit | Curriculum alignment |
| Grade | Reading level, conceptual depth, age-appropriateness |
| Language | en / fr / es / vernacular |
| Curriculum context | What the student has already covered |
| Format | Lesson / quiz / tutorial / experiment |
| Real-world framing | The bridge — connect to something current the student recognises |

This framing explains structurally why the "always current" claim holds:
libraries curate by *selection* (static); search engines curate by *query*
(dynamic). StudyBuddy is the second.

---

## Scope — what's in and what's out

**In scope**
- Copy changes on user-facing surfaces (landing, emails, help assistant,
  school portal, i18n for en/fr/es).
- CLAUDE.md positioning section for future agent sessions.
- README.md top line.
- Site metadata (title, description).

**Out of scope**
- Stream codes in the database (`stem`, `science`, `commerce`, `humanities`,
  `english`) — these are curriculum categories, not branding.
- Data files (`data/grade*_stem.json`, `mobile/data/grade*_stem.json`,
  `cbse_grade*_stem.json`) — curriculum fixtures.
- Migrations 0044 / 0045 (streams registry).
- Logo / visual identity / font choices.
- Icon set.
- Repository name (`StudyBuddy_OnDemand` — already brand-neutral).
- New marketing pages beyond what already exists.

---

## Tickets

### T-BR-1 — CLAUDE.md: description + positioning section

**File:** `CLAUDE.md`

**Changes:**
1. Line 3 — replace "Backend-powered STEM tutoring platform for Grades 5–12.
   Students get instant pre-generated AI content…" with the new description.
2. Insert a new **Positioning** section (near the top, before "Project Status")
   covering:
   - **Consumer framing:** the information-bridge metaphor + canonical tagline.
   - **Engineering mental model:** scoped retrieval over the world of knowledge,
     with the six scope dimensions table.
   - **Audience translation matrix:** when to use which framing.
   - **Load-bearing word:** why "current" and not "today's" (the three-phase
     roadmap reasoning).

**Acceptance:**
- No occurrence of "STEM tutoring platform" in CLAUDE.md.
- Any future agent reading the top 200 lines of CLAUDE.md understands both
  the consumer and engineering framings well enough to avoid describing the
  product as "a content library" or "a tutoring service."

**Severity:** MEDIUM (developer-facing, but load-bearing for every future agent session).

---

### T-BR-2 — Non-English locales: FR + ES hero, features, CTA, tagline

**Files:** `web/i18n/fr.json`, `web/i18n/es.json`

**Changes:** Both locales currently contain "Tutoría STEM" / "Tutorat STIM"
branding that was missed when `en.json` was rebranded. Update:

| Locale | Key | Lines |
|---|---|---|
| `fr.json` | `landing.hero_heading`, `landing.hero_subheading`, `landing.features_heading`, `landing.cta_subheading`, `landing.cta_btn`, `tagline` | 29, 30, 33, 48, 49, 197 |
| `es.json` | Same keys | 29, 30, 33, 48, 197 |

Target — mirror `en.json`'s framing (see `en.json` line 29–50, 291). **Full
side-by-side translation table (all keys, both locales) lives in
[../BRANDING_I18N_DRAFT.md](../BRANDING_I18N_DRAFT.md)** — including the
structural note that `fr.json` / `es.json` are currently missing the
`hero_tagline` key that `en.json` has.

Canonical tagline translations:
- FR: *"Votre pont entre vos leçons et un monde toujours actuel."*
- ES: *"Tu puente entre las lecciones y un mundo siempre actual."*

**Acceptance:**
- Zero occurrences of "STEM", "STIM", "tutorat", or "tutoría" in the landing,
  features, cta, or tagline keys of FR / ES.
- Landing page renders correctly in all three locales (Playwright persona spec
  passes).

**Severity:** HIGH (user-facing in 2 of 3 locales).

---

### T-BR-3 — Backend student-facing AI + transactional email copy

**Files:**
- `backend/src/help/service.py` line 95 — help-assistant system prompt.
- `backend/src/email/service.py` lines 89, 119 — welcome / credentials email.

**Changes:**
- Help system prompt currently reads *"You are a help assistant for StudyBuddy
  OnDemand, a K-12 STEM tutoring platform."* Replace with a description that
  uses the information-bridge framing and drops "STEM tutoring platform."
- Welcome email currently reads *"Grade 8 STEM content is pre-loaded and ready
  to explore."* (appears twice). Replace with grade-appropriate copy that
  doesn't narrow to STEM.

**Acceptance:**
- Help-widget smoke test: ask "what is StudyBuddy?" — response does not describe
  the product as STEM-only or as a tutoring service.
- Provision one test student via school-admin flow; received credentials email
  does not mention "STEM."

**Severity:** HIGH (every help-widget response + every provisioned student's first email).

---

### T-BR-4 — School portal UI copy

**Files:**
- `web/lib/content/help-mindmaps.ts` lines 301, 319
- `web/app/(school)/school/catalog/page.tsx` line 151
- `web/app/(school)/school/curriculum/definitions/new/page.tsx` line 55 (low-priority placeholder)

**Changes:**
- `help-mindmaps.ts:301` — "Complete STEM learning experience with your school or subscription" → drop "STEM".
- `help-mindmaps.ts:319` — "All STEM subjects" → "All supported subjects" (or similar).
- `catalog/page.tsx:151` — "Each package covers a full grade's STEM content across multiple subjects and units." → drop "STEM".
- `definitions/new/page.tsx:55` — placeholder *"Grade 8 STEM — Semester 1"* → *"Grade 8 — Semester 1"* (optional; cosmetic).

**Acceptance:**
- No STEM references render in `/school/catalog` or the help mind-maps for
  school-admin personas.
- Existing Playwright school-admin persona spec continues to pass.

**Severity:** HIGH (user-facing for school admins and teachers).

---

### T-BR-5 — English canonical surfaces (README, metadata, en.json)

**Files:**
- `README.md` line 3
- `web/app/layout.tsx` lines 33–37 (site metadata `title` + `description`)
- `web/i18n/en.json` keys `landing.hero_heading`, `landing.hero_tagline`,
  `landing.hero_subheading`, `tagline` (lines 29–31, 291)

**Changes:** Apply the canonical tagline + sub-headline consistently across all
three surfaces so hero, SEO metadata, and README all convey the same positioning.
The canonical pair:

- **H1:** *"Your bridge from lessons to a world that's always current."*
- **Sub:** *"An AI study buddy that connects your lessons to the world — and keeps learning alongside you."*

Note: `README.md` line 3 already reads *"Backend-powered education enhancement
platform for students"* — acceptable, but could be sharpened with the bridge
metaphor for consistency.

**Acceptance:**
- `/` landing hero, browser tab title, OG preview, and README all reflect the
  same tagline + positioning.
- Help-widget self-description (T-BR-3) aligns with this tagline.

**Severity:** HIGH (primary consumer surface).

---

## Rollout order

1. **T-BR-5** first (English surfaces are the canonical reference for translations).
2. **T-BR-2** next (translate FR/ES against the locked English copy).
3. **T-BR-3** and **T-BR-4** in parallel (independent surfaces).
4. **T-BR-1** last (CLAUDE.md is for future agent sessions — no user impact if
   it lags the user-facing changes by a day).

Suggested single PR, since the changes are tightly coupled and small. If a PR
split is preferred: one for English surfaces (T-BR-5), one for translations +
UI (T-BR-2/3/4), one for CLAUDE.md (T-BR-1).

---

## Open questions

1. **FR/ES translation quality:** Do we want a native speaker to review the
   translated tagline before commit, or is machine-translation-quality OK for
   now with a follow-up review later?
2. **README line 3 — change or leave?** It already reads "education enhancement
   platform" and is acceptable. Worth a sharpening pass (bridge metaphor), or
   leave for now?
3. **Help-widget system prompt tone:** Should the help assistant introduce
   itself using the tagline (*"I'm the AI study buddy that bridges your lessons
   to the current world"*), or keep the help prompt purely functional and let
   the tagline live in marketing surfaces only?
4. **Do we file GitHub issues?** The epic markdown is the canonical spec; each
   ticket could also be filed as a GitHub issue for tracking. Recommend: yes
   for T-BR-2/3/4/5 (execution work); no separate issue for T-BR-1 (CLAUDE.md
   updates tend to ride along with whichever PR touches code).

---

## References

- [BRANDING_TAGLINE_OPTIONS.md](../BRANDING_TAGLINE_OPTIONS.md) — full decision log, all 20+ tagline options, rejected directions.
- Memory `project_branding_current_word.md` — why "current" is load-bearing.
- Memory `project_scoped_retrieval_model.md` — the six-dimension scope framework.
