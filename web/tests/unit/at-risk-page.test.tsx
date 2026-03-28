/**
 * Unit tests for section 3.7 — Reports At-Risk (`/school/reports/at-risk`)
 * Covers TC-IDs: SCH-12, SCH-13
 *
 * Run with:
 *   npm test -- at-risk-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AtRiskReportPage from "@/app/(school)/school/reports/at-risk/page";
import {
  MOCK_TEACHER,
  MOCK_CURRICULUM_HEALTH,
  MOCK_CURRICULUM_ALL_HEALTHY,
  AT_RISK_STRINGS,
} from "../e2e/data/at-risk-page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// SCH-12 — At-risk student table renders
// ---------------------------------------------------------------------------

describe("SCH-12 — At-risk report renders with struggling/watch units", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_CURRICULUM_HEALTH, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<AtRiskReportPage />);
    expect(
      screen.getByRole("heading", { name: AT_RISK_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the Healthy tier count card", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.healthy)).toBeInTheDocument();
    expect(screen.getByText(String(MOCK_CURRICULUM_HEALTH.healthy_count))).toBeInTheDocument();
  });

  it("renders the Watch tier count card", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.watch)).toBeInTheDocument();
  });

  it("renders the Struggling tier count card", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.struggling)).toBeInTheDocument();
  });

  it("renders the No activity tier count card", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.noActivity)).toBeInTheDocument();
  });

  it("renders the Struggling units section", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.strugglingCard)).toBeInTheDocument();
  });

  it("renders the Units to watch section", () => {
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.watchCard)).toBeInTheDocument();
  });

  it("renders struggling unit name in the table", () => {
    render(<AtRiskReportPage />);
    const struggling = MOCK_CURRICULUM_HEALTH.units.find((u) => u.health_tier === "struggling")!;
    expect(screen.getByText(struggling.unit_name!)).toBeInTheDocument();
  });

  it("renders struggling unit pass rate in red", () => {
    const { container } = render(<AtRiskReportPage />);
    const redCell = container.querySelector("td.text-red-600");
    expect(redCell).toBeTruthy();
  });

  it("renders recommended action for struggling unit", () => {
    render(<AtRiskReportPage />);
    const struggling = MOCK_CURRICULUM_HEALTH.units.find((u) => u.health_tier === "struggling")!;
    expect(screen.getByText(struggling.recommended_action)).toBeInTheDocument();
  });

  it("renders watch unit name in the watch table", () => {
    render(<AtRiskReportPage />);
    const watchUnit = MOCK_CURRICULUM_HEALTH.units.find((u) => u.health_tier === "watch")!;
    expect(screen.getByText(watchUnit.unit_name!)).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<AtRiskReportPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// SCH-13 — Empty state if no at-risk students
// ---------------------------------------------------------------------------

describe("SCH-13 — Empty state when all units are healthy", () => {
  it("shows 'No at-risk units' message when no struggling or watch units", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_CURRICULUM_ALL_HEALTHY, isLoading: false });
    render(<AtRiskReportPage />);
    expect(screen.getByText(AT_RISK_STRINGS.allHealthy)).toBeInTheDocument();
  });

  it("does not render struggling table when all healthy", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_CURRICULUM_ALL_HEALTHY, isLoading: false });
    render(<AtRiskReportPage />);
    expect(screen.queryByText(AT_RISK_STRINGS.strugglingCard)).toBeNull();
  });
});
