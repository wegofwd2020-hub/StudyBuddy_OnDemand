# Epic 9 — Accessibility & Personalization

**Status:** 💭 Your call

---

## What it is

Unifies all user-facing preference work into one epic: multi-language UX
(school default + user override), theme picker, priority accessibility
features (reduced motion, audio captions, colour-blind safe palette, text
size), and a single preferences mechanism that backs them all. Finishes the
dyslexia polish shipped in Rule #18.

Full specification lives in
[studybuddy-docs/UX_REQUIREMENTS.md §2.2, §2.3, §3, §4, §5](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UX_REQUIREMENTS.md).

---

## Current state

**Shipped:**
- Font stack (Inter / Merriweather / JetBrains Mono) via `next/font` + CSS variables
- Dyslexia toggle: `useDyslexia()` hook, Alt+D shortcut, `sb_dyslexic` cookie, SSR-safe via `data-dyslexic`
- i18n framework (`next-intl`) with `en`/`fr`/`es` for web + mobile
- `students.locale` column, JWT-authoritative locale
- Skip-to-content link, focus rings, forced-colors support, min target size (WCAG 2.2 SC 2.5.8)
- Light + dark CSS-variable token sets in OKLch

**Not started:**
- `teachers.locale` column — teachers have no locale preference today
- `schools.default_locale` column — no school-level language default
- Theme picker UI (tokens exist, switcher does not)
- Reduced motion at app level (Sonner honors it; app animations not audited)
- Audio lesson transcript/captions toggle
- Colour-blind safe Reports palette (pass/fail red/green has no secondary cue)
- Text-size slider (100/125/150%)
- Dyslexia toggle on public / onboarding pages (currently only in authenticated `PortalHeader`)
- Unified preferences mechanism (one cookie family + one server-side backup)

---

## Why it matters

- **SaaS scope.** Any organisation in any country may subscribe. A French teacher
  at a US school must be able to read the UI in French while the school's default
  is English. Current model can't express that.
- **Compliance.** WCAG 2.1 AA is the stated baseline (CLAUDE.md). We are close
  but the items above are real gaps against it.
- **Retention.** Personalisation surfaces (themes, text size, reduced motion,
  language override) are low-cost wins that visibly respect the user and
  reduce churn for users with specific needs.
- **Prevents drift.** A unified preferences mechanism stops every new feature
  from inventing its own cookie + fallback pattern.

---

## Rough scope

### Wave 1 — Data model & foundation

| Phase | What gets built | Size |
|---|---|---|
| I-1 | Migration `0045_locale_preferences` — `schools.default_locale TEXT NOT NULL DEFAULT 'en'`; `teachers.locale TEXT NOT NULL DEFAULT 'en'` | S |
| I-2 | Migration `0046_user_preferences` — `users.preferences JSONB DEFAULT '{}'` (or split per-role) for theme, text_size, reduced_motion, dyslexia backup | S |
| I-3 | `web/lib/preferences.ts` — single hook + one cookie family (`sb_dyslexic`, `sb_theme`, `sb_text_size`, `sb_reduced_motion`, `sb_locale`); SSR-safe reads in root layout; sets `data-*` attributes on `<html>` | M |

### Wave 2 — Multi-language UX

| Phase | What gets built | Size |
|---|---|---|
| I-4 | Fallback chain: `user.locale → school.default_locale → 'en'`; inject `school_locale` into JWT so client can fall back without round-trip | S |
| I-5 | School Settings → **Preferences** card with `default_locale` dropdown; school admin role only | S |
| I-6 | User account settings (student + teacher) — *Language* dropdown with "Use school default" option | S |
| I-7 | Quick language switcher in `PortalHeader` (session-only override, does not persist to DB) | S |
| I-8 | Soft banner on content playback when UI locale has no matching `content_subject_versions` row: "Content not yet available in {lang} — showing English" | S |

### Wave 3 — Theme picker

| Phase | What gets built | Size |
|---|---|---|
| I-9 | Add 5 named theme selector scopes (`[data-theme="slate"]`, `rose`, `green`, `blue`, `violet`) to `globals.css`, each overriding the same OKLch token set; dark variant for each | M |
| I-10 | Theme picker in `/account/settings` (users) and `/school/settings` (school default for unauthenticated / landing); cookie `sb_theme` + localStorage; SSR-safe via `data-theme` on `<html>` | S |

### Wave 4 — Priority accessibility

| Phase | What gets built | Size |
|---|---|---|
| I-11 | Reduced-motion support: respect `prefers-reduced-motion` + manual toggle; gate non-essential animations | S |
| I-12 | Audio lesson transcript toggle: "Show transcript" next to audio player uses existing lesson JSON text | S |
| I-13 | Colour-blind safe Reports palette: add shape/pattern secondary cue to pass/fail and health tiers; WCAG AAA contrast | M |
| I-14 | Text-size slider (100/125/150%) applied via CSS variable on `<html>`; persisted alongside theme | S |

### Wave 5 — Dyslexia polish

| Phase | What gets built | Size |
|---|---|---|
| I-15 | Expose dyslexia toggle on public pages (landing, demo login, school-register) and school onboarding completion screen | S |
| I-16 | Add dyslexia + text-size + theme + language to a consolidated **Accessibility & Display** card on `/account/settings` | S |

### Deferred to later epic

- Keyboard nav audit across all flows (Epic scope; belongs in a dedicated a11y sweep)
- Full screen-reader pass with ARIA live regions on quiz feedback (same)
- ADHD / focus mode (significant UX design work)
- Per-school branded themes via tweakcn-style editor (premium feature)

---

## Open questions

1. **Adding new UI languages.** Which languages unlock real customer
   interest — German, Portuguese, Hindi, Arabic, Mandarin? RTL support is
   a non-trivial CSS addition (Arabic, Hebrew) — separate sub-phase if yes.
2. **Content vs UI language.** Do we ever commit to building content in a
   new language at school request, or permanently restrict content to the
   three already built? Budget implication is significant.
3. **Preference surface area.** Should school admins be able to *restrict*
   theme / language choices (e.g. "this school can only use the Slate theme")?
   Corporate branding scenarios might want this; adds complexity.
4. **Text-size scope.** Does the slider affect only body text, or headings
   too? Affecting headings preserves hierarchy; leaving them fixed looks
   odd at 150%.
5. **Theme picker visibility.** Available to every user, or only when the
   school allows it?
6. **Reduced motion granularity.** On/off, or tiered (essential only / no
   animation / full)?

---

## Dependencies

- No hard blockers. Wave 1 (data model) unblocks all later waves.
- Wave 3 (theme picker) can ship independently of Wave 2 (i18n).
- Wave 4 items (a11y priorities) can ship independently of each other.

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
