/**
 * Unit tests for section 3.16 — Student Roster (`/school/students`)
 * Covers TC-IDs: SCH-35, SCH-36, SCH-37, SCH-38, SCH-39, SCH-40
 *
 * Run with:
 *   npm test -- students-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StudentsPage from "@/app/(school)/school/students/page";
import {
  MOCK_TEACHER,
  MOCK_ROSTER,
  MOCK_PROFILE,
  STUDENTS_STRINGS,
  NEWLINE_EMAILS,
  COMMA_EMAILS,
  MIXED_EMAILS,
  VALID_EMAIL_COUNT,
} from "../e2e/data/students-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery     = vi.fn();
const mockInvalidateQueries = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery:       vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ invalidateQueries: mockInvalidateQueries })),
  };
});

const mockUploadRoster = vi.fn();
vi.mock("@/lib/api/school-admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/school-admin")>();
  return {
    ...actual,
    uploadRoster: (...args: unknown[]) => mockUploadRoster(...args),
  };
});

// Mock clipboard
Object.assign(navigator, {
  clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
});

function setupQueries(rosterData = MOCK_ROSTER, profileData = MOCK_PROFILE) {
  mockUseQuery.mockImplementation(({ queryKey }: { queryKey: unknown[] }) => {
    if (Array.isArray(queryKey) && queryKey[0] === "roster") {
      return { data: rosterData, isLoading: false };
    }
    if (Array.isArray(queryKey) && queryKey[0] === "school-profile") {
      return { data: profileData, isLoading: false };
    }
    return { data: undefined, isLoading: false };
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  setupQueries();
});

// ---------------------------------------------------------------------------
// SCH-35 — Roster table renders
// ---------------------------------------------------------------------------

describe("SCH-35 — Roster table renders", () => {
  it("renders the page heading", () => {
    render(<StudentsPage />);
    expect(
      screen.getByRole("heading", { name: STUDENTS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders Email column header", () => {
    render(<StudentsPage />);
    expect(screen.getByText(STUDENTS_STRINGS.colEmail)).toBeInTheDocument();
  });

  it("renders Status column header", () => {
    render(<StudentsPage />);
    expect(screen.getByText(STUDENTS_STRINGS.colStatus)).toBeInTheDocument();
  });

  it("renders Added column header", () => {
    render(<StudentsPage />);
    expect(screen.getByText(STUDENTS_STRINGS.colAdded)).toBeInTheDocument();
  });

  it("renders each student email in the table", () => {
    render(<StudentsPage />);
    for (const item of MOCK_ROSTER.roster) {
      expect(screen.getByText(item.student_email)).toBeInTheDocument();
    }
  });

  it("renders enrolled count badge", () => {
    render(<StudentsPage />);
    expect(
      screen.getByText(`${MOCK_ROSTER.roster.length} enrolled`),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-36 — Invite link displays and Copy button works
// ---------------------------------------------------------------------------

describe("SCH-36 — Invite link displayed and copyable", () => {
  it("renders the invite link card heading", () => {
    render(<StudentsPage />);
    expect(screen.getByText(STUDENTS_STRINGS.inviteLinkHeading)).toBeInTheDocument();
  });

  it("renders the enrolment code in the invite URL", () => {
    const { container } = render(<StudentsPage />);
    const code = MOCK_PROFILE.enrolment_code!;
    // The invite URL is shown in a <code> element
    const codeEl = container.querySelector("code");
    expect(codeEl?.textContent).toContain(code);
  });

  it("renders the Copy button", () => {
    render(<StudentsPage />);
    expect(screen.getByRole("button", { name: STUDENTS_STRINGS.copyBtn })).toBeInTheDocument();
  });

  it("shows 'Copied' after clicking Copy", async () => {
    render(<StudentsPage />);
    fireEvent.click(screen.getByRole("button", { name: STUDENTS_STRINGS.copyBtn }));
    expect(await screen.findByRole("button", { name: STUDENTS_STRINGS.copiedBtn })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-37 — Bulk email enrol — newline separated
// ---------------------------------------------------------------------------

describe("SCH-37 — Bulk email enrol newline separated", () => {
  beforeEach(() => {
    mockUploadRoster.mockResolvedValue({ enrolled: 3, already_enrolled: 0 });
  });

  it("calls uploadRoster with 3 emails from newline input", async () => {
    render(<StudentsPage />);
    fireEvent.change(screen.getByLabelText(STUDENTS_STRINGS.emailListLabel), {
      target: { value: NEWLINE_EMAILS },
    });
    fireEvent.click(screen.getByRole("button", { name: STUDENTS_STRINGS.enrollBtn }));
    await waitFor(() => expect(mockUploadRoster).toHaveBeenCalledTimes(1));
    expect(mockUploadRoster).toHaveBeenCalledWith(
      MOCK_TEACHER.school_id,
      ["test1@school.edu", "test2@school.edu", "test3@school.edu"],
    );
  });

  it("shows success message after enrolment", async () => {
    const { container } = render(<StudentsPage />);
    fireEvent.change(screen.getByLabelText(STUDENTS_STRINGS.emailListLabel), {
      target: { value: NEWLINE_EMAILS },
    });
    fireEvent.click(screen.getByRole("button", { name: STUDENTS_STRINGS.enrollBtn }));
    // Success text is split across spans — check container textContent
    await waitFor(() => {
      const successDiv = container.querySelector("div.text-green-700");
      expect(successDiv?.textContent).toMatch(STUDENTS_STRINGS.enrolledSuccess);
    });
  });
});

// ---------------------------------------------------------------------------
// SCH-38 — Bulk email enrol — comma separated
// ---------------------------------------------------------------------------

describe("SCH-38 — Bulk email enrol comma separated", () => {
  beforeEach(() => {
    mockUploadRoster.mockResolvedValue({ enrolled: 3, already_enrolled: 0 });
  });

  it("calls uploadRoster with 3 emails from comma-separated input", async () => {
    render(<StudentsPage />);
    fireEvent.change(screen.getByLabelText(STUDENTS_STRINGS.emailListLabel), {
      target: { value: COMMA_EMAILS },
    });
    fireEvent.click(screen.getByRole("button", { name: STUDENTS_STRINGS.enrollBtn }));
    await waitFor(() => expect(mockUploadRoster).toHaveBeenCalledTimes(1));
    expect(mockUploadRoster).toHaveBeenCalledWith(
      MOCK_TEACHER.school_id,
      ["test1@school.edu", "test2@school.edu", "test3@school.edu"],
    );
  });
});

// ---------------------------------------------------------------------------
// SCH-39 — Non-email strings filtered out
// ---------------------------------------------------------------------------

describe("SCH-39 — Non-email strings filtered out", () => {
  beforeEach(() => {
    mockUploadRoster.mockResolvedValue({ enrolled: VALID_EMAIL_COUNT, already_enrolled: 0 });
  });

  it("filters out non-email strings — only valid emails sent to API", async () => {
    render(<StudentsPage />);
    fireEvent.change(screen.getByLabelText(STUDENTS_STRINGS.emailListLabel), {
      target: { value: MIXED_EMAILS },
    });
    fireEvent.click(screen.getByRole("button", { name: STUDENTS_STRINGS.enrollBtn }));
    await waitFor(() => expect(mockUploadRoster).toHaveBeenCalledTimes(1));
    const emails = mockUploadRoster.mock.calls[0][1] as string[];
    // All sent emails must contain "@"
    expect(emails.every((e) => e.includes("@"))).toBe(true);
    expect(emails).toHaveLength(VALID_EMAIL_COUNT);
  });
});

// ---------------------------------------------------------------------------
// SCH-40 — Live email count shown
// ---------------------------------------------------------------------------

describe("SCH-40 — Live email count shown", () => {
  it("shows detected email count when valid emails are entered", () => {
    render(<StudentsPage />);
    fireEvent.change(screen.getByLabelText(STUDENTS_STRINGS.emailListLabel), {
      target: { value: NEWLINE_EMAILS },
    });
    expect(screen.getByText(/3 valid emails? detected/)).toBeInTheDocument();
  });

  it("does NOT show email count when input is empty", () => {
    render(<StudentsPage />);
    expect(screen.queryByText(/valid email/)).toBeNull();
  });
});
