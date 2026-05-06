import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

// Attach JWT from localStorage on every request (client-side only)
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("sb_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error handling
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    if (typeof window !== "undefined") {
      if (status === 401) {
        localStorage.removeItem("sb_token");
        window.location.href = "/login";
      }
      // 402 → /paywall redirect intentionally disabled while the library-metaphor
      // redesign is being iterated. Re-enable when subscription gating is ready.
    }
    return Promise.reject(error);
  },
);

export default api;
