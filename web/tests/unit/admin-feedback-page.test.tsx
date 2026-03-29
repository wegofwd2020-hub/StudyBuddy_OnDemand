/**
 * Unit tests for section 4.10 — Feedback Queue (`/admin/feedback`)
 * Covers TC-IDs: ADM-50, ADM-51, ADM-52, ADM-53, ADM-54
 *
 * Run with:
 *   npm test -- admin-feedback-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminFeedbackPage from "@/app/(admin)/admin/feedback/page";
import {
  MOCK_PRODUCT_ADMIN,
  MOCK_DEVELOPER,
  MOCK_FEEDBACK_OPEN,
  MOCK_FEEDBACK_PAGE1,
  FEEDBACK_STRINGS,
} from "../e2e/data/admin-feedback-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAdmin = vi.fn();
vi.mock("@/lib/hooks/useAdmin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useAdmin")>();
  return { ...actual, useAdmin: vi.fn(() => mockUseAdmin()) };
});

const mockUseQuery = vi.fn();
const mockInvalidateQueries = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery:       vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ invalidateQueries: mockInvalidateQueries })),
  };
});

const mockResolveFeedback = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    resolveFeedback:  (...args: unknown[]) => mockResolveFeedback(...args),
  };
});

// ---------------------------------------------------------------------------
// ADM-50 — Feedback page renders for product_admin
// ---------------------------------------------------------------------------

describe("ADM-50 — Feedback page renders for product_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_OPEN, isLoading: false });
  });

  it("renders 'Student Feedback' heading", () => {
    render(<AdminFeedbackPage />);
    expect(
      screen.getByRole("heading", { name: FEEDBACK_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders feedback item unit title", () => {
    render(<AdminFeedbackPage />);
    expect(screen.getByText(MOCK_FEEDBACK_OPEN.items[0].unit_title)).toBeInTheDocument();
  });

  it("renders Resolve button for open feedback", () => {
    render(<AdminFeedbackPage />);
    const resolveBtns = screen.getAllByRole("button", { name: FEEDBACK_STRINGS.resolveBtn });
    expect(resolveBtns.length).toBe(MOCK_FEEDBACK_OPEN.items.length);
  });
});

// ---------------------------------------------------------------------------
// ADM-51 — Access denied for developer
// ---------------------------------------------------------------------------

describe("ADM-51 — Access denied for developer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_OPEN, isLoading: false });
  });

  it("shows 'Access denied' for developer role", () => {
    render(<AdminFeedbackPage />);
    expect(screen.getByText(FEEDBACK_STRINGS.accessDenied)).toBeInTheDocument();
  });

  it("does NOT render feedback items for developer role", () => {
    render(<AdminFeedbackPage />);
    expect(
      screen.queryByText(MOCK_FEEDBACK_OPEN.items[0].unit_title),
    ).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-52 — Open/Resolved toggle filters list
// ---------------------------------------------------------------------------

describe("ADM-52 — Open/Resolved toggle filters list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_OPEN, isLoading: false });
  });

  it("clicking Resolved tab triggers a query with resolved=true", async () => {
    render(<AdminFeedbackPage />);
    fireEvent.click(screen.getByRole("button", { name: FEEDBACK_STRINGS.tabResolved }));
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      // queryKey = ["admin", "feedback", page, showResolved=true]
      expect(lastCall?.queryKey).toContain(true);
    });
  });
});

// ---------------------------------------------------------------------------
// ADM-53 — Resolve action calls API and invalidates query
// ---------------------------------------------------------------------------

describe("ADM-53 — Resolve action calls API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_OPEN, isLoading: false });
    mockResolveFeedback.mockResolvedValue(undefined);
  });

  it("calls resolveFeedback with correct feedback_id", async () => {
    render(<AdminFeedbackPage />);
    fireEvent.click(screen.getAllByRole("button", { name: FEEDBACK_STRINGS.resolveBtn })[0]);
    await waitFor(() =>
      expect(mockResolveFeedback).toHaveBeenCalledWith(
        MOCK_FEEDBACK_OPEN.items[0].feedback_id,
      ),
    );
  });

  it("invalidates the feedback query after resolve", async () => {
    render(<AdminFeedbackPage />);
    fireEvent.click(screen.getAllByRole("button", { name: FEEDBACK_STRINGS.resolveBtn })[0]);
    await waitFor(() => expect(mockInvalidateQueries).toHaveBeenCalledTimes(1));
  });
});

// ---------------------------------------------------------------------------
// ADM-54 — Pagination works
// ---------------------------------------------------------------------------

describe("ADM-54 — Pagination Next/Previous", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_FEEDBACK_PAGE1, isLoading: false });
  });

  it("renders Next button", () => {
    render(<AdminFeedbackPage />);
    expect(
      screen.getByRole("button", { name: FEEDBACK_STRINGS.nextBtn }),
    ).toBeInTheDocument();
  });

  it("Previous button is disabled on page 1", () => {
    render(<AdminFeedbackPage />);
    expect(
      screen.getByRole("button", { name: FEEDBACK_STRINGS.prevBtn }),
    ).toBeDisabled();
  });

  it("clicking Next triggers query with page=2", async () => {
    render(<AdminFeedbackPage />);
    fireEvent.click(screen.getByRole("button", { name: FEEDBACK_STRINGS.nextBtn }));
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      expect(lastCall?.queryKey).toContain(2);
    });
  });
});
