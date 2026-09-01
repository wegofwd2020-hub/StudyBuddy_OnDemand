/**
 * Venki's 1 Sep round — "Reports → Export CSV → Trends Report: Download Excel
 * data related to Last 12 weeks is shown. Don't have an option to download this
 * report for Last 7 days or This term."
 *
 * He was right, and it was not a missing feature so much as a missing argument.
 * The export page had NO period control at all, and every call was hardcoded:
 *
 *     getOverviewReport(schoolId, "30d")
 *     getTrendsReport(schoolId, "12w")
 *
 * So a teacher who had just read "This term" on the dashboard downloaded a file
 * covering the last 30 days, with nothing on screen saying so.
 *
 * The existing csv-export.test.ts exercises papaparse only — it never touches
 * the page, which is exactly why a hardcoded argument could sit there unnoticed.
 * These tests assert what reaches the API, because that is where the defect was.
 *
 * Run with: docker compose exec -T web npx vitest run csv-export-period
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExportPage from "@/app/(school)/school/reports/export/page";
import * as reportsApi from "@/lib/api/reports";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() })),
  usePathname: vi.fn(() => "/school/reports/export"),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => ({
    teacher_id: "t-1",
    school_id: "sch-1",
    role: "school_admin",
  })),
}));

vi.mock("@/lib/api/reports", async (importOriginal) => {
  const actual = await importOriginal<typeof reportsApi>();
  return {
    ...actual,
    getOverviewReport: vi.fn(),
    getTrendsReport: vi.fn(),
    getCurriculumHealth: vi.fn(),
  };
});

const getOverviewReport = vi.mocked(reportsApi.getOverviewReport);
const getTrendsReport = vi.mocked(reportsApi.getTrendsReport);
const getCurriculumHealth = vi.mocked(reportsApi.getCurriculumHealth);

beforeEach(() => {
  vi.clearAllMocks();

  getOverviewReport.mockResolvedValue({
    school_id: "sch-1",
    period: "term",
    enrolled_students: 6,
    active_students_period: 2,
    active_pct: 33.3,
    lessons_viewed: 107,
    quiz_attempts: 57,
    first_attempt_pass_rate_pct: 45,
    audio_play_rate_pct: 0,
    units_with_struggles: [],
    units_no_activity: [],
    unreviewed_feedback_count: 21,
  } as Awaited<ReturnType<typeof reportsApi.getOverviewReport>>);

  getTrendsReport.mockResolvedValue({
    school_id: "sch-1",
    period: "4w",
    weeks: [],
  } as Awaited<ReturnType<typeof reportsApi.getTrendsReport>>);

  getCurriculumHealth.mockResolvedValue({
    school_id: "sch-1",
    total_units: 0,
    healthy_count: 0,
    watch_count: 0,
    struggling_count: 0,
    no_activity_count: 0,
    units: [],
  } as Awaited<ReturnType<typeof reportsApi.getCurriculumHealth>>);

  // jsdom has no real download path; the page only needs these to not throw.
  global.URL.createObjectURL = vi.fn(() => "blob:stub");
  global.URL.revokeObjectURL = vi.fn();
});

async function chooseReport(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByText(label));
}

async function download(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /download csv/i }));
}

describe("Export CSV — period selection", () => {
  it("sends the chosen trends period, not a hardcoded 12 weeks", async () => {
    // The literal complaint. Before this change the argument was the string
    // "12w" no matter what, so this assertion is the whole fix.
    const user = userEvent.setup();
    render(<ExportPage />);

    await chooseReport(user, "Trends Report");
    await user.click(screen.getByRole("radio", { name: "4 weeks" }));
    await download(user);

    expect(getTrendsReport).toHaveBeenCalledWith("sch-1", "4w");
  });

  it("offers This term for trends, which had no way to be requested at all", async () => {
    const user = userEvent.setup();
    render(<ExportPage />);

    await chooseReport(user, "Trends Report");
    await user.click(screen.getByRole("radio", { name: "This term" }));
    await download(user);

    expect(getTrendsReport).toHaveBeenCalledWith("sch-1", "term");
  });

  it("sends the chosen overview period, not a hardcoded 30 days", async () => {
    const user = userEvent.setup();
    render(<ExportPage />);

    // Overview is the default selection.
    await user.click(screen.getByRole("radio", { name: "Last 7 days" }));
    await download(user);

    expect(getOverviewReport).toHaveBeenCalledWith("sch-1", "7d");
  });

  it("keeps each report's own period when switching between them", async () => {
    // Two independent states rather than one shared value: picking "4 weeks"
    // for trends must not leave the overview asking for a period that does not
    // exist in its vocabulary.
    const user = userEvent.setup();
    render(<ExportPage />);

    await chooseReport(user, "Trends Report");
    await user.click(screen.getByRole("radio", { name: "4 weeks" }));
    await chooseReport(user, "Overview Report");
    await user.click(screen.getByRole("radio", { name: "This term" }));
    await download(user);
    expect(getOverviewReport).toHaveBeenCalledWith("sch-1", "term");

    await chooseReport(user, "Trends Report");
    await download(user);
    expect(getTrendsReport).toHaveBeenCalledWith("sch-1", "4w");
  });

  it("offers each report only its own periods", async () => {
    // The answer to "Dashboard filters by days, Trends by weeks — is this OK?"
    // Yes: trends bucket into ISO weeks, so a seven-day trend is one data point.
    // A shared selector would have to imply an export that cannot exist.
    const user = userEvent.setup();
    render(<ExportPage />);

    expect(screen.getByRole("radio", { name: "Last 30 days" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "12 weeks" })).toBeNull();

    await chooseReport(user, "Trends Report");
    expect(screen.getByRole("radio", { name: "12 weeks" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Last 30 days" })).toBeNull();
  });

  it("says Unit Performance has no period rather than showing an inert control", async () => {
    // The endpoint takes no period and the figures are all-time. A selector that
    // silently did not apply would be the same defect in a friendlier costume —
    // which is what the dashboard's unreviewed-feedback card still does.
    const user = userEvent.setup();
    render(<ExportPage />);

    await chooseReport(user, "Unit Performance");

    expect(screen.getByText(/all activity to date/i)).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: /weeks|days|term/i })).toBeNull();

    await download(user);
    expect(getCurriculumHealth).toHaveBeenCalledWith("sch-1");
  });
});
