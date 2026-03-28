/**
 * Test data for section 1.2 — Pricing Page (`/pricing`)
 * Covers TC-IDs: PUB-11 through PUB-16
 *
 * String values sourced from i18n/en.json and page.tsx constants.
 * Update here if copy or feature lists change.
 */

// ---------------------------------------------------------------------------
// PUB-11 — Plan cards (price display)
// ---------------------------------------------------------------------------

export const PLAN_PRICES: ReadonlyArray<{ plan: string; price: string }> = [
  { plan: "Free",    price: "$0"    },
  { plan: "Student", price: "$9.99" },
  { plan: "School",  price: "$299+" },
];

// ---------------------------------------------------------------------------
// PUB-12 / PUB-13 / PUB-14 — Plan CTAs
// ---------------------------------------------------------------------------

export const PLAN_CTAS: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Start free",    href: "/signup"  }, // PUB-12 — Free plan
  { label: "Subscribe now", href: "/signup"  }, // PUB-13 — Student plan
  { label: "Contact sales", href: "/contact" }, // PUB-14 — School plan
];

// ---------------------------------------------------------------------------
// PUB-15 — FAQ accordion items (hardcoded in page.tsx)
// ---------------------------------------------------------------------------

export const FAQ_ITEMS: ReadonlyArray<{ question: string; answer: string }> = [
  {
    question: "Is there a free trial?",
    answer: "Yes. Every account starts with 5 free lessons per month, no credit card required.",
  },
  {
    question: "Can I switch plans at any time?",
    answer:
      "Yes. You can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.",
  },
  {
    question: "What languages are supported?",
    answer:
      "All AI-generated content is available in English, French, and Spanish. UI is also available in all three languages.",
  },
  {
    question: "How does school pricing work?",
    answer:
      "School plans are flat-rate monthly or annual subscriptions covering all students and teachers at the school. Contact us for a custom quote.",
  },
  {
    question: "Is there a COPPA-compliant option for under-13 students?",
    answer:
      "Yes. Students under 13 require parental consent before their account activates. We handle the consent flow automatically.",
  },
];

// ---------------------------------------------------------------------------
// PUB-16 — Most popular badge
// ---------------------------------------------------------------------------

export const MOST_POPULAR_BADGE = {
  text: "Most popular",
  /** Badge is positioned on the Student plan card */
  plan: "Student",
} as const;
