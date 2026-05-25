/**
 * Unit tests for section 3.7 — Reports At-Risk (`/school/reports/at-risk`)
 * Covers TC-IDs: SCH-12, SCH-13
 *
 * Run with:
 *   npm test -- at-risk-page
 *
 * The report was redesigned from a per-unit "curriculum health" breakdown into
 * a per-student "At-Risk Students" list (Needs attention / Reviewed sections
 * with Remind + Mark-seen actions).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AtRiskReportPage from "@/app/(school)/school/reports/at-risk/page";
import {
  MOCK_TEACHER,
  MOCK_AT_RISK,
  MOCK_AT_RISK_NONE,
  AT_RISK_STRINGS,
} from "../e2e/data/at-risk-page";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    // The page wires mark-seen + reminder mutations; stub them so render works
    // without a QueryClientProvider.
    useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false, isSuccess: false })),
    useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
  };
});

const unseen = MOCK_AT_RISK.students.filter((s) => !s.is_seen);
const seen = MOCK_AT_RISK.students.filter((s) => s.is_seen);

// ---------------------------------------------------------------------------
// SCH-12 — At-risk student list renders
// ---------------------------------------------------------------------------

describe("SCH-12 — At-risk report renders with at-risk students", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_AT_RISK, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getByRole("heading", { name: AT_RISK_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the inactivity / pass-rate thresholds", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getByText(
        new RegExp(`inactive.*${MOCK_AT_RISK.inactive_days_threshold} days`),
      ),
    ).toBeInTheDocument();
  });

  it("renders the Needs attention section with the unseen count", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getByText(new RegExp(`Needs attention \\(${unseen.length}\\)`)),
    ).toBeInTheDocument();
  });

  it("renders the Reviewed section with the seen count", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getByText(new RegExp(`Reviewed \\(${seen.length}\\)`)),
    ).toBeInTheDocument();
  });

  it("renders each unseen student's name", () => {
    render(<AtRiskReportPage />);
    for (const s of unseen) {
      expect(screen.getByText(s.student_name)).toBeInTheDocument();
    }
  });

  it("renders the reviewed student's name", () => {
    render(<AtRiskReportPage />);
    for (const s of seen) {
      expect(screen.getByText(s.student_name)).toBeInTheDocument();
    }
  });

  it("renders a low-pass-rate value in red", () => {
    const { container } = render(<AtRiskReportPage />);
    const redCell = container.querySelector("span.text-red-600");
    expect(redCell).toBeTruthy();
  });

  it("renders Remind and Mark seen actions for unseen students", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getAllByRole("button", { name: new RegExp(AT_RISK_STRINGS.remindBtn) }),
    ).toHaveLength(unseen.length);
    expect(
      screen.getAllByRole("button", { name: new RegExp(AT_RISK_STRINGS.markSeenBtn) }),
    ).toHaveLength(unseen.length);
  });

  it("links each student to their report detail", () => {
    render(<AtRiskReportPage />);
    const link = screen.getByText(unseen[0].student_name).closest("a");
    expect(link?.getAttribute("href")).toBe(
      `/school/reports/student/${unseen[0].student_id}`,
    );
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<AtRiskReportPage />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// SCH-13 — Empty state if no at-risk students
// ---------------------------------------------------------------------------

describe("SCH-13 — Empty state when no students are at risk", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_AT_RISK_NONE, isLoading: false });
  });

  it("shows the 'No at-risk students' message", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.noStudents)).toBeInTheDocument();
  });

  it("does not render the Needs attention section when none at risk", () => {
    render(<AtRiskReportPage />);
    expect(screen.queryByText(AT_RISK_STRINGS.needsAttention)).toBeNull();
  });
});
