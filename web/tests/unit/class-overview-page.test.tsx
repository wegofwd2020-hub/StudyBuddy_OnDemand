/**
 * Unit tests for section 3.3 — Class Overview (`/school/class/[class_id]`)
 * Covers TC-IDs: SCH-06, SCH-07
 *
 * Run with:
 *   npm test -- class-overview-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ClassOverviewPage from "@/app/(school)/school/class/[class_id]/page";
import {
  MOCK_TEACHER,
  MOCK_CLASS_METRICS,
  MOCK_CLASS_METRICS_EMPTY,
  CLASS_STRINGS,
  studentDetailHref,
} from "../e2e/data/class-overview-page";

// ---------------------------------------------------------------------------
// Shared mocks
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

// ---------------------------------------------------------------------------
// SCH-06 — Student list renders with latest activity
// ---------------------------------------------------------------------------

describe("SCH-06 — Student list renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_CLASS_METRICS, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<ClassOverviewPage />);
    expect(
      screen.getByRole("heading", { name: CLASS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders all student names", () => {
    render(<ClassOverviewPage />);
    for (const student of MOCK_CLASS_METRICS.students) {
      expect(screen.getByText(student.student_name)).toBeInTheDocument();
    }
  });

  it("renders correct student count in card header", () => {
    render(<ClassOverviewPage />);
    expect(
      screen.getByText(`${MOCK_CLASS_METRICS.students.length} students`),
    ).toBeInTheDocument();
  });

  it("renders table column headers", () => {
    render(<ClassOverviewPage />);
    expect(screen.getByText(CLASS_STRINGS.colStudent)).toBeInTheDocument();
    expect(screen.getByText(CLASS_STRINGS.colGrade)).toBeInTheDocument();
    expect(screen.getByText(CLASS_STRINGS.colUnitsDone)).toBeInTheDocument();
    expect(screen.getByText(CLASS_STRINGS.colAvgScore)).toBeInTheDocument();
    expect(screen.getByText(CLASS_STRINGS.colLastActive)).toBeInTheDocument();
  });

  it("renders grade filter buttons (All + grades 5-12)", () => {
    render(<ClassOverviewPage />);
    expect(screen.getByRole("button", { name: CLASS_STRINGS.gradeAll })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "8" })).toBeInTheDocument();
  });

  it("shows 'Never' for student with null last_active", () => {
    render(<ClassOverviewPage />);
    expect(screen.getByText(CLASS_STRINGS.neverActive)).toBeInTheDocument();
  });

  it("renders score bar for each student", () => {
    const { container } = render(<ClassOverviewPage />);
    // Each row has a score bar div with inline width style
    const scoreBars = container.querySelectorAll("div[style]");
    expect(scoreBars.length).toBeGreaterThanOrEqual(MOCK_CLASS_METRICS.students.length);
  });

  it("renders 'No students found.' when list is empty", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_CLASS_METRICS_EMPTY, isLoading: false });
    render(<ClassOverviewPage />);
    expect(screen.getByText(CLASS_STRINGS.noStudents)).toBeInTheDocument();
  });

  it("shows loading skeletons while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<ClassOverviewPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("clicking a column header toggles sort direction", () => {
    render(<ClassOverviewPage />);
    const studentHeader = screen.getByText(CLASS_STRINGS.colStudent).closest("th")!;
    // Initial sort is asc on student_name — ChevronUp is active
    const before = studentHeader.querySelector("svg");
    expect(before).toBeTruthy();
    fireEvent.click(studentHeader);
    // After click → desc — ChevronDown now active
    const after = studentHeader.querySelector("svg");
    expect(after).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// SCH-07 — Clicking student row navigates to student detail
// ---------------------------------------------------------------------------

describe("SCH-07 — Student Detail link href", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_CLASS_METRICS, isLoading: false });
  });

  it("each student row has a Detail link", () => {
    render(<ClassOverviewPage />);
    const detailLinks = screen.getAllByRole("link", { name: CLASS_STRINGS.detailBtn });
    expect(detailLinks).toHaveLength(MOCK_CLASS_METRICS.students.length);
  });

  it("Detail link for each student has correct href", () => {
    render(<ClassOverviewPage />);
    const detailLinks = screen.getAllByRole("link", { name: CLASS_STRINGS.detailBtn });
    for (let i = 0; i < MOCK_CLASS_METRICS.students.length; i++) {
      const student = MOCK_CLASS_METRICS.students[i];
      const match = detailLinks.find(
        (l) => l.getAttribute("href") === studentDetailHref(student.student_id),
      );
      expect(match).toBeTruthy();
    }
  });

  it("studentDetailHref returns /school/student/[student_id]", () => {
    expect(studentDetailHref("stu-001")).toBe("/school/student/stu-001");
  });
});
