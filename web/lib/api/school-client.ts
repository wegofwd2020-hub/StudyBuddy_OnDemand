/**
 * Axios client for the school portal.
 * Reads the teacher JWT from localStorage key `sb_teacher_token`.
 *
 * On 401: attempts one silent refresh using `sb_teacher_refresh_token` via
 * POST /auth/refresh. On success the new access token is stored and the
 * original request is retried. On refresh failure (expired / revoked) all
 * local-auth tokens and the session cookie are cleared and the user is
 * redirected to /school/login.
 */
import axios, { AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const schoolApi = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

schoolApi.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("sb_teacher_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Track whether a refresh is in progress to avoid concurrent refresh calls.
let refreshing: Promise<string> | null = null;

function clearLocalAuthSession() {
  localStorage.removeItem("sb_teacher_token");
  localStorage.removeItem("sb_teacher_refresh_token");
  document.cookie = "sb_local_teacher_session=; path=/; SameSite=Strict; Max-Age=0";
}

async function attemptRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem("sb_teacher_refresh_token");
  if (!refreshToken) throw new Error("no_refresh_token");

  const res = await axios.post<{ token: string }>(
    `${BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" }, timeout: 10_000 },
  );
  const newToken = res.data.token;
  localStorage.setItem("sb_teacher_token", newToken);
  return newToken;
}

schoolApi.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const status = error.response?.status;

    // Only attempt refresh for 401s on local-auth sessions with a refresh token.
    if (
      typeof window !== "undefined" &&
      status === 401 &&
      localStorage.getItem("sb_teacher_refresh_token") &&
      // Prevent infinite loop if the refresh request itself 401s.
      !(error.config as { _retried?: boolean })?._retried
    ) {
      try {
        if (!refreshing) {
          refreshing = attemptRefresh().finally(() => { refreshing = null; });
        }
        const newToken = await refreshing;

        // Retry the original request with the fresh token.
        const retryConfig = { ...error.config, _retried: true } as typeof error.config & { _retried: boolean };
        if (retryConfig.headers) {
          retryConfig.headers.Authorization = `Bearer ${newToken}`;
        }
        return schoolApi(retryConfig);
      } catch {
        // Refresh failed — clear everything and force re-login.
        clearLocalAuthSession();
        window.location.href = "/school/login";
        return Promise.reject(error);
      }
    }

    // Non-401 or no refresh token available: clear session if 401 and redirect.
    if (typeof window !== "undefined" && status === 401) {
      clearLocalAuthSession();
      window.location.href = "/school/login";
    }

    return Promise.reject(error);
  },
);

export default schoolApi;
