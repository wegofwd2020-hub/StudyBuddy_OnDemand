/**
 * Unit tests for section 3.18 — School Settings (`/school/settings`)
 * Covers TC-IDs: SCH-45, SCH-46, SCH-47, SCH-48
 *
 * Run with:
 *   npm test -- settings-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SchoolSettingsPage from "@/app/(school)/school/settings/page";
import {
  MOCK_ADMIN,
  MOCK_TEACHER,
  MOCK_PROFILE,
  SETTINGS_STRINGS,
} from "../e2e/data/settings-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseTeacher = vi.fn();
vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => mockUseTeacher()),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

vi.mock("@/lib/api/subscription", () => ({
  getBillingPortalUrl: vi.fn(),
}));

// Mock clipboard
Object.assign(navigator, {
  clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
});

// ---------------------------------------------------------------------------
// SCH-45 — School profile details render
// ---------------------------------------------------------------------------

describe("SCH-45 — School profile details render", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_PROFILE, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<SchoolSettingsPage />);
    expect(
      screen.getByRole("heading", { name: SETTINGS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the school profile card", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.profileCard)).toBeInTheDocument();
  });

  it("renders the school name", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.schoolName)).toBeInTheDocument();
  });

  it("renders the contact email", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.contactEmail)).toBeInTheDocument();
  });

  it("renders the country", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.country)).toBeInTheDocument();
  });

  it("renders the account status badge", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.status)).toBeInTheDocument();
  });

  it("renders the school ID in monospace", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.schoolId)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-46 — Enrolment code displayed and copyable
// ---------------------------------------------------------------------------

describe("SCH-46 — Enrolment code displayed and copyable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_PROFILE, isLoading: false });
  });

  it("renders the enrolment code card heading", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.enrolmentCard)).toBeInTheDocument();
  });

  it("renders the enrolment code in a <code> element", () => {
    const { container } = render(<SchoolSettingsPage />);
    const codeEl = container.querySelector("code");
    expect(codeEl?.textContent).toContain(SETTINGS_STRINGS.enrolmentCode);
  });

  it("renders the Copy button", () => {
    render(<SchoolSettingsPage />);
    expect(
      screen.getByRole("button", { name: SETTINGS_STRINGS.copyBtn }),
    ).toBeInTheDocument();
  });

  it("shows 'Copied' after clicking Copy", async () => {
    render(<SchoolSettingsPage />);
    fireEvent.click(screen.getByRole("button", { name: SETTINGS_STRINGS.copyBtn }));
    expect(
      await screen.findByRole("button", { name: SETTINGS_STRINGS.copiedBtn }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-47 — Billing portal button visible for admin
// ---------------------------------------------------------------------------

describe("SCH-47 — Billing portal button visible for admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_PROFILE, isLoading: false });
  });

  it("renders the Billing card for school_admin", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.billingCard)).toBeInTheDocument();
  });

  it("renders 'Open billing portal' button for school_admin", () => {
    render(<SchoolSettingsPage />);
    expect(
      screen.getByRole("button", { name: /Open billing portal/ }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-48 — Billing section hidden for non-admin teacher
// ---------------------------------------------------------------------------

describe("SCH-48 — Billing section hidden for non-admin teacher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_TEACHER);
    mockUseQuery.mockReturnValue({ data: MOCK_PROFILE, isLoading: false });
  });

  it("does NOT render the Billing card for a non-admin teacher", () => {
    render(<SchoolSettingsPage />);
    expect(screen.queryByText(SETTINGS_STRINGS.billingCard)).toBeNull();
  });

  it("does NOT render 'Open billing portal' button for a non-admin teacher", () => {
    render(<SchoolSettingsPage />);
    expect(screen.queryByRole("button", { name: /Open billing portal/ })).toBeNull();
  });

  it("shows the contact admin message for non-admin teacher", () => {
    render(<SchoolSettingsPage />);
    expect(screen.getByText(SETTINGS_STRINGS.contactAdmin)).toBeInTheDocument();
  });
});
