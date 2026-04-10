/**
 * Test data for section 1.1 — Landing Page (`/`)
 *
 * All string values are sourced from i18n/en.json so tests stay in sync
 * with the real UI strings. Update here if the en.json values change.
 */

// ---------------------------------------------------------------------------
// PUB-01 — Banner
// ---------------------------------------------------------------------------

export const BANNER = {
  alt: "StudyBuddy — learning for every family",
  /** Tailwind class sets height to 240 px */
  expectedHeightPx: 240,
  /** next/Image wrapping div has no fixed role; locate by img alt */
} as const;

// ---------------------------------------------------------------------------
// PUB-02 — Hero heading
// ---------------------------------------------------------------------------

export const HERO = {
  // Matches en.json "hero_heading". Update here if the i18n value changes.
  heading: "Study Buddy",
  subheading:
    "Instant lessons, quizzes, and audio where available. Just learning.",
  ctaPrimary: { text: "Start free trial", href: "/signup" },
  ctaSecondary: { text: "See how it works", href: "/#features" },
} as const;

// ---------------------------------------------------------------------------
// PUB-05 — Feature cards (6 cards, in render order)
// ---------------------------------------------------------------------------

export const FEATURES: ReadonlyArray<{ title: string; description: string }> = [
  {
    title: "Instant content",
    description:
      "Pre-generated lessons and quizzes load in milliseconds — no AI wait time.",
  },
  {
    title: "Audio lessons",
    description:
      "Every lesson has a narrated audio version. Learn by reading or listening.",
  },
  {
    title: "English, French & Spanish",
    description: "Full content in three languages. Switch any time in settings.",
  },
  {
    title: "Works offline",
    description:
      "Downloaded content is available without internet. Progress syncs automatically.",
  },
  {
    title: "Lab experiments",
    description:
      "Step-by-step experiment guides with materials lists for hands-on learning.",
  },
  {
    title: "Built for schools",
    description:
      "Teachers get real-time progress reports, alerts, and custom curriculum tools.",
  },
];

// ---------------------------------------------------------------------------
// PUB-06 — Testimonials (3 hardcoded items in page.tsx)
// ---------------------------------------------------------------------------

export const TESTIMONIALS: ReadonlyArray<{ quote: string; author: string }> = [
  {
    quote: "My daughter went from a C to a B+ in algebra in one semester.",
    author: "Maria T., Parent",
  },
  {
    quote:
      "The audio lessons are a game-changer for my students with reading difficulties.",
    author: "James K., Grade 8 Teacher",
  },
  {
    quote: "Finally an app that works when I'm on the bus with no signal.",
    author: "Priya, Grade 10 Student",
  },
];

// ---------------------------------------------------------------------------
// PUB-07 — Footer CTA
// ---------------------------------------------------------------------------

export const FOOTER_CTA = {
  heading: "Ready to get started?",
  buttonText: "Start your free trial",
  href: "/signup",
} as const;

// ---------------------------------------------------------------------------
// PUB-08 / PUB-09 — Desktop nav links
// ---------------------------------------------------------------------------

export const NAV_LINKS: ReadonlyArray<{ text: string; href: string }> = [
  { text: "Pricing", href: "/pricing" },
  { text: "Sign in", href: "/login" },
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
