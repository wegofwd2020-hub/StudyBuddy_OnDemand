/**
 * Unit tests for section 3.8 — Reports Unit Performance (`/school/reports/units`)
 * Covers TC-IDs: SCH-14
 *
 * Run with:
 *   npm test -- unit-performance-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import UnitPerformancePage from "@/app/(school)/school/reports/units/page";
import {
  MOCK_TEACHER,
  MOCK_HEALTH,
  MOCK_HEALTH_NO_ACTIVITY,
  UNIT_PERF_STRINGS,
} from "../e2e/data/unit-performance-page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// ---------------------------------------------------------------------------
// SCH-14 — Unit performance chart renders
// ---------------------------------------------------------------------------

describe("SCH-14 — Unit performance page renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_HEALTH, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<UnitPerformancePage />);
    expect(
      screen.getByRole("heading", { name: UNIT_PERF_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the pass rate chart card", () => {
    render(<UnitPerformancePage />);
    expect(screen.getByText(UNIT_PERF_STRINGS.chartCard)).toBeInTheDocument();
  });

  it("renders a bar chart", () => {
    render(<UnitPerformancePage />);
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders the All units table card", () => {
    render(<UnitPerformancePage />);
    expect(screen.getByText(UNIT_PERF_STRINGS.allUnitsCard)).toBeInTheDocument();
  });

  it("renders all table column headers", () => {
    render(<UnitPerformancePage />);
    expect(screen.getByText(UNIT_PERF_STRINGS.colUnit)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.colSubject)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.colPassRate)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.colAvgScore)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.colAvgAttempts)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.colFeedback)).toBeInTheDocument();
  });

  it("renders each unit name in the table", () => {
    render(<UnitPerformancePage />);
    for (const unit of MOCK_HEALTH.units) {
      expect(screen.getByText(unit.unit_name!)).toBeInTheDocument();
    }
  });

  it("renders pass rate colored red for struggling unit (<50%)", () => {
    const { container } = render(<UnitPerformancePage />);
    const redSpan = container.querySelector("span.text-red-500");
    expect(redSpan).toBeTruthy();
    expect(redSpan!.textContent).toContain("38");
  });

  it("renders pass rate colored green for healthy unit (≥70%)", () => {
    const { container } = render(<UnitPerformancePage />);
    const greenSpan = container.querySelector("span.text-green-600");
    expect(greenSpan).toBeTruthy();
  });

  it("renders chart legend labels", () => {
    render(<UnitPerformancePage />);
    expect(screen.getByText(UNIT_PERF_STRINGS.legendHealthy)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.legendWatch)).toBeInTheDocument();
    expect(screen.getByText(UNIT_PERF_STRINGS.legendStruggling)).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<UnitPerformancePage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows empty message when all units have no activity", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_HEALTH_NO_ACTIVITY, isLoading: false });
    render(<UnitPerformancePage />);
    expect(screen.getByText(UNIT_PERF_STRINGS.noActivity)).toBeInTheDocument();
  });
});
