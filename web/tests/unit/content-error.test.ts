import { describe, it, expect } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";
import { contentErrorMessage } from "@/lib/content-error";

function httpError(status: number, data: unknown = {}) {
  const config = { headers: new AxiosHeaders() };
  return new AxiosError("request failed", "ERR_BAD_REQUEST", config, undefined, {
    status,
    statusText: "",
    headers: {},
    config,
    data,
  } as never);
}

describe("contentErrorMessage", () => {
  it("shows the school paywall copy for 402, not the generic error", () => {
    const result = contentErrorMessage(
      httpError(402, {
        error: "subscription_required",
        detail: "Upgrade to StudyBuddy Premium to unlock all lessons.",
      }),
    );
    expect(result.message).toBe(
      "You've reached the end of what's available to you right now. Your school controls which lessons you can open.",
    );
    expect(result.unavailable).toBe(true);
    expect(result.lessonRequired).toBeUndefined();
  });

  it("keeps the not-yet-available copy for 404", () => {
    expect(contentErrorMessage(httpError(404)).message).toBe(
      "This isn't available yet. Please check back soon.",
    );
  });

  it("keeps the generic retry copy for a server error", () => {
    const result = contentErrorMessage(httpError(500));
    expect(result.message).toBe("Something went wrong loading this. Please try again.");
    expect(result.unavailable).toBe(false);
  });
});
