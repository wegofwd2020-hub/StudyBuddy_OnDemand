/**
 * Unit tests for section 3.10 — Reports Feedback (`/school/reports/feedback`)
 * Covers TC-IDs: SCH-16
 *
 * Run with:
 *   npm test -- feedback-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import FeedbackReportPage from "@/app/(school)/school/reports/feedback/page";
import {
  MOCK_TEACHER,
  MOCK_FEEDBACK_REPORT,
  MOCK_FEEDBACK_EMPTY,
  FEEDBACK_STRINGS,
} from "../e2e/data/feedback-page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// SCH-16 — Student feedback list renders
// ---------------------------------------------------------------------------

describe("SCH-16 — Feedback report renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_REPORT, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<FeedbackReportPage />);
    expect(
      screen.getByRole("heading", { name: FEEDBACK_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders total feedback count", () => {
    const { container } = render(<FeedbackReportPage />);
    // count + " total" is split across nested spans — check textContent
    const match = Array.from(container.querySelectorAll("span")).find((el) =>
      el.textContent?.match(/\d+ total/),
    );
    expect(match).toBeTruthy();
  });

  it("renders unreviewed count badge", () => {
    render(<FeedbackReportPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.unreviewedBadge)).toBeInTheDocument();
  });

  it("renders overall average rating", () => {
    render(<FeedbackReportPage />);
    expect(
      screen.getByText(`${MOCK_FEEDBACK_REPORT.avg_rating_overall!.toFixed(1)} overall`),
    ).toBeInTheDocument();
  });

  it("renders each unit name as a card heading", () => {
    render(<FeedbackReportPage />);
    for (const unit of MOCK_FEEDBACK_REPORT.by_unit) {
      expect(screen.getByText(unit.unit_name!)).toBeInTheDocument();
    }
  });

  it("renders 'Trending' label for trending unit", () => {
    render(<FeedbackReportPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.trendingLabel)).toBeInTheDocument();
  });

  it("renders each feedback message", () => {
    render(<FeedbackReportPage />);
    for (const unit of MOCK_FEEDBACK_REPORT.by_unit) {
      for (const item of unit.feedback_items) {
        expect(screen.getByText(item.message)).toBeInTheDocument();
      }
    }
  });

  it("renders 'No rating' for null-rating feedback", () => {
    render(<FeedbackReportPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.noRatingLabel)).toBeInTheDocument();
  });

  it("renders 'Unreviewed' badge for unreviewed items", () => {
    render(<FeedbackReportPage />);
    const badges = screen.getAllByText(FEEDBACK_STRINGS.unreviewedItemBadge);
    const unreviewedCount = MOCK_FEEDBACK_REPORT.by_unit.flatMap((u) =>
      u.feedback_items.filter((i) => !i.reviewed),
    ).length;
    expect(badges.length).toBe(unreviewedCount);
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<FeedbackReportPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows empty state when no feedback", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_EMPTY, isLoading: false });
    render(<FeedbackReportPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.emptyState)).toBeInTheDocument();
  });
});
