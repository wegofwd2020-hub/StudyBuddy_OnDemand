/**
 * Test data for section 3.13 — Digest Settings (`/school/digest`)
 * Covers TC-IDs: SCH-22, SCH-23
 */

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "teacher" as const,
};

export const DIGEST_STRINGS = {
  pageHeading:      "Weekly Digest",
  cardHeading:      "Digest settings",
  emailLabel:       "Email address",
  emailPlaceholder: "you@school.edu",
  timezoneLabel:    "Timezone",
  saveBtn:          "Save settings",
  savingBtn:        "Saving…",
  savedConfirm:     "Saved",
  // Toggle label (initial enabled state)
  digestEnabled:    "Digest enabled — sent every Monday",
  digestDisabled:   "Digest disabled",
  // What's in the digest card
  digestInfoHeading: "What's in the digest?",
} as const;

export const TEST_EMAIL = "teacher@school.edu";
