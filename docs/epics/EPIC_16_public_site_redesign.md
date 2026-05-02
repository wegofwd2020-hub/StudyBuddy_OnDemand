# Epic 16 — Public Site Redesign: School-First Marketing Pages

**Status:** 🔜 Ready to build — start 2026-05-03

---

## Context

The platform has been repositioned from a student-facing tutoring product to a
**school-as-primary-entity** B2B education tool. The pricing model is now 3-tier
(Platform Starter / School Pro / Enterprise). The school portal, auth, theming,
and curriculum engine all reflect this. The **public marketing site does not.**

Right now a school admin landing on the homepage sees a student-facing layout,
a "Student sign-in" nav, and no clear school journey. This is the GTM gap to close.

---

## What We Are Fixing

| Surface | Current state | Target state |
|---|---|---|
| Landing page (`/`) | Student-framed hero, STEM focus | School-first hero — leads with the school admin value prop |
| PublicNav | "Sign in" → student login, no school CTA | School-first nav — "Register your school" as primary CTA |
| "For Schools" page | Does not exist | Dedicated pitch page for school admins |
| About page | Generic, mission-only | Add product architecture + trust signals (FERPA, COPPA, WCAG) |
| Pricing page | ✅ Updated this session (3-tier school model) | No further changes needed |

---

## Positioning to Carry Through

Every page should reflect both framings consistently:

**Consumer (school admins, teachers, parents):**
> *"Your bridge from lessons to a world that's always current."*
> An AI study buddy that connects your lessons to the world — and keeps learning alongside you.

**What to lead with on every school-facing surface:**
1. School admin registers once → whole school is live in minutes
2. Pre-built curricula for Grades 5–12, ready on day one (no pipeline run needed)
3. Teachers get reports; students get lessons, quizzes, audio in EN/FR/ES
4. School can customize and build their own curricula when ready

---

## Tickets

### S-1 — PublicNav: school-first navigation

**Priority:** High — affects every page  
**Estimated effort:** Small (1–2 hours)

**Changes:**
- Primary CTA button: **"Register your school"** → `/schools/register`
- Secondary link: **"School sign-in"** → `/school/login`
- Remove or demote the student sign-in link (move to footer or a secondary dropdown)
- Add **"For Schools"** link in the nav (points to new S-3 page)
- Keep: Pricing, About, Contact

**Acceptance:**
- A school admin landing on any public page immediately sees a school-oriented CTA
- No broken links

---

### S-2 — Landing page: school-first hero + features rewrite

**Priority:** High — primary GTM surface  
**Estimated effort:** Medium (3–4 hours)

**Hero section — replace current with:**

```
Headline:   Your bridge from lessons to a world that's always current.
Sub-head:   Give every student at your school instant AI-powered lessons,
            quizzes, and audio — aligned to your curriculum, in English,
            French, and Spanish.
Primary CTA:  [Register your school — it's free]  → /schools/register
Secondary CTA: [See how it works]  → /tour/school-admin
Tertiary link: Already a teacher?  Sign in →  /school/login
```

**Retain from current page:**
- Multilingual watermark background (great, keep it)
- Home banner image (keep)
- Tour gateway section (keep, links are correct)
- Social proof section (keep)

**Rewrite features section — school admin journey, not student features:**

| Feature card | Headline | Body |
|---|---|---|
| 1 | Live in minutes | Register once. Every teacher and student at your school gets instant access — no per-account setup. |
| 2 | Curricula ready on day one | Pre-built Grades 5–12 content loads immediately. No waiting for AI to generate anything. |
| 3 | Three languages, one platform | Every lesson, quiz, and audio narration in English, French, and Spanish. Students switch any time. |
| 4 | Teachers stay informed | Real-time progress reports, at-risk alerts, and weekly digests — all without leaving the portal. |
| 5 | Your curriculum, your way | Upload your own curriculum definition. We build the content. Your school owns it. |
| 6 | Built for compliance | FERPA, COPPA, and WCAG 2.1 AA — not afterthoughts. Baked into the data model from day one. |

**CTA section at bottom:**
```
Heading:   Ready to bring StudyBuddy to your school?
Sub:       Free to start. No credit card. Full access to Grades 5–12 content on day one.
CTA:       [Register your school free]
```

**Acceptance:**
- Hero reads school-first on first load (no visible student framing above the fold)
- All 6 feature cards present
- CTAs link to `/schools/register` and `/tour/school-admin`

---

### S-3 — "For Schools" dedicated page (`/for-schools`)

**Priority:** High — linked from nav, targeted in ad/email campaigns  
**Estimated effort:** Medium-large (4–5 hours)

**Page structure:**

#### Section 1 — Hero
```
Headline:    StudyBuddy for Schools
Sub:         Pre-built curricula. Teacher tools. Three languages.
             Everything your school needs — free to start.
CTA:         [Register your school]   [Book a demo]
```

#### Section 2 — How it works (3-step)
```
Step 1: Register your school (2 minutes)
        You become the school admin. Add your teachers and students — or let them self-enrol.

Step 2: Content is ready on day one
        Grades 5–12 platform curricula are pre-built. No pipeline run, no waiting.
        Teachers can browse, assign, and customise.

Step 3: Students learn. Teachers track.
        Every student gets lessons, quizzes, audio, and experiments.
        Teachers see progress in real time.
```

#### Section 3 — Feature deep-dive (grid)
- Curriculum management (platform + custom builds)
- Classroom management
- Teacher analytics & at-risk alerts
- School branding & theming
- Multi-language content (EN / FR / ES)
- Backup & restore
- FERPA / COPPA compliance
- Accessibility (WCAG 2.1 AA)

#### Section 4 — Pricing summary (3 cards, links to /pricing)
Reuse the same 3-tier structure from the pricing page.
Keep it brief — headline + 3 bullet points per tier + CTA.

#### Section 5 — FAQ (school-admin focused, 5 questions)
1. How long does setup take?
2. Do students need their own accounts?
3. Can we use our own curriculum?
4. Is content available offline?
5. How does pricing work for a school of 200 students?

#### Section 6 — CTA footer
```
Ready to get started?
Register your school free — no credit card, no commitment.
[Register now]   [Contact us]
```

**Acceptance:**
- Page exists at `/for-schools`
- Nav link works
- All 6 sections present
- Pricing cards link to `/pricing`

---

### S-4 — About page: add trust signals

**Priority:** Medium  
**Estimated effort:** Small (1–2 hours)

The current About page is mission-focused but thin on trust signals that matter
to a school purchasing decision.

**Add a new "Built for schools" section with:**
- FERPA compliance note
- COPPA under-13 consent flow
- WCAG 2.1 AA accessibility target
- Data minimisation policy (name + email + grade only — no tracking, no fingerprinting)
- Content moderation (AlexJS pipeline-level check on all AI-generated content)

**Keep everything else as-is.**

---

### S-5 — Public layout: responsive + accessibility pass

**Priority:** Medium  
**Estimated effort:** Small (1–2 hours)

Quick sweep of all public pages for:
- Mobile nav hamburger (confirm it works on small screens)
- `lang` attribute on `<html>` (current axe finding from CLAUDE.md #189)
- `<title>` present on all public pages (second axe finding)
- Colour contrast on any new S-2/S-3 copy against their backgrounds

---

## Build Order

```
Day 1 morning:
  S-1  PublicNav (small, unblocks everything — nav appears on all pages)
  S-2  Landing page hero + features rewrite

Day 1 afternoon:
  S-3  "For Schools" page (largest ticket)

Day 2:
  S-4  About page trust signals
  S-5  Responsive + accessibility pass
  Commit + push
```

---

## Definition of Done

- [ ] All 5 tickets complete
- [ ] `npm run typecheck` passes (zero errors)
- [ ] No `console.error` in browser on any updated page
- [ ] PublicNav "Register your school" CTA links correctly on all screen sizes
- [ ] `/for-schools` returns 200 and is linked from nav
- [ ] `git commit` + push to `main`
