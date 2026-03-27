/**
 * Axios client for the school portal.
 * Reads the teacher JWT from localStorage key `sb_teacher_token`.
 * 401 → redirect to /school/login (separate from the student /login flow).
 */
import axios from "axios";

const schoolApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
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

schoolApi.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    if (typeof window !== "undefined" && status === 401) {
      localStorage.removeItem("sb_teacher_token");
      window.location.href = "/school/login";
    }
    return Promise.reject(error);
  },
);

export default schoolApi;
