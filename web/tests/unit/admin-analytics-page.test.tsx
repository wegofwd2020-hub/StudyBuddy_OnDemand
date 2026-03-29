/**
 * Unit tests for section 4.4 — Analytics (`/admin/analytics`)
 * Covers TC-IDs: ADM-11, ADM-12, ADM-13, ADM-14
 *
 * Run with:
 *   npm test -- admin-analytics-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminAnalyticsPage from "@/app/(admin)/admin/analytics/page";
import {
  MOCK_SUBSCRIPTION,
  MOCK_STRUGGLE,
  ANALYTICS_STRINGS,
} from "../e2e/data/admin-analytics-page";

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
      return { data: MOCK_SUBSCRIPTION, isLoading: false };
    }
    if (keys[2] === "struggle") {
      return { data: MOCK_STRUGGLE, isLoading: false };
    }
    return { data: undefined, isLoading: false };
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  setupQueries();
});

// ---------------------------------------------------------------------------
// ADM-11 — Page heading renders
// ---------------------------------------------------------------------------

describe("ADM-11 — Page heading renders", () => {
  it("renders 'Platform Analytics' heading", () => {
    render(<AdminAnalyticsPage />);
    expect(
      screen.getByRole("heading", { name: ANALYTICS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-12 — Subscription table renders
// ---------------------------------------------------------------------------

describe("ADM-12 — Subscription table renders", () => {
  it("renders Subscription Breakdown section heading", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.subSectionHeading)).toBeInTheDocument();
  });

  it("renders Monthly subscribers row", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.rowMonthly)).toBeInTheDocument();
  });

  it("renders Annual subscribers row", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.rowAnnual)).toBeInTheDocument();
  });

  it("renders MRR row", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.rowMrr)).toBeInTheDocument();
  });

  it("renders Churn rate row", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.rowChurn)).toBeInTheDocument();
  });

  it("renders the total_active value in the table", () => {
    render(<AdminAnalyticsPage />);
    expect(
      screen.getByText(MOCK_SUBSCRIPTION.total_active.toLocaleString()),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-13 — Struggle report table renders
// ---------------------------------------------------------------------------

describe("ADM-13 — Struggle report table renders", () => {
  it("renders Struggle Report section heading", () => {
    render(<AdminAnalyticsPage />);
    expect(
      screen.getByText(ANALYTICS_STRINGS.struggleSectionHeading),
    ).toBeInTheDocument();
  });

  it("renders the Fail Rate column header", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(ANALYTICS_STRINGS.colFailRate)).toBeInTheDocument();
  });

  it("renders unit title in struggle table", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(MOCK_STRUGGLE.units[0].unit_title)).toBeInTheDocument();
  });

  it("renders subject column", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText(MOCK_STRUGGLE.units[0].subject)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-14 — High fail-rate highlighted in red, low in green
// ---------------------------------------------------------------------------

describe("ADM-14 — Fail rate colour coding", () => {
  it("applies red class to fail rate > 40%", () => {
    const { container } = render(<AdminAnalyticsPage />);
    // Algebra Basics has fail_rate 0.45 → 45.0%
    const redSpan = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === "45.0%" && el.className.includes("text-red"),
    );
    expect(redSpan).toBeDefined();
  });

  it("applies green class to fail rate < 20%", () => {
    const { container } = render(<AdminAnalyticsPage />);
    // Photosynthesis has fail_rate 0.15 → 15.0%
    const greenSpan = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === "15.0%" && el.className.includes("text-green"),
    );
    expect(greenSpan).toBeDefined();
  });
});
