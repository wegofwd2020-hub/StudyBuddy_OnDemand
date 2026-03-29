/**
 * Unit tests for section 2.9 — Stats Page (`/stats`)
 * Covers TC-IDs: STU-31
 *
 * Run with:
 *   npm test -- stats-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import StatsPage from "@/app/(student)/stats/page";
import {
  MOCK_STUDENT_STATS,
  MOCK_STUDENT_STATS_ZERO,
  STATS_STRINGS,
  PERIOD_LABELS,
} from "../e2e/data/stats-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/student/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

// Recharts uses ResizeObserver — stub it for jsdom
vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Cell: () => null,
}));

const mockUseStudentStats = vi.fn();
vi.mock("@/lib/hooks/useStats", () => ({
  useStudentStats: (period: string) => mockUseStudentStats(period),
}));

// ---------------------------------------------------------------------------
// STU-31 — Stats page: streak, total sessions, subject breakdown visible
// ---------------------------------------------------------------------------

describe("STU-31 — Stats page renders", () => {
  beforeEach(() => {
    mockUseStudentStats.mockReturnValue({ data: MOCK_STUDENT_STATS, isLoading: false });
  });

  it("renders the page title", () => {
    render(<StatsPage />);
    expect(
      screen.getByRole("heading", { name: STATS_STRINGS.title }),
    ).toBeInTheDocument();
  });

  it("renders all three period selector buttons", () => {
    render(<StatsPage />);
    for (const label of PERIOD_LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("'Last 30 days' is active by default", () => {
    render(<StatsPage />);
    const btn = screen.getByRole("button", { name: "Last 30 days" });
    expect(btn.className).toContain("bg-blue-600");
  });

  it("clicking a period button switches the active selection", () => {
    render(<StatsPage />);
    const btn7d = screen.getByRole("button", { name: "Last 7 days" });
    fireEvent.click(btn7d);
    expect(btn7d.className).toContain("bg-blue-600");
  });

  it("renders streak day count", () => {
    render(<StatsPage />);
    expect(screen.getByText(String(MOCK_STUDENT_STATS.streak_days))).toBeInTheDocument();
  });

  it("renders lessons_viewed stat card label", () => {
    render(<StatsPage />);
    expect(screen.getByText(STATS_STRINGS.lessonsViewed)).toBeInTheDocument();
  });

  it("renders lessons_viewed value", () => {
    render(<StatsPage />);
    expect(
      screen.getByText(String(MOCK_STUDENT_STATS.lessons_viewed)),
    ).toBeInTheDocument();
  });

  it("renders quizzes_completed stat card label", () => {
    render(<StatsPage />);
    expect(screen.getByText(STATS_STRINGS.quizzesCompleted)).toBeInTheDocument();
  });

  it("renders quizzes_completed value", () => {
    render(<StatsPage />);
    expect(
      screen.getByText(String(MOCK_STUDENT_STATS.quizzes_completed)),
    ).toBeInTheDocument();
  });

  it("renders pass_rate as a percentage", () => {
    render(<StatsPage />);
    const pct = `${Math.round(MOCK_STUDENT_STATS.pass_rate * 100)}%`;
    expect(screen.getByText(pct)).toBeInTheDocument();
  });

  it("renders avg_score as a percentage", () => {
    render(<StatsPage />);
    const pct = `${Math.round(MOCK_STUDENT_STATS.avg_score * 100)}%`;
    expect(screen.getByText(pct)).toBeInTheDocument();
  });

  it("renders audio_sessions value", () => {
    render(<StatsPage />);
    expect(
      screen.getByText(String(MOCK_STUDENT_STATS.audio_sessions)),
    ).toBeInTheDocument();
  });

  it("renders Subject Breakdown heading when breakdown is non-empty", () => {
    render(<StatsPage />);
    expect(
      screen.getByRole("heading", { name: STATS_STRINGS.subjectBreakdown }),
    ).toBeInTheDocument();
  });

  it("renders bar chart when breakdown is non-empty", () => {
    render(<StatsPage />);
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("does not render Subject Breakdown section when breakdown is empty", () => {
    mockUseStudentStats.mockReturnValue({
      data: MOCK_STUDENT_STATS_ZERO,
      isLoading: false,
    });
    render(<StatsPage />);
    expect(
      screen.queryByRole("heading", { name: STATS_STRINGS.subjectBreakdown }),
    ).toBeNull();
  });

  it("shows loading skeletons while fetching", () => {
    mockUseStudentStats.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<StatsPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("useStudentStats is called with default period '30d'", () => {
    render(<StatsPage />);
    expect(mockUseStudentStats).toHaveBeenCalledWith("30d");
  });

  it("useStudentStats is called with '7d' after clicking Last 7 days", () => {
    render(<StatsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Last 7 days" }));
    expect(mockUseStudentStats).toHaveBeenCalledWith("7d");
  });

  it("useStudentStats is called with 'all' after clicking All time", () => {
    render(<StatsPage />);
    fireEvent.click(screen.getByRole("button", { name: "All time" }));
    expect(mockUseStudentStats).toHaveBeenCalledWith("all");
  });
});
