/**
 * The lesson thumbs up/down widget posted to `/feedback/submit`, but the backend
 * only ever served `/feedback` — so every submission 404'd and the feedback table
 * stayed empty for the life of the deployment (issue #600).
 *
 * These tests pin the request the widget actually puts on the wire: the path the
 * API serves, and a body the API's schema accepts. Asserting the shape here is
 * the point — the previous mocks accepted anything, which is exactly why a live
 * 404 could go unnoticed.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";

const post = vi.fn();

vi.mock("@/lib/api/client", () => ({
  default: { post: (...args: unknown[]) => post(...args) },
}));

import { submitFeedback } from "@/lib/api/feedback";

describe("submitFeedback", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue({ data: { feedback_id: "abc", submitted_at: "now" } });
  });

  it("posts to the path the backend actually serves", async () => {
    await submitFeedback({
      unit_id: "G8-MATH-001",
      content_type: "lesson",
      rating: "up",
    });

    expect(post).toHaveBeenCalledTimes(1);
    expect(post.mock.calls[0][0]).toBe("/feedback");
  });

  it("sends a body the backend schema accepts, with the thumbs verdict as a boolean", async () => {
    await submitFeedback({
      unit_id: "G8-MATH-001",
      content_type: "lesson",
      rating: "up",
    });

    expect(post.mock.calls[0][1]).toMatchObject({
      category: "content",
      unit_id: "G8-MATH-001",
      content_type: "lesson",
      helpful: true,
    });
  });

  it("maps a thumbs-down to helpful=false", async () => {
    await submitFeedback({
      unit_id: "G8-SCI-002",
      content_type: "tutorial",
      rating: "down",
    });

    expect(post.mock.calls[0][1]).toMatchObject({ helpful: false });
  });

  it("never fabricates message text the student did not write", async () => {
    await submitFeedback({
      unit_id: "G8-MATH-001",
      content_type: "lesson",
      rating: "up",
    });

    const body = post.mock.calls[0][1] as Record<string, unknown>;
    expect(body.message).toBeUndefined();
  });

  it("passes a typed comment through as the message when one is supplied", async () => {
    await submitFeedback({
      unit_id: "G8-MATH-001",
      content_type: "lesson",
      rating: "down",
      comment: "The second example was confusing.",
    });

    expect(post.mock.calls[0][1]).toMatchObject({
      message: "The second example was confusing.",
      helpful: false,
    });
  });
});
