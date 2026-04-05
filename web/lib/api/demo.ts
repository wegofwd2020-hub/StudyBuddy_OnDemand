import api from "./client";

export interface DemoRequestResponse {
  message: string;
}

export interface DemoLoginResponse {
  access_token: string;
  token_type: string;
  demo_expires_at: string;
}

/**
 * POST /demo/request
 * Submit email to request a 24-hour demo account.
 * Public endpoint — no auth required.
 */
export async function requestDemo(email: string): Promise<DemoRequestResponse> {
  const res = await api.post<DemoRequestResponse>("/demo/request", { email });
  return res.data;
}

/**
 * POST /demo/auth/login
 * Authenticate with demo credentials (email + password).
 * Returns JWT with role=demo_student.
 */
export async function demoLogin(
  email: string,
  password: string,
): Promise<DemoLoginResponse> {
  const res = await api.post<DemoLoginResponse>("/demo/auth/login", {
    email,
    password,
  });
  return res.data;
}

/**
 * POST /demo/auth/logout
 * Blacklists the demo JWT JTI in Redis.
 * Requires Authorization: Bearer <demo_token>.
 */
export async function demoLogout(token: string): Promise<void> {
  await api.post(
    "/demo/auth/logout",
    {},
    { headers: { Authorization: `Bearer ${token}` } },
  );
}

/**
 * GET /demo/verify/{token}
 * Verify an email address and create the demo account.
 * Backend sends login credentials to the user's email on success.
 */
export async function verifyDemoEmail(token: string): Promise<DemoRequestResponse> {
  const res = await api.get<DemoRequestResponse>(`/demo/verify/${token}`);
  return res.data;
}

/**
 * POST /demo/verify/resend
 * Resend the verification email for a pending demo request.
 */
export async function resendDemoVerification(email: string): Promise<void> {
  await api.post("/demo/verify/resend", { email });
}

// ── Teacher demo API ──────────────────────────────────────────────────────────

/**
 * POST /demo/teacher/request
 * Submit email to request a 48-hour teacher demo account.
 */
export async function requestTeacherDemo(email: string): Promise<DemoRequestResponse> {
  const res = await api.post<DemoRequestResponse>("/demo/teacher/request", { email });
  return res.data;
}

/**
 * POST /demo/teacher/auth/login
 * Authenticate with teacher demo credentials (email + password).
 * Returns JWT with role=demo_teacher.
 */
export async function demoTeacherLogin(
  email: string,
  password: string,
): Promise<DemoLoginResponse> {
  const res = await api.post<DemoLoginResponse>("/demo/teacher/auth/login", {
    email,
    password,
  });
  return res.data;
}

/**
 * POST /demo/teacher/auth/logout
 * Blacklists the demo teacher JWT JTI in Redis.
 */
export async function demoTeacherLogout(token: string): Promise<void> {
  await api.post(
    "/demo/teacher/auth/logout",
    {},
    { headers: { Authorization: `Bearer ${token}` } },
  );
}

/**
 * GET /demo/teacher/verify/{token}
 * Verify a teacher email address and create the demo teacher account.
 */
export async function verifyDemoTeacherEmail(
  token: string,
): Promise<DemoRequestResponse> {
  const res = await api.get<DemoRequestResponse>(`/demo/teacher/verify/${token}`);
  return res.data;
}

/**
 * POST /demo/teacher/verify/resend
 * Resend the teacher verification email for a pending demo request.
 */
export async function resendDemoTeacherVerification(email: string): Promise<void> {
  await api.post("/demo/teacher/verify/resend", { email });
}
