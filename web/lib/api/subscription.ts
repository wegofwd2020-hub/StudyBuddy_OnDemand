import api from "./client";

export type SubscriptionStatus = "free" | "trial" | "active" | "cancelled" | "past_due";
export type BillingPeriod = "monthly" | "annual";
export type PlanId = "student_monthly" | "student_annual";

export interface SubscriptionState {
  status: SubscriptionStatus;
  plan: PlanId | null;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export async function getSubscriptionStatus(): Promise<SubscriptionState> {
  const res = await api.get<SubscriptionState>("/subscription/status");
  return res.data;
}

export async function createCheckout(
  plan: PlanId,
  billingPeriod: BillingPeriod,
): Promise<string> {
  const res = await api.post<{ checkout_url: string }>("/subscription/checkout", {
    plan,
    billing_period: billingPeriod,
  });
  return res.data.checkout_url;
}

export async function getBillingPortalUrl(): Promise<string> {
  const res = await api.get<{ url: string }>("/subscription/billing-portal");
  return res.data.url;
}

export async function cancelSubscription(): Promise<void> {
  await api.post("/subscription/cancel");
}
