/**
 * Test data for section 2.3 — Subjects Page (`/subjects`)
 * Covers TC-IDs: STU-12, STU-13, STU-14
 *
 * Auth note: /subjects requires a real Auth0 session for E2E.
 * Unit tests mock useCurriculumTree() directly.
 *
 * Implementation note (STU-13): The page renders all units inline per subject
 * card — there is no accordion expand/collapse. Units are always visible.
 * STU-13 is interpreted as: units within a subject card are visible and
 * their Lesson/Quiz buttons have correct hrefs.
 *
 * Implementation note (STU-14): Paywall is triggered server-side (HTTP 402)
 * when navigating to /lesson/[unit_id] with a free-plan account. The subjects
 * page itself does not gate content — it always shows all units.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/curriculum/tree → MOCK_CURRICULUM_TREE
 */

import type { CurriculumTree } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock CurriculumTree — Grade 8, 2 subjects, mix of lab / non-lab units
// ---------------------------------------------------------------------------

export const MOCK_CURRICULUM_TREE: CurriculumTree = {
  curriculum_id: "default-2026-g8",
  grade: 8,
  subjects: [
    {
      subject: "Mathematics",
      units: [
        {
          unit_id: "G8-MATH-001",
          title: "Linear Equations",
          subject: "Mathematics",
          grade: 8,
          sort_order: 1,
          has_lab: false,
        },
        {
          unit_id: "G8-MATH-002",
          title: "Quadratic Functions",
          subject: "Mathematics",
          grade: 8,
          sort_order: 2,
          has_lab: false,
        },
        {
          unit_id: "G8-MATH-003",
          title: "Geometry: Pythagorean Theorem",
          subject: "Mathematics",
          grade: 8,
          sort_order: 3,
          has_lab: false,
        },
      ],
    },
    {
      subject: "Science",
      units: [
        {
          unit_id: "G8-SCI-001",
          title: "Cell Biology",
          subject: "Science",
          grade: 8,
          sort_order: 1,
          has_lab: true,
        },
        {
          unit_id: "G8-SCI-002",
          title: "Chemical Reactions",
          subject: "Science",
          grade: 8,
          sort_order: 2,
          has_lab: true,
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const SUBJECTS_STRINGS = {
  pageHeading:  "Subjects",
  errorMessage: "Could not load curriculum. Please retry.",
  lessonBtn:    "Lesson",
  quizBtn:      "Quiz",
} as const;

// ---------------------------------------------------------------------------
// Derived href helpers (mirrors page.tsx link construction)
// ---------------------------------------------------------------------------

export function lessonHref(unitId: string) {
  return `/lesson/${unitId}`;
}

export function quizHref(unitId: string) {
  return `/quiz/${unitId}`;
}
