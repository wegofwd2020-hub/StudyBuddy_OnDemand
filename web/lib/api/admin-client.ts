/**
 * Axios client for the admin console.
 * Reads the admin JWT from localStorage key `sb_admin_token`.
 * 401 → redirect to /admin/login (separate from student and school auth flows).
 */
import axios from "axios";

const adminApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

adminApi.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("sb_admin_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

adminApi.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    if (typeof window !== "undefined" && status === 401) {
      localStorage.removeItem("sb_admin_token");
      window.location.href = "/admin/login";
    }
    return Promise.reject(error);
  },
);

export default adminApi;
