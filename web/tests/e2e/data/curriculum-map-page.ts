/**
 * Test data for section 2.10 — Curriculum Map (`/curriculum`)
 * Covers TC-IDs: STU-32, STU-33
 *
 * Auth note: /curriculum requires a real Auth0 session for E2E.
 * Unit tests mock useCurriculumTree() and useProgressHistory() directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET /api/v1/curriculum/tree          → MOCK_CURRICULUM_TREE
 *   GET /api/v1/progress/history?limit=100 → MOCK_PROGRESS_WITH_STATUS
 */

import type { CurriculumTree, ProgressHistory } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock curriculum tree — Grade 8, 2 subjects, mix of lab / non-lab (STU-32)
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
        {
          unit_id: "G8-SCI-003",
          title: "Forces and Motion",
          subject: "Science",
          grade: 8,
          sort_order: 3,
          has_lab: false,
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Mock progress history — covers all 4 UnitStatus values (STU-33)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_WITH_STATUS: ProgressHistory = {
  sessions: [],
  unit_progress: [
    {
      unit_id: "G8-SCI-001",
      status: "completed",
      best_score: 3,
      attempts: 1,
      last_attempted_at: "2026-03-25T10:00:00Z",
    },
    {
      unit_id: "G8-MATH-001",
      status: "needs_retry",
      best_score: 1,
      attempts: 2,
      last_attempted_at: "2026-03-24T14:30:00Z",
    },
    {
      unit_id: "G8-SCI-002",
      status: "in_progress",
      best_score: null,
      attempts: 1,
      last_attempted_at: "2026-03-23T09:00:00Z",
    },
    // G8-MATH-002, G8-MATH-003, G8-SCI-003 → not_started (absent from map)
  ],
};

// ---------------------------------------------------------------------------
// Empty progress (all units not_started) (STU-32 baseline)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_EMPTY: ProgressHistory = {
  sessions: [],
  unit_progress: [],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// (title key matches useTranslations("curriculum_map_screen") — mock returns key)
// ---------------------------------------------------------------------------

export const CURRICULUM_MAP_STRINGS = {
  title: "title",
  noUnits: "no_units",
  lessonBtn: "Lesson",
  quizBtn: "Quiz",
  labBadge: "Lab",
  // Status legend labels (rendered as plain text)
  completed: "Completed",
  needsRetry: "Needs retry",
  inProgress: "In progress",
  notStarted: "Not started",
} as const;

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

export function lessonHref(unitId: string) {
  return `/lesson/${unitId}`;
}
export function quizHref(unitId: string) {
  return `/quiz/${unitId}`;
}
