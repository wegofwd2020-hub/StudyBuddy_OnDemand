/**
 * Unit tests for section 3.6 — Reports Trends (`/school/reports/trends`)
 * Covers TC-IDs: SCH-11
 *
 * Run with:
 *   npm test -- trends-report-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TrendsReportPage from "@/app/(school)/school/reports/trends/page";
import {
  MOCK_TEACHER,
  MOCK_TRENDS,
  MOCK_TRENDS_EMPTY,
  TRENDS_STRINGS,
} from "../e2e/data/trends-report-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

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
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

// ---------------------------------------------------------------------------
// SCH-11 — Trends chart renders
// ---------------------------------------------------------------------------

describe("SCH-11 — Trends report renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_TRENDS, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<TrendsReportPage />);
    expect(
      screen.getByRole("heading", { name: TRENDS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders all period toggle buttons", () => {
    render(<TrendsReportPage />);
    expect(
      screen.getByRole("button", { name: TRENDS_STRINGS.period4w }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: TRENDS_STRINGS.period12w }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: TRENDS_STRINGS.periodTerm }),
    ).toBeInTheDocument();
  });

  it("renders the lesson views & active students chart card", () => {
    render(<TrendsReportPage />);
    expect(screen.getByText(TRENDS_STRINGS.lessonViewsCard)).toBeInTheDocument();
  });

  it("renders the pass rate & average score chart card", () => {
    render(<TrendsReportPage />);
    expect(screen.getByText(TRENDS_STRINGS.passRateCard)).toBeInTheDocument();
  });

  it("renders at least one line chart", () => {
    render(<TrendsReportPage />);
    const charts = screen.getAllByTestId("line-chart");
    expect(charts.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Weekly breakdown table heading", () => {
    render(<TrendsReportPage />);
    expect(screen.getByText(TRENDS_STRINGS.weeklyBreakdown)).toBeInTheDocument();
  });

  it("renders all table column headers", () => {
    render(<TrendsReportPage />);
    expect(screen.getByText(TRENDS_STRINGS.colWeek)).toBeInTheDocument();
    expect(screen.getByText(TRENDS_STRINGS.colActive)).toBeInTheDocument();
    expect(screen.getByText(TRENDS_STRINGS.colLessons)).toBeInTheDocument();
    expect(screen.getByText(TRENDS_STRINGS.colQuizzes)).toBeInTheDocument();
    expect(screen.getByText(TRENDS_STRINGS.colAvgScore)).toBeInTheDocument();
    expect(screen.getByText(TRENDS_STRINGS.colPassRate)).toBeInTheDocument();
  });

  it("renders each week_start date in the table", () => {
    render(<TrendsReportPage />);
    for (const w of MOCK_TRENDS.weeks) {
      expect(screen.getByText(w.week_start)).toBeInTheDocument();
    }
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<TrendsReportPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows empty message when no weeks data", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_TRENDS_EMPTY, isLoading: false });
    render(<TrendsReportPage />);
    expect(screen.getByText(TRENDS_STRINGS.noData)).toBeInTheDocument();
  });

  it("clicking a period button changes the active period", () => {
    render(<TrendsReportPage />);
    const btn12w = screen.getByRole("button", { name: TRENDS_STRINGS.period12w });
    fireEvent.click(btn12w);
    expect(btn12w.className).toContain("bg-blue-600");
  });
});
