/**
 * Teacher API — independent teacher endpoints.
 *
 * Covers Connect (Express) revenue-share billing (Option B, #104).
 * Uses the same school-client Axios instance (reads sb_teacher_token).
 */

import schoolApi from "./school-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ConnectStatus {
  has_connect_account: boolean;
  stripe_account_id: string | null;
  onboarding_complete: boolean;
  charges_enabled: boolean;
  payouts_enabled: boolean;
}

export interface ConnectOnboardResult {
  stripe_account_id: string;
  onboarding_url: string;
}

export interface EarningsItem {
  transfer_id: string;
  amount_cents: number;
  currency: string;
  created: number; // Unix timestamp
  description: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getConnectStatus(teacherId: string): Promise<ConnectStatus> {
  const res = await schoolApi.get<ConnectStatus>(
    `/teachers/${teacherId}/connect/status`,
  );
  return res.data;
}

export async function startConnectOnboarding(
  teacherId: string,
): Promise<ConnectOnboardResult> {
  const res = await schoolApi.post<ConnectOnboardResult>(
    `/teachers/${teacherId}/connect/onboard`,
  );
  return res.data;
}

export async function refreshConnectLink(
  teacherId: string,
): Promise<{ onboarding_url: string }> {
  const res = await schoolApi.post<{ onboarding_url: string }>(
    `/teachers/${teacherId}/connect/refresh`,
  );
  return res.data;
}

export async function getConnectEarnings(
  teacherId: string,
  limit = 25,
): Promise<EarningsItem[]> {
  const res = await schoolApi.get<EarningsItem[]>(
    `/teachers/${teacherId}/connect/earnings`,
    { params: { limit } },
  );
  return res.data;
}

export async function createStudentCheckoutSession(
  teacherId: string,
  studentId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  const res = await schoolApi.post<{ checkout_url: string }>(
    `/teachers/${teacherId}/connect/student-checkout`,
    { student_id: studentId, success_url: successUrl, cancel_url: cancelUrl },
  );
  return res.data;
}
