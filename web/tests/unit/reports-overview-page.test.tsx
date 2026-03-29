/**
 * Unit tests for section 3.5 — Reports Overview (`/school/reports/overview`)
 * Covers TC-IDs: SCH-09, SCH-10
 *
 * Run with:
 *   npm test -- reports-overview-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import OverviewReportPage from "@/app/(school)/school/reports/overview/page";
import { SchoolNav } from "@/components/layout/SchoolNav";
import {
  MOCK_TEACHER,
  MOCK_OVERVIEW_REPORT,
  MOCK_OVERVIEW_HEALTHY,
  MOCK_OVERVIEW_LOW_PASS,
  OVERVIEW_STRINGS,
  REPORT_SUBNAV_LABELS,
  REPORT_SUBNAV_HREFS,
} from "../e2e/data/reports-overview-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/school/reports/overview"),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// SCH-09 — Overview report loads: KPI cards visible
// ---------------------------------------------------------------------------

describe("SCH-09 — Overview report KPI cards render", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_OVERVIEW_REPORT, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByRole("heading", { name: OVERVIEW_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders all period toggle buttons", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByRole("button", { name: OVERVIEW_STRINGS.period7d }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: OVERVIEW_STRINGS.period30d }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: OVERVIEW_STRINGS.periodTerm }),
    ).toBeInTheDocument();
  });

  it("renders Enrolled KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.enrolled)).toBeInTheDocument();
  });

  it("renders Enrolled student count", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByText(String(MOCK_OVERVIEW_REPORT.enrolled_students)),
    ).toBeInTheDocument();
  });

  it("renders Active KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.active)).toBeInTheDocument();
  });

  it("renders active percentage value", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByText(`${MOCK_OVERVIEW_REPORT.active_pct.toFixed(0)}%`),
    ).toBeInTheDocument();
  });

  it("renders active student sub-count", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByText(`${MOCK_OVERVIEW_REPORT.active_students_period} students`),
    ).toBeInTheDocument();
  });

  it("renders Lessons viewed KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.lessonsViewed)).toBeInTheDocument();
  });

  it("renders lessons viewed value", () => {
    render(<OverviewReportPage />);
    expect(
      screen.getByText(String(MOCK_OVERVIEW_REPORT.lessons_viewed)),
    ).toBeInTheDocument();
  });

  it("renders Quiz attempts KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.quizAttempts)).toBeInTheDocument();
  });

  it("renders 1st-attempt pass rate KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.passRate)).toBeInTheDocument();
  });

  it("renders pass rate value as green when ≥60%", () => {
    const { container } = render(<OverviewReportPage />);
    const greenVal = container.querySelector("p.text-green-600");
    expect(greenVal).toBeTruthy();
    expect(greenVal!.textContent).toBe(
      `${MOCK_OVERVIEW_REPORT.first_attempt_pass_rate_pct.toFixed(0)}%`,
    );
  });

  it("renders pass rate value as red when <60%", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_OVERVIEW_LOW_PASS, isLoading: false });
    const { container } = render(<OverviewReportPage />);
    const redVal = container.querySelector("p.text-red-500");
    expect(redVal).toBeTruthy();
    expect(redVal!.textContent).toBe(
      `${MOCK_OVERVIEW_LOW_PASS.first_attempt_pass_rate_pct.toFixed(0)}%`,
    );
  });

  it("renders Audio play rate KPI label", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.audioPlayRate)).toBeInTheDocument();
  });

  it("renders Units with struggles section heading", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.unitsWithStruggles)).toBeInTheDocument();
  });

  it("renders each struggling unit as a badge", () => {
    render(<OverviewReportPage />);
    for (const uid of MOCK_OVERVIEW_REPORT.units_with_struggles) {
      expect(screen.getByText(uid)).toBeInTheDocument();
    }
  });

  it("shows 'None — all units healthy.' when no struggles", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_OVERVIEW_HEALTHY, isLoading: false });
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.noStruggles)).toBeInTheDocument();
  });

  it("renders Units with no activity section heading", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.unitsNoActivity)).toBeInTheDocument();
  });

  it("shows 'All units have activity.' when no inactive units", () => {
    render(<OverviewReportPage />);
    expect(screen.getByText(OVERVIEW_STRINGS.allUnitsActive)).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<OverviewReportPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("does not render KPI cards when no data", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    render(<OverviewReportPage />);
    expect(screen.queryByText(OVERVIEW_STRINGS.enrolled)).toBeNull();
  });

  it("clicking a period button changes the active period", () => {
    render(<OverviewReportPage />);
    const btn30d = screen.getByRole("button", { name: OVERVIEW_STRINGS.period30d });
    fireEvent.click(btn30d);
    expect(btn30d.className).toContain("bg-blue-600");
  });
});

// ---------------------------------------------------------------------------
// SCH-10 — Reports sub-nav visible on reports pages
// ---------------------------------------------------------------------------

describe("SCH-10 — Reports sub-nav renders", () => {
  beforeEach(() => {
    // SchoolNav queries alerts; return empty to avoid noise
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("renders all sub-nav links when on a reports route", () => {
    render(<SchoolNav />);
    for (const label of REPORT_SUBNAV_LABELS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("Overview sub-nav link has correct href", () => {
    render(<SchoolNav />);
    const link = screen.getByRole("link", { name: "Overview" });
    expect(link.getAttribute("href")).toBe(REPORT_SUBNAV_HREFS.overview);
  });

  it("Trends sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Trends" }).getAttribute("href")).toBe(
      REPORT_SUBNAV_HREFS.trends,
    );
  });

  it("At-Risk sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "At-Risk" }).getAttribute("href")).toBe(
      REPORT_SUBNAV_HREFS.atRisk,
    );
  });

  it("Unit Performance sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(
      screen.getByRole("link", { name: "Unit Performance" }).getAttribute("href"),
    ).toBe(REPORT_SUBNAV_HREFS.units);
  });

  it("Engagement sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Engagement" }).getAttribute("href")).toBe(
      REPORT_SUBNAV_HREFS.engagement,
    );
  });

  it("Feedback sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Feedback" }).getAttribute("href")).toBe(
      REPORT_SUBNAV_HREFS.feedback,
    );
  });

  it("Export CSV sub-nav link has correct href", () => {
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Export CSV" }).getAttribute("href")).toBe(
      REPORT_SUBNAV_HREFS.exportCsv,
    );
  });

  it("sub-nav is NOT rendered when not on a reports route", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/school/dashboard");
    render(<SchoolNav />);
    expect(screen.queryByRole("link", { name: "At-Risk" })).toBeNull();
  });
});
