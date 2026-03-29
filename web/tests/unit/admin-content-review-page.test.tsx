/**
 * Unit tests for section 4.8 — Content Review Queue (`/admin/content-review`)
 * Covers TC-IDs: ADM-31, ADM-32, ADM-33, ADM-34, ADM-35
 *
 * Run with:
 *   npm test -- admin-content-review-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminContentReviewPage from "@/app/(admin)/admin/content-review/page";
import {
  MOCK_QUEUE,
  MOCK_QUEUE_EMPTY,
  REVIEW_QUEUE_STRINGS,
} from "../e2e/data/admin-content-review-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockGetReviewQueue = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    getReviewQueue: (...args: unknown[]) => mockGetReviewQueue(...args),
  };
});

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQuery: vi.fn((opts) => mockUseQuery(opts)) };
});

// ---------------------------------------------------------------------------
// ADM-31 — Content Review Queue page renders
// ---------------------------------------------------------------------------

describe("ADM-31 — Content Review Queue heading renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_QUEUE, isLoading: false });
  });

  it("renders 'Content Review Queue' heading", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("heading", { name: REVIEW_QUEUE_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-32 — Status filter tabs render
// ---------------------------------------------------------------------------

describe("ADM-32 — Status filter tabs render", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_QUEUE, isLoading: false });
  });

  it("renders 'pending' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabPending }),
    ).toBeInTheDocument();
  });

  it("renders 'approved' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabApproved }),
    ).toBeInTheDocument();
  });

  it("renders 'published' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabPublished }),
    ).toBeInTheDocument();
  });

  it("renders 'rejected' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabRejected }),
    ).toBeInTheDocument();
  });

  it("renders 'blocked' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabBlocked }),
    ).toBeInTheDocument();
  });

  it("renders 'All' tab", () => {
    render(<AdminContentReviewPage />);
    expect(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabAll }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-33 — Filtering by status updates list
// ---------------------------------------------------------------------------

describe("ADM-33 — Filter tab click updates the query", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_QUEUE, isLoading: false });
  });

  it("clicking 'approved' tab triggers query with approved status", async () => {
    render(<AdminContentReviewPage />);
    fireEvent.click(
      screen.getByRole("button", { name: REVIEW_QUEUE_STRINGS.tabApproved }),
    );
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      expect(lastCall?.queryKey).toContain("approved");
    });
  });
});

// ---------------------------------------------------------------------------
// ADM-34 — Review link navigates to detail
// ---------------------------------------------------------------------------

describe("ADM-34 — Review link navigates to detail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_QUEUE, isLoading: false });
  });

  it("renders 'Review →' links for each item", () => {
    render(<AdminContentReviewPage />);
    const links = screen.getAllByRole("link", { name: REVIEW_QUEUE_STRINGS.reviewLink });
    expect(links.length).toBe(MOCK_QUEUE.items.length);
  });

  it("Review link href contains version_id", () => {
    render(<AdminContentReviewPage />);
    const link = screen.getAllByRole("link", {
      name: REVIEW_QUEUE_STRINGS.reviewLink,
    })[0];
    expect(link).toHaveAttribute(
      "href",
      `/admin/content-review/${MOCK_QUEUE.items[0].version_id}`,
    );
  });
});

// ---------------------------------------------------------------------------
// ADM-35 — Empty state when no items
// ---------------------------------------------------------------------------

describe("ADM-35 — Empty state when no items", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: MOCK_QUEUE_EMPTY, isLoading: false });
  });

  it("shows empty state message when queue is empty", () => {
    render(<AdminContentReviewPage />);
    expect(screen.getByText(REVIEW_QUEUE_STRINGS.noItems)).toBeInTheDocument();
  });
});
