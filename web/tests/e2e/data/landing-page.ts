/**
 * Test data for section 1.1 — Landing Page (`/`)
 *
 * Refreshed for the Epic 16 public-site redesign (school-first hero, 6 feature
 * cards, Tour Gateway section, school-register CTAs). Values mirror the strings
 * hard-coded in app/(public)/page.tsx — update both together.
 */

// ---------------------------------------------------------------------------
// PUB-01 — Banner
// ---------------------------------------------------------------------------

export const BANNER = {
  alt: "StudyBuddy — learning for every school",
  /** Tailwind class sets height to 240 px */
  expectedHeightPx: 240,
  /** next/Image wrapping div has no fixed role; locate by img alt */
} as const;

// ---------------------------------------------------------------------------
// PUB-02 — Hero heading
// ---------------------------------------------------------------------------

export const HERO = {
  heading: "Lessons, always current.",
  subheading:
    "AI-powered lessons, quizzes, and tutorials — your bridge from classroom to a world that won't sit still.",
  // Primary CTA is now "Register your school"; the "Already a teacher? Sign in"
  // text link sits below it. PUB-03/04 remain fixme pending a rewrite.
  ctaPrimary: { text: "Register your school — it's free", href: "/school/register" },
  ctaSecondary: { text: "Already a teacher? Sign in", href: "/signin" },
} as const;

// ---------------------------------------------------------------------------
// PUB-05 — Feature cards (6 cards, in render order)
// ---------------------------------------------------------------------------

export const FEATURES: ReadonlyArray<{ title: string; description: string }> = [
  {
    title: "Live in minutes",
    description:
      "Register once. Every teacher and student at your school gets instant access — no per-account setup.",
  },
  {
    title: "Curricula ready on day one",
    description:
      "Pre-built Grades 5–12 content loads immediately. No waiting for AI to generate anything.",
  },
  {
    title: "Three languages, one platform",
    description:
      "Every lesson, quiz, and audio narration in English, French, and Spanish. Students switch any time.",
  },
  {
    title: "Teachers stay informed",
    description:
      "Real-time progress reports, at-risk alerts, and weekly digests — all without leaving the portal.",
  },
  {
    title: "Your curriculum, your way",
    description:
      "Upload your own curriculum definition. We build the content. Your school owns it.",
  },
  {
    title: "Built for compliance",
    description:
      "FERPA, COPPA, and WCAG 2.1 AA — not afterthoughts. Baked into the data model from day one.",
  },
];

// ---------------------------------------------------------------------------
// PUB-06 — Tour Gateway section (replaced the old testimonials block in the
// Epic 16 redesign — the pre-register "see it first" confidence section).
// ---------------------------------------------------------------------------

export const TOUR_GATEWAY = {
  eyebrow: "No account needed",
  heading: "See exactly what you can do",
  ctaText: "Explore the platform",
  ctaHref: "/tour",
} as const;

// ---------------------------------------------------------------------------
// PUB-07 — Footer CTA
// ---------------------------------------------------------------------------

export const FOOTER_CTA = {
  heading: "Ready to bring StudyBuddy to your school?",
  buttonText: "Register your school free",
  href: "/school/register",
} as const;

// ---------------------------------------------------------------------------
// PUB-08 / PUB-09 — Desktop nav links
// ---------------------------------------------------------------------------

export const NAV_LINKS: ReadonlyArray<{ text: string; href: string }> = [
  { text: "Pricing", href: "/pricing" },
  { text: "Sign in", href: "/signin" },
];

// ---------------------------------------------------------------------------
// PUB-10 — Mobile viewport
// ---------------------------------------------------------------------------

export const MOBILE_VIEWPORT = {
  /** Below Tailwind's `md` breakpoint (768 px) — hamburger becomes visible */
  width: 375,
  height: 667,
  /** aria-label on the hamburger <button> in PublicNav */
  hamburgerLabel: "Toggle menu",
} as const;
