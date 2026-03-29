/**
 * Test data for section 4.8 — Content Review Queue (`/admin/content-review`)
 * Covers TC-IDs: ADM-31, ADM-32, ADM-33, ADM-34, ADM-35
 */

import type { ReviewQueueResponse } from "@/lib/api/admin";

export const MOCK_QUEUE: ReviewQueueResponse = {
  total: 2,
  items: [
    {
      version_id: "ver-001",
      unit_id: "unit-001",
      unit_title: "Algebra Basics",
      grade: 8,
      subject: "Math",
      lang: "en",
      content_version: 1,
      status: "pending",
      submitted_at: "2026-03-28T08:00:00Z",
      reviewer_id: null,
    },
    {
      version_id: "ver-002",
      unit_id: "unit-002",
      unit_title: "Photosynthesis",
      grade: 7,
      subject: "Biology",
      lang: "en",
      content_version: 2,
      status: "pending",
      submitted_at: "2026-03-27T08:00:00Z",
      reviewer_id: null,
    },
  ],
};

export const MOCK_QUEUE_EMPTY: ReviewQueueResponse = { total: 0, items: [] };

export const REVIEW_QUEUE_STRINGS = {
  pageHeading: "Content Review Queue",
  // Filter tabs
  tabPending: "pending",
  tabApproved: "approved",
  tabPublished: "published",
  tabRejected: "rejected",
  tabBlocked: "blocked",
  tabAll: "All",
  // Table columns
  colUnit: "Unit",
  colGrade: "Grade",
  colLang: "Lang",
  colStatus: "Status",
  // Review link
  reviewLink: "Review →",
  // Empty state
  noItems: /No .* items in the queue/,
} as const;
