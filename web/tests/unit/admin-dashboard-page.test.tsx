/**
 * Unit tests for section 4.3 — Admin Dashboard (`/admin/dashboard`)
 * Covers TC-IDs: ADM-07, ADM-08, ADM-09
 *
 * Run with:
 *   npm test -- admin-dashboard-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminDashboardPage from "@/app/(admin)/admin/dashboard/page";
import {
  MOCK_ANALYTICS,
  MOCK_PIPELINE_JOBS,
  DASHBOARD_STRINGS,
} from "../e2e/data/admin-dashboard-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

function setupQueries() {
  mockUseQuery.mockImplementation(({ queryKey }: { queryKey: unknown[] }) => {
    const keys = queryKey as string[];
    if (keys[2] === "subscriptions") {
      return { data: MOCK_ANALYTICS, isLoading: false };
    }
    if (keys[2] === "jobs") {
      return { data: MOCK_PIPELINE_JOBS, isLoading: false };
    }
    return { data: undefined, isLoading: false };
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  setupQueries();
});

// ---------------------------------------------------------------------------
// ADM-07 — Dashboard heading renders
// ---------------------------------------------------------------------------

describe("ADM-07 — Dashboard heading renders", () => {
  it("renders 'Platform Dashboard' heading", () => {
    render(<AdminDashboardPage />);
    expect(
      screen.getByRole("heading", { name: DASHBOARD_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-08 — Subscription KPI cards render
// ---------------------------------------------------------------------------

describe("ADM-08 — Subscription KPI cards render", () => {
  it("renders Total Active card label", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.totalActive)).toBeInTheDocument();
  });

  it("renders MRR card label", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.mrr)).toBeInTheDocument();
  });

  it("renders New This Month card label", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.newThisMonth)).toBeInTheDocument();
  });

  it("renders Churn Rate card label", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.churnRate)).toBeInTheDocument();
  });

  it("renders total_active value", () => {
    render(<AdminDashboardPage />);
    expect(
      screen.getByText(MOCK_ANALYTICS.total_active.toLocaleString()),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-09 — Pipeline section renders
// ---------------------------------------------------------------------------

describe("ADM-09 — Pipeline section renders", () => {
  it("renders Pipeline section heading", () => {
    render(<AdminDashboardPage />);
    const matches = screen.getAllByText(/pipeline/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Total Jobs card", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.totalJobs)).toBeInTheDocument();
  });

  it("renders Active jobs card", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.activeJobs)).toBeInTheDocument();
  });

  it("renders Failed jobs card", () => {
    render(<AdminDashboardPage />);
    expect(screen.getByText(DASHBOARD_STRINGS.failedJobs)).toBeInTheDocument();
  });

  it("shows correct total job count", () => {
    render(<AdminDashboardPage />);
    // 2 jobs total
    expect(
      screen.getByText(String(MOCK_PIPELINE_JOBS.jobs.length)),
    ).toBeInTheDocument();
  });
});
