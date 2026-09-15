/**
 * The admin subscription analytics client called `/admin/analytics/subscriptions`
 * (plural). The API serves `/admin/analytics/subscription` (singular), so the
 * dashboard and analytics pages both 404'd — a one-character path mismatch, the
 * same class of bug as #524 and #600 (issue #604).
 *
 * The declared TypeScript type was wrong too: it promised `active_monthly` /
 * `active_annual`, which the system does not model. Plans are starter /
 * professional / enterprise, not billing intervals, and the API returns a
 * `by_plan` breakdown. Those two fields could never have been populated.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";

const get = vi.fn();

vi.mock("@/lib/api/admin-client", () => ({
  default: { get: (...args: unknown[]) => get(...args) },
}));

import { getSubscriptionAnalytics } from "@/lib/api/admin";

const API_RESPONSE = {
  by_plan: {
    professional: { active: 2, new_this_month: 0, cancelled_this_month: 0 },
  },
  total_active: 2,
  mrr_usd: "598.00",
  new_this_month: 0,
  cancelled_this_month: 0,
  churn_rate: 0.0,
};

describe("getSubscriptionAnalytics", () => {
  beforeEach(() => {
    get.mockReset();
    get.mockResolvedValue({ data: API_RESPONSE });
  });

  it("calls the path the API actually serves", async () => {
    await getSubscriptionAnalytics();

    expect(get).toHaveBeenCalledTimes(1);
    expect(get.mock.calls[0][0]).toBe("/admin/analytics/subscription");
  });

  it("returns the plan breakdown the API sends", async () => {
    const result = await getSubscriptionAnalytics();

    expect(result.total_active).toBe(2);
    expect(result.mrr_usd).toBe("598.00");
    expect(result.by_plan.professional.active).toBe(2);
  });
});
