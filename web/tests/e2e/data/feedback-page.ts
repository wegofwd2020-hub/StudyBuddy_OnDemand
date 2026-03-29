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
  by_unit: [
    {
      unit_id: "G8-MATH-001",
      unit_name: "Linear Equations",
      feedback_count: 3,
      category_breakdown: { content: 2, ux: 1 },
      trending: true,
      feedback_items: [
        {
          feedback_id: "fb-001",
          category: "content",
          rating: 3,
          message: "The examples could be clearer.",
          submitted_at: "2026-03-25T10:00:00Z",
          reviewed: false,
        },
        {
          feedback_id: "fb-002",
          category: "ux",
          rating: 4,
          message: "Navigation is smooth.",
          submitted_at: "2026-03-24T09:00:00Z",
          reviewed: true,
        },
        {
          feedback_id: "fb-003",
          category: "content",
          rating: null,
          message: "Missing worked examples.",
          submitted_at: "2026-03-23T08:00:00Z",
          reviewed: false,
        },
      ],
    },
    {
      unit_id: "G8-SCI-001",
      unit_name: "Cell Biology",
      feedback_count: 2,
      category_breakdown: { general: 2 },
      trending: false,
      feedback_items: [
        {
          feedback_id: "fb-004",
          category: "general",
          rating: 5,
          message: "Excellent unit!",
          submitted_at: "2026-03-22T07:00:00Z",
          reviewed: true,
        },
        {
          feedback_id: "fb-005",
          category: "general",
          rating: 4,
          message: "Good but audio was too fast.",
          submitted_at: "2026-03-21T06:00:00Z",
          reviewed: true,
        },
      ],
    },
  ],
};

export const MOCK_FEEDBACK_EMPTY: FeedbackReport = {
  school_id: "school-001",
  total_feedback_count: 0,
  unreviewed_count: 0,
  avg_rating_overall: null,
  by_unit: [],
};

export const FEEDBACK_STRINGS = {
  pageHeading: "Student Feedback",
  totalLabel: /\d+ total/,
  unreviewedBadge: /\d+ unreviewed/,
  trendingLabel: "Trending",
  noRatingLabel: "No rating",
  unreviewedItemBadge: "Unreviewed",
  emptyState: "No feedback submitted yet.",
} as const;
