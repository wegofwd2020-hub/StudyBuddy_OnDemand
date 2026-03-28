/**
 * Unit tests for section 3.9 — Reports Engagement (`/school/reports/engagement`)
 * Covers TC-IDs: SCH-15
 *
 * Run with:
 *   npm test -- engagement-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import EngagementReportPage from "@/app/(school)/school/reports/engagement/page";
import {
  MOCK_TEACHER,
  MOCK_OVERVIEW_30D,
  MOCK_OVERVIEW_FULL_ACTIVE,
  MOCK_HEALTH_WITH_NO_ACTIVITY,
  MOCK_HEALTH_ALL_ACTIVE,
  ENGAGEMENT_STRINGS,
} from "../e2e/data/engagement-page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn(({ queryKey }: { queryKey: unknown[] }) => {
      // Dispatch by queryKey[0]
      if (Array.isArray(queryKey) && queryKey[0] === "report-overview") {
        return mockUseQueryOverview();
      }
      if (Array.isArray(queryKey) && queryKey[0] === "curriculum-health") {
        return mockUseQueryHealth();
      }
      return { data: undefined, isLoading: false };
    }),
  };
});

const mockUseQueryOverview = vi.fn();
const mockUseQueryHealth   = vi.fn();

// ---------------------------------------------------------------------------
// SCH-15 — Engagement metrics render
// ---------------------------------------------------------------------------

describe("SCH-15 — Engagement report renders", () => {
  beforeEach(() => {
    mockUseQueryOverview.mockReturnValue({ data: MOCK_OVERVIEW_30D, isLoading: false });
    mockUseQueryHealth.mockReturnValue({ data: MOCK_HEALTH_ALL_ACTIVE, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<EngagementReportPage />);
    expect(
      screen.getByRole("heading", { name: ENGAGEMENT_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders 'Last 30 days' period label", () => {
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.period30d)).toBeInTheDocument();
  });

  it("renders Active students KPI card", () => {
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.activeStudents)).toBeInTheDocument();
  });

  it("renders active student count", () => {
    render(<EngagementReportPage />);
    expect(
      screen.getByText(String(MOCK_OVERVIEW_30D.active_students_period)),
    ).toBeInTheDocument();
  });

  it("renders enrolled student sub-count", () => {
    render(<EngagementReportPage />);
    expect(
      screen.getByText(`of ${MOCK_OVERVIEW_30D.enrolled_students} enrolled`),
    ).toBeInTheDocument();
  });

  it("renders Activity rate KPI card", () => {
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.activityRate)).toBeInTheDocument();
  });

  it("renders activity rate percentage", () => {
    render(<EngagementReportPage />);
    expect(
      screen.getByText(`${MOCK_OVERVIEW_30D.active_pct.toFixed(0)}%`),
    ).toBeInTheDocument();
  });

  it("renders Audio engagement KPI card", () => {
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.audioEngagement)).toBeInTheDocument();
  });

  it("renders audio play rate percentage", () => {
    render(<EngagementReportPage />);
    expect(
      screen.getByText(`${MOCK_OVERVIEW_30D.audio_play_rate_pct.toFixed(0)}%`),
    ).toBeInTheDocument();
  });

  it("shows Inactive students card when active_pct < 100", () => {
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.inactiveStudents)).toBeInTheDocument();
    const inactive = MOCK_OVERVIEW_30D.enrolled_students - MOCK_OVERVIEW_30D.active_students_period;
    expect(screen.getByText(String(inactive))).toBeInTheDocument();
  });

  it("does NOT show Inactive students card when all students are active", () => {
    mockUseQueryOverview.mockReturnValue({ data: MOCK_OVERVIEW_FULL_ACTIVE, isLoading: false });
    render(<EngagementReportPage />);
    expect(screen.queryByText(ENGAGEMENT_STRINGS.inactiveStudents)).toBeNull();
  });

  it("shows Units with zero activity card when dropout-risk units exist", () => {
    mockUseQueryHealth.mockReturnValue({ data: MOCK_HEALTH_WITH_NO_ACTIVITY, isLoading: false });
    render(<EngagementReportPage />);
    expect(screen.getByText(ENGAGEMENT_STRINGS.zeroActivityCard)).toBeInTheDocument();
  });

  it("does NOT show Units with zero activity when none", () => {
    render(<EngagementReportPage />);
    expect(screen.queryByText(ENGAGEMENT_STRINGS.zeroActivityCard)).toBeNull();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQueryOverview.mockReturnValue({ data: undefined, isLoading: true });
    mockUseQueryHealth.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<EngagementReportPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });
});
