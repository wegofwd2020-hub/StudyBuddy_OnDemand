/**
 * Engagement report parity with the dashboard (#770).
 *
 * The report was bespoke markup predating the #640 dashboard redesign, and had
 * drifted from it in the three ways a reader actually notices: no period
 * selector (the window was hardcoded in prose), no scope note (so a teacher
 * could not tell whether the figures were their grades or the school), and
 * hand-rolled cards instead of the shared `KpiCard`.
 *
 * These tests pin the first two as behaviour. The third is structural and is
 * covered by the fact that `KpiCard` now has exactly one definition — a test
 * asserting "this markup came from that component" would pin the implementation
 * rather than anything a user can observe.
 *
 * Run with:
 *   npm test -- engagement-report-770
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import EngagementReportPage from "@/app/(school)/school/reports/engagement/page";

const mockGetOverviewReport = vi.fn();
const mockGetCurriculumHealth = vi.fn();

vi.mock("@/lib/api/reports", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reports")>();
  return {
    ...actual,
    getOverviewReport: (...args: unknown[]) => mockGetOverviewReport(...args),
    getCurriculumHealth: (...args: unknown[]) => mockGetCurriculumHealth(...args),
  };
});

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: () => ({ school_id: "school-1", role: "teacher" }),
}));

const OVERVIEW = {
  enrolled_students: 40,
  active_students_period: 10,
  active_pct: 25,
  audio_play_rate_pct: 12,
  scope: { kind: "teacher", grades: [11] },
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <EngagementReportPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetOverviewReport.mockResolvedValue(OVERVIEW);
  mockGetCurriculumHealth.mockResolvedValue({ units: [] });
});

describe("Engagement report (#770)", () => {
  it("offers the same three reporting windows as the dashboard", async () => {
    renderPage();
    await waitFor(() => expect(mockGetOverviewReport).toHaveBeenCalled());

    for (const label of ["Last 7 days", "Last 30 days", "This term"]) {
      expect(screen.getByRole("button", { name: label })).toBeTruthy();
    }
  });

  it("defaults to 30 days and refetches when the window changes", async () => {
    renderPage();
    await waitFor(() =>
      expect(mockGetOverviewReport).toHaveBeenCalledWith("school-1", "30d"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Last 7 days" }));

    // The window is a real query parameter, not a caption: the figures must be
    // re-fetched for it. Hardcoding "Last 30 days" in prose was the defect.
    await waitFor(() =>
      expect(mockGetOverviewReport).toHaveBeenCalledWith("school-1", "7d"),
    );
  });

  it("restates the chosen window in the body copy", async () => {
    const { container } = renderPage();
    await waitFor(() => expect(mockGetOverviewReport).toHaveBeenCalled());

    expect(container.textContent).toContain("Showing the last 30 days");

    fireEvent.click(screen.getByRole("button", { name: "This term" }));
    await waitFor(() => expect(container.textContent).toContain("Showing this term"));
  });

  it("says WHO the figures cover, not only when", async () => {
    const { container } = renderPage();
    await waitFor(() => expect(mockGetOverviewReport).toHaveBeenCalled());

    // ScopeNote derives its wording from `scope.grades`, not from any label the
    // API sends. A teacher seeing school-wide numbers and assuming they were
    // their own is the defect #640 was reported for.
    await waitFor(() => expect(container.textContent).toContain("Your grades: 11"));
  });

  it("counts inactive students against the selected window's wording", async () => {
    const { container } = renderPage();
    await waitFor(() => expect(mockGetOverviewReport).toHaveBeenCalled());

    // 40 enrolled, 10 active.
    await waitFor(() => expect(container.textContent).toContain("30"));
    expect(container.textContent).toContain("had no activity in the last 30 days");
  });
});
