/**
 * Unit tests for section 3.2 — School Dashboard (`/school/dashboard`)
 * Covers TC-IDs: SCH-03, SCH-04, SCH-05
 *
 * Run with:
 *   npm test -- school-dashboard
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import SchoolDashboard from "@/app/(school)/school/dashboard/page";
import {
  MOCK_TEACHER,
  MOCK_OVERVIEW,
  MOCK_OVERVIEW_NO_STRUGGLES,
  MOCK_ALERTS_WITH_UNREAD,
  MOCK_ALERTS_EMPTY,
  DASHBOARD_STRINGS,
  DASHBOARD_HREFS,
} from "../e2e/data/school-dashboard";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

// Mock useQuery to return overview + alerts based on queryKey
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn(({ queryKey }: { queryKey: unknown[] }) => {
      if (Array.isArray(queryKey) && queryKey[0] === "report-overview") {
        return mockUseQueryOverview();
      }
      if (Array.isArray(queryKey) && queryKey[0] === "alerts") {
        return mockUseQueryAlerts();
      }
      return { data: undefined, isLoading: false };
    }),
  };
});

const mockUseQueryOverview = vi.fn();
const mockUseQueryAlerts = vi.fn();

// ---------------------------------------------------------------------------
// SCH-03 — Dashboard loads: KPI cards visible
// ---------------------------------------------------------------------------

describe("SCH-03 — Dashboard KPI cards render", () => {
  beforeEach(() => {
    mockUseQueryOverview.mockReturnValue({ data: MOCK_OVERVIEW, isLoading: false });
    mockUseQueryAlerts.mockReturnValue({ data: MOCK_ALERTS_EMPTY, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<SchoolDashboard />);
    expect(
      screen.getByRole("heading", { name: DASHBOARD_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders Enrolled students KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.enrolledStudents)).toBeInTheDocument();
  });

  it("renders enrolled students value", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(String(MOCK_OVERVIEW.enrolled_students))).toBeInTheDocument();
  });

  it("renders Active this week KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.activeThisWeek)).toBeInTheDocument();
  });

  it("renders Lessons viewed KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.lessonsViewed)).toBeInTheDocument();
  });

  it("renders lessons viewed value", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(String(MOCK_OVERVIEW.lessons_viewed))).toBeInTheDocument();
  });

  it("renders Pass rate KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.passRate)).toBeInTheDocument();
  });

  it("renders Quiz attempts KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.quizAttempts)).toBeInTheDocument();
  });

  it("renders Unreviewed feedback KPI card title", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.unreviewedFeedback)).toBeInTheDocument();
  });

  it("renders View full report link with correct href", () => {
    render(<SchoolDashboard />);
    const link = screen.getByRole("link", { name: DASHBOARD_STRINGS.viewFullReport });
    expect(link.getAttribute("href")).toBe(DASHBOARD_HREFS.overview);
  });

  it("renders Units needing attention section when struggles exist", () => {
    render(<SchoolDashboard />);
    expect(screen.getByText(DASHBOARD_STRINGS.unitsNeedingAttention)).toBeInTheDocument();
  });

  it("renders each struggling unit as a badge", () => {
    render(<SchoolDashboard />);
    for (const uid of MOCK_OVERVIEW.units_with_struggles) {
      expect(screen.getByText(uid)).toBeInTheDocument();
    }
  });

  it("renders View at-risk report link", () => {
    render(<SchoolDashboard />);
    const link = screen.getByRole("link", { name: DASHBOARD_STRINGS.viewAtRiskReport });
    expect(link.getAttribute("href")).toBe(DASHBOARD_HREFS.atRisk);
  });

  it("does NOT render Units needing attention when struggles list is empty", () => {
    mockUseQueryOverview.mockReturnValue({
      data: MOCK_OVERVIEW_NO_STRUGGLES,
      isLoading: false,
    });
    render(<SchoolDashboard />);
    expect(screen.queryByText(DASHBOARD_STRINGS.unitsNeedingAttention)).toBeNull();
  });

  it("shows loading skeletons while fetching", () => {
    mockUseQueryOverview.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<SchoolDashboard />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("renders all quick-nav links", () => {
    render(<SchoolDashboard />);
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.classOverview }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.trendsReport }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.unitPerformance }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.studentFeedback }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.exportCsv }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: DASHBOARD_STRINGS.alertInbox }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SCH-04 — SchoolNav is visible
// (SchoolNav is rendered by the layout, not the page — verified via import path)
// ---------------------------------------------------------------------------

describe("SCH-04 — SchoolNav presence", () => {
  it("SchoolNav component file exists at expected path", async () => {
    const mod = await import("@/components/layout/SchoolNav");
    expect(mod.SchoolNav).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// SCH-05 — At-risk alert count shown in header
// ---------------------------------------------------------------------------

describe("SCH-05 — Alert count badge in header", () => {
  beforeEach(() => {
    mockUseQueryOverview.mockReturnValue({ data: MOCK_OVERVIEW, isLoading: false });
  });

  it("shows alert count link when there are unread alerts", () => {
    mockUseQueryAlerts.mockReturnValue({
      data: MOCK_ALERTS_WITH_UNREAD,
      isLoading: false,
    });
    render(<SchoolDashboard />);
    const unread = MOCK_ALERTS_WITH_UNREAD.alerts.filter((a) => !a.acknowledged).length;
    const link = screen.getByRole("link", { name: new RegExp(`${unread} alert`) });
    expect(link).toBeInTheDocument();
    expect(link.getAttribute("href")).toBe(DASHBOARD_HREFS.alerts);
  });

  it("alert count badge shows correct count (2 unread)", () => {
    mockUseQueryAlerts.mockReturnValue({
      data: MOCK_ALERTS_WITH_UNREAD,
      isLoading: false,
    });
    render(<SchoolDashboard />);
    expect(screen.getByText(/2 alerts/)).toBeInTheDocument();
  });

  it("alert link is NOT shown when all alerts are acknowledged", () => {
    mockUseQueryAlerts.mockReturnValue({ data: MOCK_ALERTS_EMPTY, isLoading: false });
    render(<SchoolDashboard />);
    expect(screen.queryByText(/\d+ alert/)).toBeNull();
  });
});
