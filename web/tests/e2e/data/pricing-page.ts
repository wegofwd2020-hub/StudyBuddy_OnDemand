/**
 * Test data for section 1.2 — Pricing Page (`/pricing`)
 * Covers TC-IDs: PUB-11 through PUB-16
 *
 * Refreshed for the Epic 16 school-first pricing redesign: three school plans
 * (Platform Starter / School Pro / School Enterprise). Plan names render in a
 * styled <div>, not a heading. Values mirror app/(public)/pricing/page.tsx.
 */

// ---------------------------------------------------------------------------
// PUB-11 — Plan cards (name + price display)
// ---------------------------------------------------------------------------

export const PLAN_PRICES: ReadonlyArray<{ plan: string; price: string }> = [
  { plan: "Platform Starter", price: "$0" },
  { plan: "School Pro", price: "~$5" },
  { plan: "School Enterprise", price: "Custom" },
];

// ---------------------------------------------------------------------------
// PUB-12 / PUB-13 / PUB-14 — Plan CTAs
// ---------------------------------------------------------------------------

export const PLAN_CTAS: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Get started free", href: "/schools/register" }, // PUB-12 — Starter
  { label: "Get a quote", href: "/contact" }, // PUB-13 — School Pro
  { label: "Contact us", href: "/contact" }, // PUB-14 — Enterprise
];

// ---------------------------------------------------------------------------
// PUB-15 — FAQ accordion items (hardcoded in page.tsx)
// ---------------------------------------------------------------------------

export const FAQ_ITEMS: ReadonlyArray<{ question: string; answer: string }> = [
  {
    question: "What is included in the free Platform Starter plan?",
    answer:
      "Platform Starter gives your school access to our pre-built STEM curricula for Grades 5–12 at no cost. You get up to 30 students, 2 teachers, and 1 school admin — no credit card required. Content is available in English.",
  },
  {
    question: "How does per-student pricing work for School Pro?",
    answer:
      "School Pro is billed annually at roughly $5–8 per student per year — comparable to the cost of a single textbook. The exact price scales with your student count. Contact us for a precise quote.",
  },
  {
    question: "What counts as a custom curriculum build?",
    answer:
      "A curriculum build is when StudyBuddy generates AI-powered lessons, quizzes, tutorials, and audio for a curriculum your school defines. School Pro includes an annual build allowance. Additional builds are available as paid add-ons.",
  },
  {
    question: "Can we keep using the platform if we exceed the Starter student limit?",
    answer:
      "Yes — we will reach out before locking anything. Upgrading to School Pro unlocks unlimited students and teachers and takes effect immediately.",
  },
  {
    question: "What languages are supported?",
    answer:
      "Pre-built content is available in English on the free Starter plan. School Pro and Enterprise unlock French and Spanish content. UI is available in all three languages on all plans.",
  },
  {
    question: "Is there a COPPA-compliant option for under-13 students?",
    answer:
      "Yes. Students under 13 require parental consent before their account activates. We handle the consent flow automatically on all plans.",
  },
  {
    question: "How does Enterprise / district licensing work?",
    answer:
      "Enterprise covers multiple schools under one agreement — one invoice, one admin dashboard, one support relationship. Pricing is custom based on total student count across the district. Contact us to start a conversation.",
  },
];

// ---------------------------------------------------------------------------
// PUB-16 — Most popular badge (School Pro plan)
// ---------------------------------------------------------------------------

export const MOST_POPULAR_BADGE = {
  text: "Most popular",
  /** Badge is positioned on the School Pro plan card */
  plan: "School Pro",
} as const;
