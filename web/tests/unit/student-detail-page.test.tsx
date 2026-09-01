/**
 * Unit tests for section 3.4 — Student Detail (`/school/student/[student_id]`)
 * Covers TC-IDs: SCH-08
 *
 * Run with:
 *   npm test -- student-detail-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import StudentDetailPage from "@/app/(school)/school/student/[student_id]/page";
import {
  MOCK_TEACHER,
  MOCK_STUDENT_ID,
  MOCK_STUDENT_REPORT,
  STUDENT_DETAIL_STRINGS,
  BACK_HREF,
} from "../e2e/data/student-detail-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ student_id: MOCK_STUDENT_ID })),
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
// SCH-08 — Student detail page renders correctly
// ---------------------------------------------------------------------------

describe("SCH-08 — Student detail page", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_STUDENT_REPORT, isLoading: false });
  });

  it("renders the student name as heading", () => {
    render(<StudentDetailPage />);
    expect(
      screen.getByRole("heading", { name: MOCK_STUDENT_REPORT.student_name }),
    ).toBeInTheDocument();
  });

  it("renders grade badge", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(`Grade ${MOCK_STUDENT_REPORT.grade}`)).toBeInTheDocument();
  });

  it("renders back button with correct href", () => {
    render(<StudentDetailPage />);
    const backLink = screen.getByRole("link", { name: STUDENT_DETAIL_STRINGS.backBtn });
    expect(backLink.getAttribute("href")).toBe(BACK_HREF);
  });

  it("renders Units completed KPI label", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.unitsCompleted)).toBeInTheDocument();
  });

  it("renders Units completed value", () => {
    render(<StudentDetailPage />);
    expect(
      screen.getByText(String(MOCK_STUDENT_REPORT.units_completed)),
    ).toBeInTheDocument();
  });

  it("renders In progress KPI label", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.inProgress)).toBeInTheDocument();
  });

  it("renders In progress value", () => {
    render(<StudentDetailPage />);
    // units_in_progress = 2; quiz_attempts also has 2 — use getAllByText
    const matches = screen.getAllByText(String(MOCK_STUDENT_REPORT.units_in_progress));
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Pass rate KPI label", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.passRate)).toBeInTheDocument();
  });

  it("renders Pass rate value as percentage", () => {
    render(<StudentDetailPage />);
    expect(
      screen.getByText(`${MOCK_STUDENT_REPORT.first_attempt_pass_rate_pct.toFixed(0)}%`),
    ).toBeInTheDocument();
  });

  it("renders Time spent KPI label", () => {
    render(<StudentDetailPage />);
    // "Reading time" now appears TWICE on purpose: on the tile (a total) and as
    // the column header (the same quantity per unit, which sums to the tile).
    // getByText would throw on the ambiguity, so this asserts both exist rather
    // than pretending only one does.
    expect(screen.getAllByText(STUDENT_DETAIL_STRINGS.timeSpent)).toHaveLength(2);
  });

  it("renders Time spent formatted as 2h 0m", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.twoHours)).toBeInTheDocument();
  });

  it("renders Unit progress card heading", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.unitProgressCard)).toBeInTheDocument();
  });

  it("renders all table column headers", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colUnit)).toBeInTheDocument();
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colSubject)).toBeInTheDocument();
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colLesson)).toBeInTheDocument();
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colAttempts)).toBeInTheDocument();
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colBestScore)).toBeInTheDocument();
    // Shares its text with the tile above (see the KPI label test), so this
    // looks for the header cell specifically rather than any matching node.
    expect(
      screen.getByRole("columnheader", { name: STUDENT_DETAIL_STRINGS.colTime }),
    ).toBeInTheDocument();
  });

  it("renders each unit name in the table", () => {
    render(<StudentDetailPage />);
    for (const unit of MOCK_STUDENT_REPORT.per_unit) {
      expect(screen.getByText(unit.unit_name!)).toBeInTheDocument();
    }
  });

  it("renders subject values (capitalized) in the table", () => {
    render(<StudentDetailPage />);
    // science × 2, mathematics × 1
    const scienceCells = screen.getAllByText("science");
    expect(scienceCells.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("mathematics")).toBeInTheDocument();
  });

  it("renders best score as green for passed unit", () => {
    const { container } = render(<StudentDetailPage />);
    // Cell Biology: best_score 90, passed true → text-green-600
    const greenScore = container.querySelector("span.text-green-600");
    expect(greenScore).toBeTruthy();
    expect(greenScore!.textContent).toBe("90%");
  });

  it("renders best score in the needs-attention colour for a failed unit", () => {
    const { container } = render(<StudentDetailPage />);
    // Linear Equations: best_score 55, passed false.
    //
    // This asserted `text-red-500` until 2026-09-01. Two reasons it is now
    // `text-orange-700`:
    //
    //   1. It matches the "Needs attention" chip above the table, so the legend
    //      and the rows it describes use one colour for one meaning. A tester
    //      reported exactly that disconnect.
    //   2. red-500 measures 3.76:1 on white — BELOW the 4.5:1 WCAG AA floor this
    //      project targets. orange-700 is 5.18:1. (orange-600 would also have
    //      failed at 3.56:1, so the shade was measured, not eyeballed.)
    const flagged = container.querySelector("span.text-orange-700");
    expect(flagged).toBeTruthy();
    expect(flagged!.textContent).toContain("55%");
  });

  it("renders em-dash for unit with no attempts (no best score)", () => {
    render(<StudentDetailPage />);
    // Chemical Reactions: best_score null → "—"
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders Strongest subject tag", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("Strongest:")).toBeInTheDocument();
    expect(screen.getByText(MOCK_STUDENT_REPORT.strongest_subject!)).toBeInTheDocument();
  });

  it("renders Needs attention subject tag", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("Needs attention:")).toBeInTheDocument();
    expect(
      screen.getByText(MOCK_STUDENT_REPORT.needs_attention_subject!),
    ).toBeInTheDocument();
  });

  it("shows loading heading when isLoading is true", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    render(<StudentDetailPage />);
    expect(screen.getByRole("heading", { name: "Loading…" })).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<StudentDetailPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows fallback heading when no data and not loading", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    render(<StudentDetailPage />);
    expect(screen.getByRole("heading", { name: "Student Detail" })).toBeInTheDocument();
  });

  it("does not render KPI cards or table when no data", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });
    render(<StudentDetailPage />);
    expect(screen.queryByText(STUDENT_DETAIL_STRINGS.unitsCompleted)).toBeNull();
    expect(screen.queryByText(STUDENT_DETAIL_STRINGS.unitProgressCard)).toBeNull();
  });

  // ── Every tile says what it counts ─────────────────────────────────────────
  //
  // A tester compared this card with the student's own My Stats page and found
  // 43% here against 65% there for the same child on the same afternoon, and
  // reported a data bug. Both numbers were right — this one counts first
  // attempts, that one counts every attempt — and neither screen said so.
  //
  // These are label assertions, which regress silently and invisibly: nothing
  // breaks when a qualifier is dropped, the number just starts lying by omission
  // again. That is precisely why they are worth pinning.

  it("says the pass rate counts first attempts only", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("First attempt only")).toBeInTheDocument();
  });

  it("says what In progress includes, answering whether Needs Retry counts", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("Reached, not yet passed")).toBeInTheDocument();
  });

  it("says Units completed means the quiz was passed", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("Quiz passed")).toBeInTheDocument();
  });

  it("ties the Reading time tile to the column beneath it", () => {
    render(<StudentDetailPage />);
    expect(screen.getByText("Total of the column below")).toBeInTheDocument();
  });

  // ── The legend and the rows speak one language ─────────────────────────────
  //
  // A tester read the Lesson column's bare green tick as a health marker and
  // asked why low-scoring rows carried no warning there. Fair reading: the tick
  // was unlabelled, and the same tick was also the "Strongest" chip's icon and
  // the app-wide "done" mark. One glyph, three classes of meaning.

  it("marks a unit that was not passed with the needs-attention icon", () => {
    render(<StudentDetailPage />);
    // Fixture: G8-MATH-001 scored 55% and did NOT pass.
    expect(screen.getAllByLabelText("Needs attention").length).toBeGreaterThan(0);
  });

  it("drives the marker off `passed`, not a hardcoded 50%", () => {
    // The tester asked for the marker "where the best score is <= 50%". A fixed
    // threshold would be wrong: pass marks are per-school (ADR-007), so it would
    // flag units a school considers passed and miss ones it does not.
    //
    // The fixture proves which rule ran. G8-MATH-001 scored 55% — ABOVE 50 — and
    // did not pass. A 50% rule leaves it unmarked; `passed` marks it.
    render(<StudentDetailPage />);
    const marked = screen.getAllByLabelText("Needs attention");
    expect(marked).toHaveLength(1);
    const row = marked[0].closest("tr");
    expect(row).not.toBeNull();
    expect(row!.textContent).toContain("55%");
    expect(row!.textContent).toContain("Linear Equations");
  });

  it("does not mark a unit that was passed", () => {
    // The negative direction. A marker rendered on every row would satisfy the
    // test above while telling a teacher nothing.
    render(<StudentDetailPage />);
    const passedRow = screen.getByText("Cell Biology").closest("tr");
    expect(passedRow!.querySelector("[aria-label='Needs attention']")).toBeNull();
  });

  it("does not mark a unit that has no score yet", () => {
    // Never attempted is not the same as failed, and saying so would send a
    // teacher after a student who has simply not started.
    render(<StudentDetailPage />);
    const noScoreRow = screen.getByText("Chemical Reactions").closest("tr");
    expect(noScoreRow!.querySelector("[aria-label='Needs attention']")).toBeNull();
  });

  it("labels the Lesson column icons instead of leaving them bare", () => {
    render(<StudentDetailPage />);
    expect(screen.getAllByLabelText("Lesson opened").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Lesson not opened").length).toBeGreaterThan(0);
  });

  it("renders per-unit reading time from total_duration_s", () => {
    // Guards the #717 rename at the seam it actually broke. `tests/**` is
    // EXCLUDED from tsconfig, so the fixture's `: StudentReport` annotation is
    // never checked — the rename left `avg_duration_s` in the fixture and the
    // page read `undefined` with nothing failing to typecheck.
    render(<StudentDetailPage />);
    // 1200s and 900s from the fixture; 0s renders as a plain "0m".
    expect(screen.getByText("20m")).toBeInTheDocument();
    expect(screen.getByText("15m")).toBeInTheDocument();
    expect(screen.queryByText("NaNm")).toBeNull();
  });
});
