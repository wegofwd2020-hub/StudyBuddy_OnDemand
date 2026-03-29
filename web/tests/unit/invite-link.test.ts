import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Enrolment invite link construction
// ---------------------------------------------------------------------------

describe("invite link construction", () => {
  const ORIGIN = "https://app.studybuddy.ca";

  it("builds correct invite URL from enrolment_code", () => {
    const code = "ABC123";
    const url = `${ORIGIN}/enrol/${code}`;
    expect(url).toBe("https://app.studybuddy.ca/enrol/ABC123");
  });

  it("returns null when enrolment_code is null", () => {
    const code: string | null = null;
    const url = code ? `${ORIGIN}/enrol/${code}` : null;
    expect(url).toBeNull();
  });

  it("handles long alphanumeric codes", () => {
    const code = "A1B2C3D4E5F6";
    const url = `${ORIGIN}/enrol/${code}`;
    expect(url).toContain(code);
    expect(url.startsWith("https://")).toBe(true);
  });

  it("email parsing splits on newlines", () => {
    const raw = "a@s.com\nb@s.com\nc@s.com";
    const emails = raw
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter((s) => s.includes("@"));
    expect(emails).toHaveLength(3);
  });

  it("email parsing splits on commas", () => {
    const raw = "a@s.com,b@s.com,c@s.com";
    const emails = raw
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter((s) => s.includes("@"));
    expect(emails).toHaveLength(3);
  });

  it("email parsing strips whitespace and blank lines", () => {
    const raw = "  a@s.com  \n\n  b@s.com  ";
    const emails = raw
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter((s) => s.includes("@"));
    expect(emails).toHaveLength(2);
    expect(emails[0]).toBe("a@s.com");
  });

  it("email parsing rejects non-email strings", () => {
    const raw = "not-an-email\na@b.com";
    const emails = raw
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter((s) => s.includes("@"));
    expect(emails).toHaveLength(1);
    expect(emails[0]).toBe("a@b.com");
  });

  it("mixed delimiters all work", () => {
    const raw = "a@s.com;b@s.com\nc@s.com,d@s.com";
    const emails = raw
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter((s) => s.includes("@"));
    expect(emails).toHaveLength(4);
  });
});

// ---------------------------------------------------------------------------
// inviteTeacher API call
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/school-client", () => ({
  default: { post: vi.fn(), get: vi.fn() },
}));

import schoolApi from "@/lib/api/school-client";
import { inviteTeacher, uploadRoster } from "@/lib/api/school-admin";

const mockPost = schoolApi.post as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("inviteTeacher", () => {
  it("posts name and email to teacher invite endpoint", async () => {
    mockPost.mockResolvedValueOnce({
      data: { teacher_id: "t-123", email: "j@school.edu", role: "teacher" },
    });

    const result = await inviteTeacher("school-abc", "Jane Smith", "j@school.edu");
    expect(result.teacher_id).toBe("t-123");
    expect(mockPost).toHaveBeenCalledWith("/schools/school-abc/teachers/invite", {
      name: "Jane Smith",
      email: "j@school.edu",
    });
  });
});

describe("uploadRoster", () => {
  it("posts student_emails array to enrolment endpoint", async () => {
    mockPost.mockResolvedValueOnce({
      data: { enrolled: 3, already_enrolled: 1 },
    });

    const emails = ["a@s.com", "b@s.com", "c@s.com", "d@s.com"];
    const result = await uploadRoster("school-abc", emails);
    expect(result.enrolled).toBe(3);
    expect(result.already_enrolled).toBe(1);
    expect(mockPost).toHaveBeenCalledWith("/schools/school-abc/enrolment", {
      student_emails: emails,
    });
  });
});
