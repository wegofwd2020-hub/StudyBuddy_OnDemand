import axios from "axios";
import api from "./client";

// Unauthenticated Axios instance for login endpoints (no Bearer token pre-injected)
const publicApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function exchangeToken(idToken: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/auth/exchange", {
    id_token: idToken,
  });
  return res.data;
}

export async function exchangeTeacherToken(idToken: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/auth/teacher/exchange", {
    id_token: idToken,
  });
  return res.data;
}

export async function requestPasswordReset(email: string): Promise<void> {
  await api.post("/auth/forgot-password", { email });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post("/auth/reset-password", { token, new_password: newPassword });
}

export async function submitConsent(data: {
  student_id: string;
  parent_name: string;
  parent_email: string;
}): Promise<void> {
  await api.post("/auth/consent", data);
}

// ── Phase A — local auth (school-provisioned users) ───────────────────────────

export interface LocalLoginRequest {
  email: string;
  password: string;
}

export interface LocalLoginResponse {
  token: string;
  refresh_token: string;
  /** "school_admin" | "teacher" | "student" */
  role: string;
  /** When true the client must redirect to /school/change-password before any nav */
  first_login: boolean;
  user_id: string;
}

/**
 * Email + password login for school-provisioned teachers, school admins, and students.
 * Uses an unauthenticated Axios instance — no Bearer token pre-injected.
 * On success store the token in localStorage:
 *   - teachers / school_admins → "sb_teacher_token"
 *   - students               → "sb_token"
 */
export async function localLogin(body: LocalLoginRequest): Promise<LocalLoginResponse> {
  const res = await publicApi.post<LocalLoginResponse>("/auth/login", body);
  return res.data;
}

export interface ChangePasswordRequest {
  current_password: string;
  /** Must be ≥12 chars, ≤72 bytes */
  new_password: string;
}

export interface ChangePasswordResponse {
  /** Fresh JWT with first_login=false — client must replace the stored token. */
  token: string;
  refresh_token: string;
  role: string;
}

/**
 * Change password for a local-auth user.
 * Returns a fresh JWT with first_login=false so the client can replace the
 * stored token immediately without requiring another login round-trip.
 * Pass the current token explicitly — publicApi has no Bearer pre-injected.
 */
export async function changePassword(
  token: string,
  body: ChangePasswordRequest,
): Promise<ChangePasswordResponse> {
  const res = await publicApi.patch<ChangePasswordResponse>(
    "/auth/change-password",
    body,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return res.data;
}
