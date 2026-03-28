/**
 * Unit tests for section 4.12 — Audit Log (`/admin/audit`)
 * Covers TC-IDs: ADM-62, ADM-63, ADM-64, ADM-65
 *
 * Run with:
 *   npm test -- admin-audit-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminAuditPage from "@/app/(admin)/admin/audit/page";
import {
  MOCK_PRODUCT_ADMIN,
  MOCK_DEVELOPER,
  MOCK_AUDIT_LOG,
  MOCK_AUDIT_LOG_PAGE1,
  AUDIT_STRINGS,
} from "../e2e/data/admin-audit-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAdmin = vi.fn();
vi.mock("@/lib/hooks/useAdmin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useAdmin")>();
  return { ...actual, useAdmin: vi.fn(() => mockUseAdmin()) };
});

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// ADM-62 — Audit log renders for product_admin
// ---------------------------------------------------------------------------

describe("ADM-62 — Audit log renders for product_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_AUDIT_LOG, isLoading: false });
  });

  it("renders 'Audit Log' heading", () => {
    render(<AdminAuditPage />);
    expect(
      screen.getByRole("heading", { name: AUDIT_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders Time column header", () => {
    render(<AdminAuditPage />);
    expect(screen.getByText(AUDIT_STRINGS.colTime)).toBeInTheDocument();
  });

  it("renders Actor column header", () => {
    render(<AdminAuditPage />);
    expect(screen.getByText(AUDIT_STRINGS.colActor)).toBeInTheDocument();
  });

  it("renders Action column header", () => {
    render(<AdminAuditPage />);
    expect(screen.getByText(AUDIT_STRINGS.colAction)).toBeInTheDocument();
  });

  it("renders Resource column header", () => {
    render(<AdminAuditPage />);
    expect(screen.getByText(AUDIT_STRINGS.colResource)).toBeInTheDocument();
  });

  it("renders action value in table row", () => {
    render(<AdminAuditPage />);
    expect(
      screen.getByText(MOCK_AUDIT_LOG.entries[0].action),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-63 — Access denied for developer
// ---------------------------------------------------------------------------

describe("ADM-63 — Access denied for developer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_AUDIT_LOG, isLoading: false });
  });

  it("shows 'Access denied' for developer role", () => {
    render(<AdminAuditPage />);
    expect(screen.getByText(AUDIT_STRINGS.accessDenied)).toBeInTheDocument();
  });

  it("does NOT render table headers for developer role", () => {
    render(<AdminAuditPage />);
    expect(screen.queryByText(AUDIT_STRINGS.colTime)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-64 — Action filter narrows results
// ---------------------------------------------------------------------------

describe("ADM-64 — Action filter input renders and triggers filtered query", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_AUDIT_LOG, isLoading: false });
  });

  it("renders the action filter input", () => {
    render(<AdminAuditPage />);
    expect(
      screen.getByPlaceholderText(AUDIT_STRINGS.filterPlaceholder),
    ).toBeInTheDocument();
  });

  it("typing in filter updates the query key with the action string", async () => {
    render(<AdminAuditPage />);
    const input = screen.getByPlaceholderText(AUDIT_STRINGS.filterPlaceholder);
    fireEvent.change(input, { target: { value: "publish" } });
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      expect(lastCall?.queryKey).toContain("publish");
    });
  });
});

// ---------------------------------------------------------------------------
// ADM-65 — Pagination works
// ---------------------------------------------------------------------------

describe("ADM-65 — Pagination Next/Previous", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_AUDIT_LOG_PAGE1, isLoading: false });
  });

  it("renders Next button", () => {
    render(<AdminAuditPage />);
    expect(
      screen.getByRole("button", { name: AUDIT_STRINGS.nextBtn }),
    ).toBeInTheDocument();
  });

  it("Previous button is disabled on page 1", () => {
    render(<AdminAuditPage />);
    expect(
      screen.getByRole("button", { name: AUDIT_STRINGS.prevBtn }),
    ).toBeDisabled();
  });

  it("clicking Next triggers query with page=2", async () => {
    render(<AdminAuditPage />);
    fireEvent.click(screen.getByRole("button", { name: AUDIT_STRINGS.nextBtn }));
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      expect(lastCall?.queryKey).toContain(2);
    });
  });
});
