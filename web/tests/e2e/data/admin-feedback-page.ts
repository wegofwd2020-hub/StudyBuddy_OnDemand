/**
 * Test data for section 4.10 — Feedback Queue (`/admin/feedback`)
 * Covers TC-IDs: ADM-50, ADM-51, ADM-52, ADM-53, ADM-54
 */

import type { FeedbackListResponse } from "@/lib/api/admin";

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const MOCK_FEEDBACK_OPEN: FeedbackListResponse = {
  total: 3,
  page: 1,
  page_size: 20,
  items: [
    {
      feedback_id: "fb-001",
      student_id: "stu-001",
      unit_id: "unit-001",
      unit_title: "Algebra Basics",
      rating: 3,
      comment: "Hard to follow",
      submitted_at: "2026-03-28T09:00:00Z",
      resolved: false,
    },
    {
      feedback_id: "fb-002",
      student_id: "stu-002",
      unit_id: "unit-002",
      unit_title: "Photosynthesis",
      rating: 5,
      comment: "Great lesson!",
      submitted_at: "2026-03-27T09:00:00Z",
      resolved: false,
    },
  ],
};

export const MOCK_FEEDBACK_RESOLVED: FeedbackListResponse = {
  total: 1,
  page: 1,
  page_size: 20,
  items: [
    {
      feedback_id: "fb-003",
      student_id: "stu-003",
      unit_id: "unit-001",
      unit_title: "Algebra Basics",
      rating: 2,
      comment: "Too fast",
      submitted_at: "2026-03-26T09:00:00Z",
      resolved: true,
    },
  ],
};

// 21 items to test pagination
export const MOCK_FEEDBACK_PAGE1: FeedbackListResponse = {
  total: 21,
  page: 1,
  page_size: 20,
  items: Array.from({ length: 20 }, (_, i) => ({
    feedback_id: `fb-p${i}`,
    student_id: `stu-${i}`,
    unit_id: "unit-001",
    unit_title: "Algebra Basics",
    rating: 4,
    comment: null,
    submitted_at: "2026-03-28T09:00:00Z",
    resolved: false,
  })),
};

export const FEEDBACK_STRINGS = {
  pageHeading: "Student Feedback",
  // Tabs
  tabOpen: "Open",
  tabResolved: "Resolved",
  // Resolve button
  resolveBtn: "Resolve",
  // Pagination
  nextBtn: "Next",
  prevBtn: "Previous",
  // Access denied
  accessDenied: "Access denied",
} as const;
