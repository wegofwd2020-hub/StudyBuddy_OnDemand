/**
 * The grade filter on Unit Performance (Venki, 2 Sep):
 *
 *   "Can we include filter option for the User to select for which Grade they
 *    are looking this report. You can default to all to start with."
 *
 * The backend tests hold the scoping rules. These hold the control itself, and
 * in particular the one failure that makes a server-side filter a trap: a
 * picker whose options come from the filtered result collapses to the single
 * option just chosen, and "All grades" becomes unreachable without a reload.
 *
 * Run with:
 *   npm test -- unit-performance-grade-filter
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UnitPerformancePage from "@/app/(school)/school/reports/units/page";

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => ({ school_id: "sch-1", role: "school_admin" })),
}));

const mockGetCurriculumHealth = vi.fn();
vi.mock("@/lib/api/reports", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reports")>();
  return {
    ...actual,
    getCurriculumHealth: (...args: unknown[]) => mockGetCurriculumHealth(...args),
  };
});

// useQuery is stubbed so the test drives what the server "returned" and can
// reach in for the queryFn — the page's request is the thing under test, and
// running it through a real client would only add a scheduler between the
// click and the assertion.
type QueryOpts = { queryKey: unknown[]; queryFn: () => unknown };
let lastOpts: QueryOpts | null = null;
const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts: QueryOpts) => {
      lastOpts = opts;
      return mockUseQuery(opts);
    }),
  };
});

vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const UNIT = {
  unit_id: "G5-SCI-001",
  unit_name: "Weather and Climate",
  subject: "Science",
  health_tier: "healthy" as const,
  first_attempt_pass_rate_pct: 82,
  avg_attempts_to_pass: 1.1,
  avg_score_pct: 77,
  feedback_count: 0,
  avg_rating: null,
  recommended_action: "none",
};

function report(overrides: Record<string, unknown> = {}) {
  return {
    school_id: "sch-1",
    total_units: 1,
    healthy_count: 1,
    watch_count: 0,
    struggling_count: 0,
    no_activity_count: 0,
    general_feedback_count: 0,
    available_grades: [5, 10],
    selected_grade: null,
    units: [UNIT],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  lastOpts = null;
  mockUseQuery.mockReturnValue({ data: report(), isLoading: false });
});

describe("Unit Performance — grade filter", () => {
  it("defaults to all grades", async () => {
    render(<UnitPerformancePage />);

    expect(screen.getByRole("radio", { name: "All grades" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    // No grade in the request until one is chosen.
    lastOpts?.queryFn();
    expect(mockGetCurriculumHealth).toHaveBeenCalledWith("sch-1", null);
  });

  it("offers every grade the server says the caller may see", () => {
    render(<UnitPerformancePage />);

    expect(screen.getByRole("radio", { name: "Grade 5" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Grade 10" })).toBeInTheDocument();
  });

  it("requests the chosen grade", async () => {
    const user = userEvent.setup();
    render(<UnitPerformancePage />);

    await user.click(screen.getByRole("radio", { name: "Grade 5" }));

    lastOpts?.queryFn();
    expect(mockGetCurriculumHealth).toHaveBeenLastCalledWith("sch-1", 5);
  });

  it("keeps every grade selectable after one is chosen", async () => {
    // The trap. The server keeps reporting the full `available_grades`; the
    // page must render the picker from THAT and not from the rows it just
    // received, or Grade 10 and "All grades" both vanish on first use.
    const user = userEvent.setup();
    render(<UnitPerformancePage />);

    await user.click(screen.getByRole("radio", { name: "Grade 5" }));
    mockUseQuery.mockReturnValue({
      data: report({ selected_grade: 5, units: [UNIT] }),
      isLoading: false,
    });

    expect(screen.getByRole("radio", { name: "Grade 5" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "Grade 10" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "All grades" })).toBeInTheDocument();
  });

  it("shows no control when there is no choice to make", () => {
    mockUseQuery.mockReturnValue({
      data: report({ available_grades: [5] }),
      isLoading: false,
    });
    render(<UnitPerformancePage />);

    expect(screen.queryByRole("radio", { name: "All grades" })).toBeNull();
    expect(screen.queryByRole("radio", { name: "Grade 5" })).toBeNull();
  });

  it("says an empty result is the filter's doing, and offers a way back", async () => {
    // "No unit activity recorded yet" under a grade filter blames the data for
    // a choice the reader just made — and leaves them on a page with nothing on
    // it and no obvious undo.
    const user = userEvent.setup();
    // Keyed off the grade in the query key, so the mock answers the way the
    // server would: Grade 10 has nothing, everything else does. Swapping a
    // fixed return value after the click would not work — the page only
    // re-reads the mock when its state actually changes.
    mockUseQuery.mockImplementation((opts: QueryOpts) => ({
      data:
        opts.queryKey[2] === 10
          ? report({ selected_grade: 10, units: [], total_units: 0, healthy_count: 0 })
          : report(),
      isLoading: false,
    }));
    render(<UnitPerformancePage />);

    await user.click(screen.getByRole("radio", { name: "Grade 10" }));

    expect(
      screen.getByText(/no unit activity recorded yet for grade 10/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /show all grades/i }));
    expect(screen.getByRole("radio", { name: "All grades" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
