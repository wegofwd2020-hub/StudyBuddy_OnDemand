/**
 * Unit tests for section 3.11 — Reports Export CSV (`/school/reports/export`)
 * Covers TC-IDs: SCH-17, SCH-18
 *
 * Run with:
 *   npm test -- export-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ExportPage from "@/app/(school)/school/reports/export/page";
import { MOCK_TEACHER, EXPORT_STRINGS } from "../e2e/data/export-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockGetOverviewReport = vi.fn();
const mockGetTrendsReport = vi.fn();
const mockGetCurriculumHealth = vi.fn();

vi.mock("@/lib/api/reports", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reports")>();
  return {
    ...actual,
    getOverviewReport: (...args: unknown[]) => mockGetOverviewReport(...args),
    getTrendsReport: (...args: unknown[]) => mockGetTrendsReport(...args),
    getCurriculumHealth: (...args: unknown[]) => mockGetCurriculumHealth(...args),
  };
});

// Mock papaparse
vi.mock("papaparse", () => ({
  default: { unparse: vi.fn(() => "col1,col2\nval1,val2") },
}));

// Mock URL and anchor (jsdom doesn't support createObjectURL)
const mockClick = vi.fn();
vi.stubGlobal("URL", {
  createObjectURL: vi.fn(() => "blob:mock-url"),
  revokeObjectURL: vi.fn(),
});

// Capture the original before spying to avoid infinite recursion
const _originalCreateElement = document.createElement.bind(document);
const mockCreateElement = vi.spyOn(document, "createElement");

beforeEach(() => {
  vi.clearAllMocks();
  mockCreateElement.mockImplementation((tag: string) => {
    if (tag === "a") {
      const el = _originalCreateElement("a");
      el.click = mockClick;
      return el;
    }
    return _originalCreateElement(tag as keyof HTMLElementTagNameMap);
  });
});

// ---------------------------------------------------------------------------
// SCH-17 — Export form renders
// ---------------------------------------------------------------------------

describe("SCH-17 — Export form renders", () => {
  it("renders the page heading", () => {
    render(<ExportPage />);
    expect(
      screen.getByRole("heading", { name: EXPORT_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the Select report card heading", () => {
    render(<ExportPage />);
    expect(screen.getByText(EXPORT_STRINGS.selectReport)).toBeInTheDocument();
  });

  it("renders Overview Report option", () => {
    render(<ExportPage />);
    expect(screen.getByText(EXPORT_STRINGS.overviewReport)).toBeInTheDocument();
  });

  it("renders Trends Report option", () => {
    render(<ExportPage />);
    expect(screen.getByText(EXPORT_STRINGS.trendsReport)).toBeInTheDocument();
  });

  it("renders Unit Performance option", () => {
    render(<ExportPage />);
    expect(screen.getByText(EXPORT_STRINGS.unitPerformance)).toBeInTheDocument();
  });

  it("renders the Download CSV button", () => {
    render(<ExportPage />);
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeInTheDocument();
  });

  it("Download CSV button is enabled when teacher is loaded", () => {
    render(<ExportPage />);
    const btn = screen.getByRole("button", { name: /Download CSV/ });
    expect(btn).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// SCH-18 — CSV download triggers
// ---------------------------------------------------------------------------

describe("SCH-18 — CSV download triggers on export click", () => {
  beforeEach(() => {
    mockGetOverviewReport.mockResolvedValue({
      school_id: "school-001",
      period: "30d",
      enrolled_students: 120,
      active_students_period: 85,
      active_pct: 70.8,
      lessons_viewed: 340,
      quiz_attempts: 210,
      first_attempt_pass_rate_pct: 72.0,
      audio_play_rate_pct: 45.0,
      units_with_struggles: [],
      units_no_activity: [],
      unreviewed_feedback_count: 3,
    });
  });

  it("shows 'Generating…' while export is in progress", async () => {
    // Make the API call pend briefly
    mockGetOverviewReport.mockReturnValue(new Promise(() => {}));
    render(<ExportPage />);
    fireEvent.click(screen.getByRole("button", { name: /Download CSV/ }));
    expect(await screen.findByText(EXPORT_STRINGS.generatingBtn)).toBeInTheDocument();
  });

  it("triggers anchor click (file download) after successful export", async () => {
    render(<ExportPage />);
    fireEvent.click(screen.getByRole("button", { name: /Download CSV/ }));
    await waitFor(() => expect(mockClick).toHaveBeenCalledTimes(1));
  });

  it("shows 'Downloaded' state after successful export", async () => {
    render(<ExportPage />);
    fireEvent.click(screen.getByRole("button", { name: /Download CSV/ }));
    expect(await screen.findByText(EXPORT_STRINGS.downloadedBtn)).toBeInTheDocument();
  });

  it("shows error message when export fails", async () => {
    mockGetOverviewReport.mockRejectedValue(new Error("network error"));
    render(<ExportPage />);
    fireEvent.click(screen.getByRole("button", { name: /Download CSV/ }));
    expect(await screen.findByText(EXPORT_STRINGS.exportError)).toBeInTheDocument();
  });
});
