/**
 * Unit tests for section 4.11 — System Health (`/admin/health`)
 * Covers TC-IDs: ADM-55, ADM-56, ADM-57, ADM-58, ADM-59, ADM-61
 *
 * Run with:
 *   npm test -- admin-health-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminHealthPage from "@/app/(admin)/admin/health/page";
import {
  MOCK_HEALTH_OK,
  MOCK_HEALTH_DEGRADED,
  HEALTH_STRINGS,
} from "../e2e/data/admin-health-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// ADM-55 — Health page heading renders
// ---------------------------------------------------------------------------

describe("ADM-55 — Health page heading renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_OK,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("renders 'System Health' heading", () => {
    render(<AdminHealthPage />);
    expect(
      screen.getByRole("heading", { name: HEALTH_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-56 — PostgreSQL service row renders
// ---------------------------------------------------------------------------

describe("ADM-56 — PostgreSQL service row renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_OK,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("renders the PostgreSQL row", () => {
    render(<AdminHealthPage />);
    expect(screen.getByText(HEALTH_STRINGS.postgresRow)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-57 — Redis service row renders
// ---------------------------------------------------------------------------

describe("ADM-57 — Redis service row renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_OK,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("renders the Redis row", () => {
    render(<AdminHealthPage />);
    expect(screen.getByText(HEALTH_STRINGS.redisRow)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-58 — All-ok banner shows green
// ---------------------------------------------------------------------------

describe("ADM-58 — All-ok green banner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_OK,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("shows 'All systems operational' when both services are ok", () => {
    render(<AdminHealthPage />);
    expect(screen.getByText(HEALTH_STRINGS.allOkBanner)).toBeInTheDocument();
  });

  it("all-ok banner has green background class", () => {
    render(<AdminHealthPage />);
    const span = screen.getByText(HEALTH_STRINGS.allOkBanner);
    expect(span.closest("div")?.className).toContain("green");
  });
});

// ---------------------------------------------------------------------------
// ADM-59 — Degraded banner shows red
// ---------------------------------------------------------------------------

describe("ADM-59 — Degraded red banner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_DEGRADED,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("shows 'One or more systems degraded' when a service is down", () => {
    render(<AdminHealthPage />);
    expect(screen.getByText(HEALTH_STRINGS.degradedBanner)).toBeInTheDocument();
  });

  it("degraded banner has red background class", () => {
    render(<AdminHealthPage />);
    const span = screen.getByText(HEALTH_STRINGS.degradedBanner);
    expect(span.closest("div")?.className).toContain("red");
  });
});

// ---------------------------------------------------------------------------
// ADM-61 — Page always polls (refetchInterval always returns a number)
// ---------------------------------------------------------------------------

describe("ADM-61 — Page always polls (refetchInterval always set)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: MOCK_HEALTH_OK,
      isLoading: false,
      dataUpdatedAt: Date.now(),
    });
  });

  it("useQuery is called with refetchInterval=10000", () => {
    render(<AdminHealthPage />);
    const callArgs = mockUseQuery.mock.calls[0]?.[0];
    expect(callArgs?.refetchInterval).toBe(10_000);
  });
});
