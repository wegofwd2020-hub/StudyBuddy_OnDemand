/**
 * Unit tests for section 3.12 — Alerts (`/school/alerts`)
 * Covers TC-IDs: SCH-19, SCH-20, SCH-21
 *
 * Run with:
 *   npm test -- alerts-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AlertsPage from "@/app/(school)/school/alerts/page";
import { formatDay } from "@/lib/utils/date";
import { SchoolNav } from "@/components/layout/SchoolNav";
import {
  MOCK_TEACHER,
  MOCK_ALERTS,
  MOCK_ALERTS_EMPTY,
  ALERTS_STRINGS,
} from "../e2e/data/alerts-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/school/alerts"),
}));

vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => MOCK_TEACHER),
}));

const mockUseQuery = vi.fn();
const mockSetQueryData = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ setQueryData: mockSetQueryData })),
  };
});

// ---------------------------------------------------------------------------
// SCH-19 — Alerts list renders
// ---------------------------------------------------------------------------

describe("SCH-19 — Alerts list renders", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_ALERTS, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<AlertsPage />);
    expect(
      screen.getByRole("heading", { name: ALERTS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders new alerts count badge", () => {
    render(<AlertsPage />);
    const unread = MOCK_ALERTS.alerts.filter((a) => !a.acknowledged).length;
    expect(screen.getByText(`${unread} new`)).toBeInTheDocument();
  });

  it("renders 'Low pass rate' alert type label", () => {
    render(<AlertsPage />);
    expect(screen.getByText(ALERTS_STRINGS.lowPassRate)).toBeInTheDocument();
  });

  it("renders 'Inactive students' alert type label", () => {
    render(<AlertsPage />);
    expect(screen.getByText(ALERTS_STRINGS.inactiveStudents)).toBeInTheDocument();
  });

  it("renders Dismiss buttons for each unacknowledged alert", () => {
    render(<AlertsPage />);
    const unread = MOCK_ALERTS.alerts.filter((a) => !a.acknowledged).length;
    const dismissBtns = screen.getAllByRole("button", { name: /Dismiss/ });
    expect(dismissBtns).toHaveLength(unread);
  });

  it("renders Acknowledged section for acknowledged alerts", () => {
    render(<AlertsPage />);
    expect(screen.getByText(ALERTS_STRINGS.acknowledgedLabel)).toBeInTheDocument();
  });

  it("renders Score drop label in acknowledged section", () => {
    render(<AlertsPage />);
    expect(screen.getByText(ALERTS_STRINGS.scoreDrop)).toBeInTheDocument();
  });

  it("shows loading skeletons while fetching", () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<AlertsPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows empty state when no alerts", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_ALERTS_EMPTY, isLoading: false });
    render(<AlertsPage />);
    expect(screen.getByText(ALERTS_STRINGS.noAlerts)).toBeInTheDocument();
  });

  it("dates an open alert as ongoing, not as a past event", () => {
    // The evaluator re-checks every morning and deliberately leaves
    // `triggered_at` alone on a repeat breach, so the value is when the breach
    // STARTED and the alert is still live. Rendered as a bare date it reads as
    // old news: a tester looked at a unit still breaching today, saw a date
    // four weeks back, and asked why no alert had fired for it.
    render(<AlertsPage />);
    const open = MOCK_ALERTS.alerts.filter((a) => !a.acknowledged);
    expect(open.length).toBeGreaterThan(0);
    for (const a of open) {
      expect(
        screen.getByText(`Open since ${formatDay(a.triggered_at)}`),
      ).toBeInTheDocument();
    }
  });

  it("names the month, so the date cannot be read as another day", () => {
    // `toLocaleDateString()` gives 05/08/2026 here and 08/05/2026 in the US —
    // the same ambiguity fixed for the weekly breakdown.
    render(<AlertsPage />);
    const first = MOCK_ALERTS.alerts.find((a) => !a.acknowledged)!;
    expect(formatDay(first.triggered_at)).toMatch(
      /^\d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}$/,
    );
  });
});

// ---------------------------------------------------------------------------
// SCH-20 — Dismissing alert removes it from visible list
// ---------------------------------------------------------------------------

describe("SCH-20 — Dismiss alert (optimistic update)", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: MOCK_ALERTS, isLoading: false });
  });

  it("calls setQueryData when Dismiss is clicked", () => {
    render(<AlertsPage />);
    const [firstDismiss] = screen.getAllByRole("button", { name: /Dismiss/ });
    fireEvent.click(firstDismiss);
    expect(mockSetQueryData).toHaveBeenCalledTimes(1);
  });

  it("Dismiss button is present before click", () => {
    render(<AlertsPage />);
    const unread = MOCK_ALERTS.alerts.filter((a) => !a.acknowledged).length;
    expect(screen.getAllByRole("button", { name: /Dismiss/ })).toHaveLength(unread);
  });
});

// ---------------------------------------------------------------------------
// SCH-21 — Unread count badge in SchoolNav
// ---------------------------------------------------------------------------

describe("SCH-21 — Unread count badge in SchoolNav", () => {
  it("shows red badge count on Alerts nav item when there are unread alerts", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_ALERTS, isLoading: false });
    const { container } = render(<SchoolNav />);
    const unread = MOCK_ALERTS.alerts.filter((a) => !a.acknowledged).length;
    // The badge is a span with red background
    const badge = container.querySelector("span.bg-red-500");
    expect(badge).toBeTruthy();
    expect(badge!.textContent).toBe(String(unread));
  });

  it("does NOT show badge when all alerts are acknowledged", () => {
    mockUseQuery.mockReturnValue({ data: MOCK_ALERTS_EMPTY, isLoading: false });
    const { container } = render(<SchoolNav />);
    const badge = container.querySelector("span.bg-red-500");
    expect(badge).toBeNull();
  });
});
