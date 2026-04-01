/**
 * Unit tests for section 4.9 — Content Review Detail (`/admin/content-review/[version_id]`)
 * Covers TC-IDs: ADM-36, ADM-37, ADM-38, ADM-39, ADM-40, ADM-41,
 *                ADM-42, ADM-43, ADM-44, ADM-45, ADM-46, ADM-47, ADM-48, ADM-49
 *
 * Run with:
 *   npm test -- admin-content-review-detail-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminContentReviewDetailPage from "@/app/(admin)/admin/content-review/[version_id]/page";
import {
  MOCK_VERSION_ID,
  MOCK_ITEM_PENDING,
  MOCK_ITEM_APPROVED,
  MOCK_ITEM_PUBLISHED,
  MOCK_ITEM_WITH_ANNOTATIONS,
  MOCK_PRODUCT_ADMIN,
  MOCK_DEVELOPER,
  REVIEW_DETAIL_STRINGS,
} from "../e2e/data/admin-content-review-detail-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ version_id: MOCK_VERSION_ID })),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

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
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ invalidateQueries: mockInvalidateQueries })),
  };
});

const mockApprove = vi.fn();
const mockReject = vi.fn();
const mockPublish = vi.fn();
const mockRollback = vi.fn();
const mockBlock = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    approveReview: (...args: unknown[]) => mockApprove(...args),
    rejectReview: (...args: unknown[]) => mockReject(...args),
    publishReview: (...args: unknown[]) => mockPublish(...args),
    rollbackReview: (...args: unknown[]) => mockRollback(...args),
    blockVersionContent: (...args: unknown[]) => mockBlock(...args),
  };
});

// ---------------------------------------------------------------------------
// ADM-36 — Lesson preview renders
// ---------------------------------------------------------------------------

describe("ADM-36 — Lesson preview renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
  });

  it("renders the subject heading", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByText(new RegExp(MOCK_ITEM_PENDING.subject))).toBeInTheDocument();
  });

  it("renders units section heading", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByText(/Units \(1\)/)).toBeInTheDocument();
  });

  it("renders curriculum_id and version metadata", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByText(/default-2026-g8/)).toBeInTheDocument();
    expect(screen.getByText(/Math/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-37 — Approve button visible for pending
// ---------------------------------------------------------------------------

describe("ADM-37 — Approve button visible for pending item", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
  });

  it("renders Approve button for pending item", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByRole("button", { name: /Approve/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-38 — Reject opens reason modal
// ---------------------------------------------------------------------------

describe("ADM-38 — Reject opens reason modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
  });

  it("clicking Reject opens the reason modal", () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Reject/i }));
    expect(screen.getByText("Reject version")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-39 — Reject Confirm disabled when reason empty
// ---------------------------------------------------------------------------

describe("ADM-39 — Reject Confirm button disabled with empty reason", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
  });

  it("Confirm reject button is disabled when reason textarea is empty", () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Reject/i }));
    const confirmBtn = screen.getByRole("button", { name: /Confirm reject/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("Confirm reject button is enabled when reason is entered", () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Reject/i }));
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Poor content quality" },
    });
    const confirmBtn = screen.getByRole("button", { name: /Confirm reject/i });
    expect(confirmBtn).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// ADM-40 — Approve action calls API
// ---------------------------------------------------------------------------

describe("ADM-40 — Approve action calls API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
    mockApprove.mockResolvedValue(undefined);
  });

  it("calls approveReview with version_id on click", async () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Approve/i }));
    await waitFor(() => expect(mockApprove).toHaveBeenCalledWith(MOCK_VERSION_ID));
  });
});

// ---------------------------------------------------------------------------
// ADM-41 — Reject action calls API with reason
// ---------------------------------------------------------------------------

describe("ADM-41 — Reject action calls API with reason", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
    mockReject.mockResolvedValue(undefined);
  });

  it("calls rejectReview with version_id and reason", async () => {
    const reason = "Content too advanced for grade level";
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Reject/i }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: reason } });
    fireEvent.click(screen.getByRole("button", { name: /Confirm reject/i }));
    await waitFor(() => expect(mockReject).toHaveBeenCalledWith(MOCK_VERSION_ID, reason));
  });
});

// ---------------------------------------------------------------------------
// ADM-42 — Publish button visible for approved (product_admin)
// ---------------------------------------------------------------------------

describe("ADM-42 — Publish button visible for approved item (product_admin)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_APPROVED, isLoading: false });
  });

  it("renders Publish button for approved item when product_admin", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByRole("button", { name: /Publish/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-43 — Publish action calls API
// ---------------------------------------------------------------------------

describe("ADM-43 — Publish action calls API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_APPROVED, isLoading: false });
    mockPublish.mockResolvedValue(undefined);
  });

  it("calls publishReview with version_id on click", async () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Publish/i }));
    await waitFor(() => expect(mockPublish).toHaveBeenCalledWith(MOCK_VERSION_ID));
  });
});

// ---------------------------------------------------------------------------
// ADM-44 — Rollback button visible for published (product_admin)
// ---------------------------------------------------------------------------

describe("ADM-44 — Rollback button visible for published item", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PUBLISHED, isLoading: false });
  });

  it("renders Rollback button for published item when product_admin", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByRole("button", { name: /Rollback/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-45 — Block opens reason modal
// ---------------------------------------------------------------------------

describe("ADM-45 — Block opens reason modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PUBLISHED, isLoading: false });
  });

  it("clicking Block opens the reason modal", () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Block unit content/i }));
    expect(
      screen.getByRole("heading", { name: /Block unit content/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-46 — Rollback action calls API
// ---------------------------------------------------------------------------

describe("ADM-46 — Rollback action calls API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PUBLISHED, isLoading: false });
    mockRollback.mockResolvedValue(undefined);
  });

  it("calls rollbackReview with version_id on click", async () => {
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Rollback/i }));
    await waitFor(() => expect(mockRollback).toHaveBeenCalledWith(MOCK_VERSION_ID));
  });
});

// ---------------------------------------------------------------------------
// ADM-47 — Block action calls API with reason
// ---------------------------------------------------------------------------

describe("ADM-47 — Block action calls API with reason", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PUBLISHED, isLoading: false });
    mockBlock.mockResolvedValue(undefined);
  });

  it("calls blockVersionContent with version_id, unit_id, content_type, and reason", async () => {
    const reason = "Inappropriate content detected";
    render(<AdminContentReviewDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: /Block unit content/i }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: reason } });
    fireEvent.click(screen.getByRole("button", { name: /Confirm block/i }));
    await waitFor(() =>
      expect(mockBlock).toHaveBeenCalledWith(
        MOCK_VERSION_ID,
        "unit-001",
        "lesson",
        reason,
      ),
    );
  });
});

// ---------------------------------------------------------------------------
// ADM-48 — Annotations rendered
// ---------------------------------------------------------------------------

describe("ADM-48 — Annotations rendered when present", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_WITH_ANNOTATIONS, isLoading: false });
  });

  it("renders Annotations heading", () => {
    render(<AdminContentReviewDetailPage />);
    expect(
      screen.getByText(REVIEW_DETAIL_STRINGS.annotationsHeading),
    ).toBeInTheDocument();
  });

  it("renders the annotation note text", () => {
    render(<AdminContentReviewDetailPage />);
    expect(
      screen.getByText(MOCK_ITEM_WITH_ANNOTATIONS.annotations[0].annotation_text),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-49 — Back link returns to queue
// ---------------------------------------------------------------------------

describe("ADM-49 — Back link returns to queue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_ITEM_PENDING, isLoading: false });
  });

  it("renders 'Back to queue' link", () => {
    render(<AdminContentReviewDetailPage />);
    expect(screen.getByRole("link", { name: /Back to queue/i })).toBeInTheDocument();
  });

  it("back link points to /admin/content-review", () => {
    render(<AdminContentReviewDetailPage />);
    const link = screen.getByRole("link", { name: /Back to queue/i });
    expect(link).toHaveAttribute("href", "/admin/content-review");
  });
});
