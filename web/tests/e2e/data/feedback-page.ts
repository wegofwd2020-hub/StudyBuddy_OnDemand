/**
 * Test data for section 3.10 — Reports Feedback (`/school/reports/feedback`)
 * Covers TC-IDs: SCH-16
 */

import type { FeedbackReport } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_FEEDBACK_REPORT: FeedbackReport = {
  school_id: "school-001",
  total_feedback_count: 5,
  unreviewed_count: 2,
  avg_rating_overall: 3.8,
  // Flat rows since #611 — the report paginates instead of grouping by unit.
  items: [
    {
      feedback_id: "fb-001",
      unit_id: "G8-MATH-001",
      unit_name: "Linear Equations",
      category: "content",
      rating: 3,
      message: "The examples could be clearer.",
      helpful: null,
      content_type: null,
      submitted_at: "2026-03-25T10:00:00Z",
      reviewed: false,
    },
    {
      feedback_id: "fb-002",
      unit_id: "G8-MATH-001",
      unit_name: "Linear Equations",
      category: "ux",
      rating: 4,
      message: "Navigation is smooth.",
      helpful: null,
      content_type: null,
      submitted_at: "2026-03-24T09:00:00Z",
      reviewed: true,
    },
    {
      feedback_id: "fb-003",
      unit_id: "G8-SCI-002",
      unit_name: "Photosynthesis",
      category: "content",
      rating: null,
      message: "The second question made no sense.",
      helpful: false,
      content_type: "lesson",
      submitted_at: "2026-03-23T08:00:00Z",
      reviewed: false,
    },
  ],
  pagination: { page: 1, page_size: 25, total: 3 },
};

export const MOCK_FEEDBACK_EMPTY: FeedbackReport = {
  school_id: "school-001",
  total_feedback_count: 0,
  unreviewed_count: 0,
  avg_rating_overall: null,
  items: [],
  pagination: { page: 1, page_size: 25, total: 0 },
};

export const FEEDBACK_STRINGS = {
  pageHeading: "Student Feedback",
  totalLabel: /\d+ total/,
  unreviewedBadge: /\d+ unreviewed/,
  unreviewedItemBadge: "Unreviewed",
  emptyState: "No feedback to show.",
  // Table columns (#611)
  colUnit: "Unit",
  colVerdict: "Verdict",
  colComment: "Comment",
  notHelpful: "👎 Not helpful",
} as const;
