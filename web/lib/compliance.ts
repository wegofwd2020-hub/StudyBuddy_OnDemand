/**
 * Compliance standards data for StudyBuddy OnDemand.
 *
 * This file is the single source of truth for every accessibility, privacy,
 * and content standard the platform targets or complies with.
 *
 * The About page (/about) renders this table and stamps it with the build time,
 * so the "Last verified" date updates automatically on every deployment.
 */

export type ComplianceStatus = "compliant" | "targeted" | "partial";

export interface ComplianceStandard {
  /** Short display name shown in the table heading */
  standard: string;
  /** Specification version or last-updated year */
  version: string;
  /** One-sentence description of what is covered */
  description: string;
  /** Compliance level */
  status: ComplianceStatus;
  /** Grouping category for visual separation */
  category: "Accessibility" | "Privacy & Legal" | "Content" | "Internationalisation";
}

export const COMPLIANCE_STANDARDS: ComplianceStandard[] = [
  // ── Accessibility ─────────────────────────────────────────────────────────

  {
    standard: "WCAG 2.1 Level AA",
    version: "W3C Rec — June 2018",
    description:
      "Full web-portal compliance with all Level A and AA success criteria including perceivable, operable, understandable, and robust requirements. Verified automatically on every build with axe-core (WCAG2A + WCAG2AA + best-practice rule sets).",
    status: "targeted",
    category: "Accessibility",
  },
  {
    standard: "Dyslexia-Friendly Font — OpenDyslexic",
    version: "OpenDyslexic v3.003",
    description:
      "Students can switch body text to OpenDyslexic via Settings. The preference is persisted in a cookie so the server-side render applies the correct font before React hydrates — eliminating any flash of unstyled text.",
    status: "compliant",
    category: "Accessibility",
  },
  {
    standard: "Windows High Contrast / Forced Colors Mode",
    version: "CSS4 · WCAG 2.1 SC 1.4.11",
    description:
      "A dedicated @media (forced-colors: active) block ensures all interactive elements, status badges, and focus rings remain visible when the OS overrides author colours with the system palette (ButtonText, Highlight, GrayText).",
    status: "compliant",
    category: "Accessibility",
  },
  {
    standard: "Colour Contrast — 4.5:1 Normal Text / 3:1 Large Text",
    version: "WCAG 2.1 SC 1.4.3",
    description:
      "All text–background combinations meet or exceed the AA contrast thresholds. The OKLCH perceptually-uniform colour space is used throughout so contrast values are accurate across display profiles.",
    status: "targeted",
    category: "Accessibility",
  },
  {
    standard: "Screen Reader Support (WAI-ARIA 1.2)",
    version: "W3C Rec — June 2023",
    description:
      "Interactive widgets use correct ARIA roles, aria-label, aria-hidden, and aria-invalid attributes. Decorative icons are hidden from the accessibility tree. Live regions (role=\"status\") announce time-sensitive updates such as the demo countdown banner.",
    status: "compliant",
    category: "Accessibility",
  },
  {
    standard: "Keyboard Navigation — Focus Visible",
    version: "WCAG 2.1 SC 2.1.1 + 2.4.7",
    description:
      "All interactive elements are reachable via Tab and have a visible focus ring (:focus-visible). A skip-to-main-content link at the top of every page lets keyboard users bypass repeated navigation.",
    status: "compliant",
    category: "Accessibility",
  },
  {
    standard: "Android TalkBack / iOS VoiceOver",
    version: "WCAG 2.1 Mobile Guidance",
    description:
      "PSA and notification content is authored to be fully readable by TalkBack (Android) and VoiceOver (iOS) through semantic HTML, ARIA labels, and no information conveyed by colour alone.",
    status: "targeted",
    category: "Accessibility",
  },

  // ── Privacy & Legal ───────────────────────────────────────────────────────

  {
    standard: "COPPA — Children's Online Privacy Protection Act",
    version: "FTC Rule — amended 2013",
    description:
      "Students under 13 require verifiable parental consent before account activation. No data is collected until account_status = 'active'. Only the minimum necessary PII is collected (name, email, grade, locale). No location data, device IDs, or behavioural fingerprinting.",
    status: "compliant",
    category: "Privacy & Legal",
  },
  {
    standard: "FERPA — Family Educational Rights and Privacy Act",
    version: "20 U.S.C. § 1232g · 34 CFR Part 99",
    description:
      "Student progress records, quiz scores, and lesson-view history are treated as educational records. Teacher and admin endpoints are scoped to the student's own institution. JWT secrets are separate for students, teachers, and internal staff so roles cannot be forged or crossed.",
    status: "compliant",
    category: "Privacy & Legal",
  },
  {
    standard: "GDPR — Right to Erasure",
    version: "EU 2016/679 · Art. 17",
    description:
      "Deleted student accounts are anonymised within 30 days: the student_id foreign key is stripped from progress records. No student data is shared with third parties without explicit consent.",
    status: "compliant",
    category: "Privacy & Legal",
  },

  // ── Content ───────────────────────────────────────────────────────────────

  {
    standard: "Age-Appropriate Content — Grades 5–12",
    version: "UK Age Appropriate Design Code (2021)",
    description:
      "All AI-generated lessons, quizzes, and experiments are restricted to academic STEM topics. Content is reviewed by AlexJS for inclusive language before publication. Error messages exposed to students are non-technical and age-appropriate.",
    status: "compliant",
    category: "Content",
  },
  {
    standard: "Reading-Level Accessibility",
    version: "Flesch-Kincaid · CAST UDL Guidelines",
    description:
      "Lesson content is generated at 1–2 grade levels below the student's actual grade to maximise comprehension. PSA and emergency notifications target Flesch-Kincaid Grade 8 or below with multi-channel delivery (text + audio + visual).",
    status: "compliant",
    category: "Content",
  },
  {
    standard: "Inclusive Language",
    version: "AlexJS v11",
    description:
      "All AI-generated content passes AlexJS analysis before publication. Gender-neutral phrasing is enforced for professional roles. No gendered emoji in diagrams or examples.",
    status: "compliant",
    category: "Content",
  },

  // ── Internationalisation ──────────────────────────────────────────────────

  {
    standard: "Multi-Language Support (EN / FR / ES)",
    version: "ISO 639-1 · next-intl 4.8.3",
    description:
      "All student-facing UI strings are fully translated into English, French, and Spanish via next-intl. AI-generated lesson content is built separately per language by the content pipeline — no machine translation of AI output. Students switch locale in Settings; the preference is stored in the JWT.",
    status: "compliant",
    category: "Internationalisation",
  },
  {
    standard: "HTML lang Attribute",
    version: "WCAG 2.1 SC 3.1.1",
    description:
      "The <html lang=\"…\"> attribute is set server-side from the user's active locale so screen readers announce content in the correct language without guessing.",
    status: "compliant",
    category: "Internationalisation",
  },
];

/** Ordered list of categories for display grouping */
export const COMPLIANCE_CATEGORIES: ComplianceStandard["category"][] = [
  "Accessibility",
  "Privacy & Legal",
  "Content",
  "Internationalisation",
];
