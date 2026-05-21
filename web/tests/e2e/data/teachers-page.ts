/**
 * Test data for section 3.17 — Teacher Management (`/school/teachers`)
 * Covers TC-IDs: SCH-41, SCH-42, SCH-43, SCH-44
 */

export const MOCK_ADMIN = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "school_admin" as const,
};

export const MOCK_TEACHER = {
  teacher_id: "teacher-002",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_INVITED_TEACHER = {
  teacher_id: "teacher-003",
  email: "jane.smith@school.edu",
  role: "teacher",
};

export const TEACHERS_STRINGS = {
  pageHeading: "Teacher Management",
  // Add-teacher form (admin only). The invite flow was replaced by Phase A
  // provisioning (system-generated password emailed to the teacher).
  addFormCard: "Add a teacher",
  nameLabel: "Full name",
  emailLabel: "Work email",
  addBtn: "Add teacher",
  addingBtn: "Adding…",
  // Success
  successMsg: /temporary password has been sent to/,
} as const;

export const TEST_INVITE = {
  name: "Jane Smith",
  email: "jane.smith@school.edu",
};
