import { describe, it, expect, vi, beforeEach } from "vitest";
import { trialDaysRemaining } from "@/lib/hooks/useSubscription";

// ---------------------------------------------------------------------------
// trialDaysRemaining — pure function, no mocks needed for most cases
// ---------------------------------------------------------------------------

describe("trialDaysRemaining", () => {
  it("returns null when trialEndsAt is null", () => {
    expect(trialDaysRemaining(null)).toBeNull();
  });

  it("returns 0 when trial has already ended", () => {
    const past = new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString();
    expect(trialDaysRemaining(past)).toBe(0);
  });

  it("returns 0 when trial ends exactly now", () => {
    // 1 ms in the past still rounds to 0
    const justPast = new Date(Date.now() - 1).toISOString();
    expect(trialDaysRemaining(justPast)).toBe(0);
  });

  it("returns 1 for a trial ending in less than 24 h (ceil)", () => {
    const soon = new Date(Date.now() + 1000 * 60 * 60 * 12).toISOString(); // 12 h
    expect(trialDaysRemaining(soon)).toBe(1);
  });

  it("returns 1 for a trial ending in exactly 24 h", () => {
    const tomorrow = new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString();
    expect(trialDaysRemaining(tomorrow)).toBe(1);
  });

  it("returns 7 for a trial ending in 7 days", () => {
    const sevenDays = new Date(Date.now() + 1000 * 60 * 60 * 24 * 7).toISOString();
    expect(trialDaysRemaining(sevenDays)).toBe(7);
  });

  it("returns 14 for a two-week trial", () => {
    const twoWeeks = new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString();
    expect(trialDaysRemaining(twoWeeks)).toBe(14);
  });
});

// ---------------------------------------------------------------------------
// Subscription API module — mock axios client
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import api from "@/lib/api/client";
import {
  getSubscriptionStatus,
  createCheckout,
  getBillingPortalUrl,
  cancelSubscription,
} from "@/lib/api/subscription";

const mockGet = api.get as ReturnType<typeof vi.fn>;
const mockPost = api.post as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getSubscriptionStatus", () => {
  it("returns subscription state from API", async () => {
    const payload = {
      status: "trial",
      plan: null,
      trial_ends_at: "2026-04-10T00:00:00Z",
      current_period_end: null,
      cancel_at_period_end: false,
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getSubscriptionStatus();
    expect(result).toEqual(payload);
    expect(mockGet).toHaveBeenCalledWith("/subscription/status");
  });
});

describe("createCheckout", () => {
  it("posts plan and billing_period, returns checkout_url", async () => {
    mockPost.mockResolvedValueOnce({
      data: { checkout_url: "https://checkout.stripe.com/abc" },
    });

    const url = await createCheckout("student_monthly", "monthly");
    expect(url).toBe("https://checkout.stripe.com/abc");
    expect(mockPost).toHaveBeenCalledWith("/subscription/checkout", {
      plan: "student_monthly",
      billing_period: "monthly",
    });
  });
});

describe("getBillingPortalUrl", () => {
  it("fetches and returns portal URL", async () => {
    mockGet.mockResolvedValueOnce({
      data: { url: "https://billing.stripe.com/session/xyz" },
    });

    const url = await getBillingPortalUrl();
    expect(url).toBe("https://billing.stripe.com/session/xyz");
    expect(mockGet).toHaveBeenCalledWith("/subscription/billing-portal");
  });
});

describe("cancelSubscription", () => {
  it("posts to /subscription/cancel", async () => {
    mockPost.mockResolvedValueOnce({});

    await cancelSubscription();
    expect(mockPost).toHaveBeenCalledWith("/subscription/cancel");
  });
});
