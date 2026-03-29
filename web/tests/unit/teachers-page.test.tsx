/**
 * Unit tests for section 3.17 — Teacher Management (`/school/teachers`)
 * Covers TC-IDs: SCH-41, SCH-42, SCH-43, SCH-44
 *
 * Run with:
 *   npm test -- teachers-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TeachersPage from "@/app/(school)/school/teachers/page";
import { SchoolNav } from "@/components/layout/SchoolNav";
import {
  MOCK_ADMIN,
  MOCK_TEACHER,
  MOCK_INVITED_TEACHER,
  TEACHERS_STRINGS,
  TEST_INVITE,
} from "../e2e/data/teachers-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/school/teachers"),
}));

const mockUseTeacher = vi.fn();
vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => mockUseTeacher()),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

const mockInviteTeacher = vi.fn();
vi.mock("@/lib/api/school-admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/school-admin")>();
  return {
    ...actual,
    inviteTeacher: (...args: unknown[]) => mockInviteTeacher(...args),
  };
});

// ---------------------------------------------------------------------------
// SCH-41 — Invite form visible for school_admin
// ---------------------------------------------------------------------------

describe("SCH-41 — Invite form visible for school_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("heading", { name: TEACHERS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders 'Admin only' badge", () => {
    render(<TeachersPage />);
    expect(screen.getByText(TEACHERS_STRINGS.adminOnlyBadge)).toBeInTheDocument();
  });

  it("renders the Invite a teacher card", () => {
    render(<TeachersPage />);
    expect(screen.getByText(TEACHERS_STRINGS.inviteFormCard)).toBeInTheDocument();
  });

  it("renders the Full name input field", () => {
    render(<TeachersPage />);
    expect(screen.getByLabelText(TEACHERS_STRINGS.nameLabel)).toBeInTheDocument();
  });

  it("renders the Work email input field", () => {
    render(<TeachersPage />);
    expect(screen.getByLabelText(TEACHERS_STRINGS.emailLabel)).toBeInTheDocument();
  });

  it("renders the Send invitation button", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("button", { name: TEACHERS_STRINGS.sendInviteBtn }),
    ).toBeInTheDocument();
  });

  it("Send invitation button is disabled when fields are empty", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("button", { name: TEACHERS_STRINGS.sendInviteBtn }),
    ).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// SCH-42 — Access denied for non-admin teacher
// ---------------------------------------------------------------------------

describe("SCH-42 — Access denied for non-admin teacher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_TEACHER);
  });

  it("shows access denied message for non-admin", () => {
    render(<TeachersPage />);
    expect(screen.getByText(TEACHERS_STRINGS.accessDenied)).toBeInTheDocument();
  });

  it("does NOT render the invite form for non-admin", () => {
    render(<TeachersPage />);
    expect(screen.queryByText(TEACHERS_STRINGS.inviteFormCard)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SCH-43 — Successful invite adds to list
// ---------------------------------------------------------------------------

describe("SCH-43 — Successful invite adds teacher to list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockInviteTeacher.mockResolvedValue(MOCK_INVITED_TEACHER);
  });

  it("shows success message after invite", async () => {
    render(<TeachersPage />);
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.nameLabel), {
      target: { value: TEST_INVITE.name },
    });
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.emailLabel), {
      target: { value: TEST_INVITE.email },
    });
    fireEvent.click(screen.getByRole("button", { name: TEACHERS_STRINGS.sendInviteBtn }));
    expect(await screen.findByText(TEACHERS_STRINGS.successMsg)).toBeInTheDocument();
  });

  it("shows invited teacher in the session table", async () => {
    render(<TeachersPage />);
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.nameLabel), {
      target: { value: TEST_INVITE.name },
    });
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.emailLabel), {
      target: { value: TEST_INVITE.email },
    });
    fireEvent.click(screen.getByRole("button", { name: TEACHERS_STRINGS.sendInviteBtn }));
    await waitFor(() => {
      const matches = screen.getAllByText(MOCK_INVITED_TEACHER.email);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("clears name and email fields after invite", async () => {
    render(<TeachersPage />);
    const nameInput = screen.getByLabelText(
      TEACHERS_STRINGS.nameLabel,
    ) as HTMLInputElement;
    const emailInput = screen.getByLabelText(
      TEACHERS_STRINGS.emailLabel,
    ) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: TEST_INVITE.name } });
    fireEvent.change(emailInput, { target: { value: TEST_INVITE.email } });
    fireEvent.click(screen.getByRole("button", { name: TEACHERS_STRINGS.sendInviteBtn }));
    await waitFor(() => expect(nameInput.value).toBe(""));
    expect(emailInput.value).toBe("");
  });
});

// ---------------------------------------------------------------------------
// SCH-44 — Teachers nav item hidden for non-admin
// ---------------------------------------------------------------------------

describe("SCH-44 — Teachers nav item visibility in SchoolNav", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("shows Teachers nav item for school_admin", () => {
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Teachers" })).toBeInTheDocument();
  });

  it("does NOT show Teachers nav item for non-admin teacher", () => {
    mockUseTeacher.mockReturnValue(MOCK_TEACHER);
    render(<SchoolNav />);
    expect(screen.queryByRole("link", { name: "Teachers" })).toBeNull();
  });
});
