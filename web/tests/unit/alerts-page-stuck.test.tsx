/**
 * The Alert Inbox renders `student_stuck_on_unit` — the first alert type that
 * names a STUDENT rather than a unit.
 *
 * Reported by Venki 2026-09-02 against a card reading `Attempt #11 · Score 3/8`:
 * "Why was this not shown in the Alerts section?" Nothing per-student could be,
 * because every alert type before this one was unit-grained.
 *
 * The page tests matter here beyond the usual, because the last two field
 * regressions on this surface were both rendering-side: the alert label map was
 * keyed on `pass_rate_low`, which nothing emits, so every real alert fell
 * through and the inbox printed the literal string `pass_rate_breach` at a
 * teacher; and `AlertItem` in `lib/api/reports.ts` is HAND-WRITTEN, so a field
 * present in the API and in `types.gen.ts` can still be missing from the type
 * the page imports (pitfall #40).
 *
 * Run with:
 *   npm test -- alerts-page-stuck
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AlertsPage from "@/app/(school)/school/alerts/page";
import type { AlertItem } from "@/lib/api/reports";
import { MOCK_TEACHER } from "../e2e/data/alerts-page";

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
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ setQueryData: vi.fn() })),
  };
});

/** Shaped from a real row: `details` carries ids only, names are resolved. */
const STUCK_ALERT: AlertItem = {
  alert_id: "a1",
  alert_type: "student_stuck_on_unit",
  school_id: "s1",
  details: {
    unit_id: "G10-TECH-004",
    student_id: "11111111-2222-3333-4444-555555555555",
    failed_attempts: 3,
  },
  triggered_at: "2026-08-05T06:00:00Z",
  acknowledged: false,
  grade: 10,
  unit_title: "Software Development Lifecycle",
  student_name: "Priya Raman",
};

const UNIT_ALERT: AlertItem = {
  alert_id: "a2",
  alert_type: "pass_rate_breach",
  school_id: "s1",
  details: { unit_id: "G10-TECH-001", pass_rate: 0 },
  triggered_at: "2026-08-05T06:00:00Z",
  acknowledged: false,
  grade: 10,
  unit_title: "Introduction to Computing",
  student_name: null,
};

describe("student_stuck_on_unit in the Alert Inbox", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({
      data: { alerts: [STUCK_ALERT] },
      isLoading: false,
    });
  });

  it("labels the type in the teacher's words, not the key", () => {
    render(<AlertsPage />);
    expect(screen.getByText("Not passing")).toBeInTheDocument();
    // The exact regression that shipped once: an unmapped type falls through to
    // the raw key and the inbox shows a database string to a teacher.
    expect(screen.queryByText(/student_stuck_on_unit/)).not.toBeInTheDocument();
  });

  it("names the student and the unit", () => {
    render(<AlertsPage />);
    expect(screen.getByText(/Priya Raman/)).toBeInTheDocument();
    expect(screen.getByText(/Software Development Lifecycle/)).toBeInTheDocument();
  });

  it("says how many attempts, so the alert is actionable without a click", () => {
    render(<AlertsPage />);
    expect(screen.getByText(/3 attempts, no pass/)).toBeInTheDocument();
  });

  it("dates the alert as ongoing rather than as a past event", () => {
    render(<AlertsPage />);
    // The evaluator deliberately does not touch `triggered_at` on a repeat, so a
    // bare date reads as old news — which is how the reporter read a live breach.
    expect(screen.getByText(/Open since/)).toBeInTheDocument();
  });

  it("falls back to the raw id rather than rendering a blank line", () => {
    mockUseQuery.mockReturnValue({
      data: {
        alerts: [{ ...STUCK_ALERT, unit_title: null, student_name: null }],
      },
      isLoading: false,
    });
    render(<AlertsPage />);
    expect(screen.getByText(/G10-TECH-004/)).toBeInTheDocument();
  });

  it("leaves a unit-grained alert reading exactly as before", () => {
    mockUseQuery.mockReturnValue({ data: { alerts: [UNIT_ALERT] }, isLoading: false });
    render(<AlertsPage />);
    expect(screen.getByText("Low pass rate")).toBeInTheDocument();
    expect(screen.getByText(/pass rate 0%/)).toBeInTheDocument();
    // No student half, and no stray separator left behind by the new branch.
    expect(screen.queryByText(/attempts, no pass/)).not.toBeInTheDocument();
  });
});
