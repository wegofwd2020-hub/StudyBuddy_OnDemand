/**
 * Test data for section 2.8 — Progress Page (`/progress`)
 * Covers TC-IDs: STU-29, STU-30
 *
 * Auth note: /progress requires a real Auth0 session for E2E.
 * Unit tests mock useProgressHistory() directly via vi.mock.
 *
 * Backend API route for E2E page.route() interception:
 *   GET /api/v1/progress/history?limit=50 → MOCK_PROGRESS_HISTORY | MOCK_PROGRESS_EMPTY
 */

import type { ProgressHistory } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mock progress history — 3 sessions (passed, failed, in-progress) (STU-29)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_HISTORY: ProgressHistory = {
  unit_progress: [
    { unit_id: "G8-SCI-001", status: "completed",    best_score: 3, attempts: 1, last_attempted_at: "2026-03-25T10:00:00Z" },
    { unit_id: "G8-MATH-001", status: "needs_retry", best_score: 1, attempts: 2, last_attempted_at: "2026-03-24T14:30:00Z" },
    { unit_id: "G8-SCI-002", status: "in_progress",  best_score: null, attempts: 1, last_attempted_at: "2026-03-23T09:15:00Z" },
  ],
  sessions: [
    {
      session_id: "sess-001",
      unit_id: "G8-SCI-001",
      unit_title: "Cell Biology",
      subject: "Science",
      started_at: "2026-03-25T10:00:00Z",
      ended_at: "2026-03-25T10:15:00Z",
      score: 3,
      total: 3,
      passed: true,
      attempt_number: 1,
    },
    {
      session_id: "sess-002",
      unit_id: "G8-MATH-001",
      unit_title: "Linear Equations",
      subject: "Mathematics",
      started_at: "2026-03-24T14:30:00Z",
      ended_at: "2026-03-24T14:45:00Z",
      score: 1,
      total: 3,
      passed: false,
      attempt_number: 2,
    },
    {
      session_id: "sess-003",
      unit_id: "G8-SCI-002",
      unit_title: "Chemical Reactions",
      subject: "Science",
      started_at: "2026-03-23T09:15:00Z",
      ended_at: null,
      score: null,
      total: null,
      passed: null,
      attempt_number: 1,
    },
  ],
};

// ---------------------------------------------------------------------------
// Mock empty history (STU-30)
// ---------------------------------------------------------------------------

export const MOCK_PROGRESS_EMPTY: ProgressHistory = {
  sessions: [],
  unit_progress: [],
};

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const PROGRESS_STRINGS = {
  pageHeading:    "Progress History",
  emptyMessage:   "No sessions yet. Start learning to track progress.",
  browseSubjects: "Browse Subjects",
  lessonBtn:      "Lesson",
  retryQuizBtn:   "Retry quiz",
} as const;

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

export function lessonHref(unitId: string) { return `/lesson/${unitId}`; }
export function quizHref(unitId: string)   { return `/quiz/${unitId}`; }
