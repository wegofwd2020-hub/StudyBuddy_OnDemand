import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/admin-client", () => ({
  default: { post: vi.fn(), get: vi.fn() },
}));

import adminApi from "@/lib/api/admin-client";
import {
  approveReview,
  rejectReview,
  publishReview,
  rollbackReview,
  blockVersionContent,
  getReviewQueue,
} from "@/lib/api/admin";

const mockPost = adminApi.post as ReturnType<typeof vi.fn>;
const mockGet = adminApi.get as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("approveReview", () => {
  it("posts to approve endpoint", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await approveReview("ver-001");
    expect(mockPost).toHaveBeenCalledWith("/admin/content/review/ver-001/approve", {
      notes: undefined,
    });
  });
});

describe("rejectReview", () => {
  it("posts notes to reject endpoint", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await rejectReview("ver-002", "Inaccurate formula");
    expect(mockPost).toHaveBeenCalledWith("/admin/content/review/ver-002/reject", {
      notes: "Inaccurate formula",
      regenerate: false,
    });
  });
});

describe("publishReview", () => {
  it("posts to publish endpoint", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await publishReview("ver-003");
    expect(mockPost).toHaveBeenCalledWith("/admin/content/versions/ver-003/publish");
  });
});

describe("rollbackReview", () => {
  it("posts to rollback endpoint", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await rollbackReview("ver-004");
    expect(mockPost).toHaveBeenCalledWith("/admin/content/versions/ver-004/rollback");
  });
});

describe("blockVersionContent", () => {
  it("posts unit/type/reason to block endpoint", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await blockVersionContent("ver-005", "unit-001", "lesson", "Unsafe content");
    expect(mockPost).toHaveBeenCalledWith("/admin/content/review/ver-005/block", {
      unit_id: "unit-001",
      content_type: "lesson",
      reason: "Unsafe content",
    });
  });
});

describe("getReviewQueue", () => {
  it("fetches pending queue by status filter", async () => {
    mockGet.mockResolvedValueOnce({
      data: { items: [], total: 0 },
    });
    const result = await getReviewQueue("pending");
    expect(result.total).toBe(0);
    expect(mockGet).toHaveBeenCalledWith("/admin/content/review/queue", {
      params: { status: "pending" },
    });
  });

  it("fetches all items when no status filter", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await getReviewQueue();
    expect(mockGet).toHaveBeenCalledWith("/admin/content/review/queue", {
      params: {},
    });
  });
});
