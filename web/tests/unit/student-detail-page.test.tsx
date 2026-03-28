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
    expect(screen.getByText(String(MOCK_STUDENT_REPORT.units_completed))).toBeInTheDocument();
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
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.timeSpent)).toBeInTheDocument();
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
    expect(screen.getByText(STUDENT_DETAIL_STRINGS.colTime)).toBeInTheDocument();
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

  it("renders best score as red for failed unit", () => {
    const { container } = render(<StudentDetailPage />);
    // Linear Equations: best_score 55, passed false → text-red-500
    const redScore = container.querySelector("span.text-red-500");
    expect(redScore).toBeTruthy();
    expect(redScore!.textContent).toBe("55%");
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
    expect(screen.getByText(MOCK_STUDENT_REPORT.needs_attention_subject!)).toBeInTheDocument();
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
});
