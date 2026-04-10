/**
 * Teacher subscription API — independent teacher flat-fee plan management.
 *
 * Covers the seat-tiered flat-fee billing (Option A, #57 + #105).
 * Uses the school-client Axios instance (reads sb_teacher_token).
 */

import schoolApi from "./school-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TeacherSubscriptionStatus {
  plan: string;
  status: string | null;
  max_students: number;
  seats_used_students: number;
  current_period_end: string | null;
  over_quota: boolean;
  over_quota_since: string | null;
}

export interface TeacherCheckoutResult {
  checkout_url: string;
}

export interface TeacherPlanUpgradeResult {
  plan: string;
  max_students: number;
  over_quota: boolean;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getTeacherSubscription(
  teacherId: string,
): Promise<TeacherSubscriptionStatus> {
  const res = await schoolApi.get<TeacherSubscriptionStatus>(
    `/teachers/${teacherId}/subscription`,
  );
  return res.data;
}

export async function startTeacherCheckout(
  teacherId: string,
  plan: string,
  successUrl: string,
  cancelUrl: string,
): Promise<TeacherCheckoutResult> {
  const res = await schoolApi.post<TeacherCheckoutResult>(
    `/teachers/${teacherId}/subscription/checkout`,
    { plan, success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}

export async function upgradeTeacherPlan(
  teacherId: string,
  newPlan: string,
): Promise<TeacherPlanUpgradeResult> {
  const res = await schoolApi.patch<TeacherPlanUpgradeResult>(
    `/teachers/${teacherId}/subscription/plan`,
    { new_plan: newPlan },
  );
  return res.data;
}

export async function cancelTeacherSubscription(
  teacherId: string,
): Promise<{ status: string; current_period_end: string | null }> {
  const res = await schoolApi.delete(
    `/teachers/${teacherId}/subscription`,
  );
  return res.data;
}
