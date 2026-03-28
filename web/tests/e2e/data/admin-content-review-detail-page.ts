/**
 * Test data for section 4.9 — Content Review Detail (`/admin/content-review/[version_id]`)
 * Covers TC-IDs: ADM-36..ADM-49
 */

import type { ReviewItemDetail } from "@/lib/api/admin";

export const MOCK_VERSION_ID = "ver-001";

const BASE_ITEM = {
  version_id:      MOCK_VERSION_ID,
  unit_id:         "unit-001",
  unit_title:      "Algebra Basics",
  grade:           8,
  subject:         "Math",
  lang:            "en",
  content_version: 1,
  submitted_at:    "2026-03-28T08:00:00Z",
  reviewer_id:     null,
  lesson_preview:  "In this lesson we explore linear equations...",
  quiz_count:      5,
  alexjs_score:    0,
};

export const MOCK_ITEM_PENDING: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "pending",
  annotations: [],
};

export const MOCK_ITEM_APPROVED: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "approved",
  annotations: [],
};

export const MOCK_ITEM_PUBLISHED: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "published",
  annotations: [],
};

export const MOCK_ITEM_WITH_ANNOTATIONS: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "pending",
  annotations: [
    {
      reviewer_id: "adm-001",
      note:        "Please simplify the language in paragraph 2.",
      created_at:  "2026-03-27T10:00:00Z",
    },
  ],
};

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const REVIEW_DETAIL_STRINGS = {
  backLink:        "Back to queue",
  // Metadata
  lessonPreview:   "Lesson Preview",
  // Actions — pending
  approveBtn:      "Approve",
  rejectBtn:       "Reject",
  // Actions — approved (product_admin)
  publishBtn:      "Publish",
  // Actions — published (product_admin)
  rollbackBtn:     "Rollback",
  blockBtn:        "Block",
  // Modal
  confirmReject:   "Confirm reject",
  confirmBlock:    "Confirm block",
  // Annotations
  annotationsHeading: "Annotations",
} as const;
