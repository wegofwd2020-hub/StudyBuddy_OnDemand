/**
 * Unit tests for section 3.10 — Reports Feedback (`/school/reports/feedback`)
 * Covers TC-IDs: SCH-16
 *
 * Run with:
 *   npm test -- feedback-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
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

  it("renders a table with the reviewer's columns", () => {
    render(<FeedbackReportPage />);
    for (const col of [
      FEEDBACK_STRINGS.colUnit,
      FEEDBACK_STRINGS.colVerdict,
      FEEDBACK_STRINGS.colComment,
    ]) {
      expect(screen.getByRole("columnheader", { name: col })).toBeInTheDocument();
    }
  });

  it("renders one row per feedback item", () => {
    render(<FeedbackReportPage />);
    // +1 for the header row.
    expect(screen.getAllByRole("row")).toHaveLength(
      MOCK_FEEDBACK_REPORT.items.length + 1,
    );
  });

  it("names the unit each item belongs to", () => {
    render(<FeedbackReportPage />);
    for (const name of new Set(MOCK_FEEDBACK_REPORT.items.map((i) => i.unit_name!))) {
      expect(screen.getAllByText(name).length).toBeGreaterThan(0);
    }
  });

  it("renders each feedback message", () => {
    render(<FeedbackReportPage />);
    for (const item of MOCK_FEEDBACK_REPORT.items) {
      if (item.message) expect(screen.getByText(item.message)).toBeInTheDocument();
    }
  });

  it("shows the thumbs verdict, which is what a thumbs row carries", () => {
    render(<FeedbackReportPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.notHelpful)).toBeInTheDocument();
  });

  it("renders 'Unreviewed' badge for unreviewed items", () => {
    render(<FeedbackReportPage />);
    // Scope to the table: a filter chip carries the same label.
    const table = screen.getByRole("table");
    const badges = within(table).getAllByText(FEEDBACK_STRINGS.unreviewedItemBadge);
    const unreviewed = MOCK_FEEDBACK_REPORT.items.filter((i) => !i.reviewed).length;
    expect(badges.length).toBe(unreviewed);
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
