"use client";

/**
 * /dev-login
 *
 * Development-only login bypass. Calls the backend POST /auth/dev-login
 * endpoint to get a long-lived JWT, stores it in localStorage, sets the
 * sb_dev_session cookie (read by server layouts as an Auth0 fallback),
 * then redirects to the appropriate portal.
 *
 * This page intentionally has no production guard — it simply won't work
 * if the backend dev-login endpoint is absent (non-development backend).
 */

import { useState } from "react";
import { BookOpen, School, Loader2, AlertCircle } from "lucide-react";

async function loginAs(role: "student" | "teacher"): Promise<void> {
  // Calls the Next.js proxy route (/api/dev-login) to avoid CORS
  const res = await fetch("/api/dev-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }

  const data = await res.json() as {
    token: string;
    name: string;
    email: string;
    role: string;
  };

  // Store token in localStorage (used by API clients)
  const tokenKey = role === "student" ? "sb_token" : "sb_teacher_token";
  localStorage.setItem(tokenKey, data.token);

  // Set sb_dev_session cookie so server-side layouts can read name/email
  const payload = btoa(JSON.stringify({ name: data.name, email: data.email }));
  // 7-day expiry — same as the token lifetime
  document.cookie = `sb_dev_session=${payload}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export default function DevLoginPage() {
  const [loading, setLoading] = useState<"student" | "teacher" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(role: "student" | "teacher") {
    setLoading(role);
    setError(null);
    try {
      await loginAs(role);
      window.location.href = role === "student" ? "/dashboard" : "/school/dashboard";
    } catch (err: unknown) {
      setError((err as Error).message ?? "Login failed.");
      setLoading(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm w-full max-w-sm p-8">
        <div className="text-center mb-8">
          <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-700 mb-3">
            DEV ONLY
          </span>
          <h1 className="text-xl font-bold text-gray-900">Test Login</h1>
          <p className="text-sm text-gray-500 mt-1">
            Bypass Auth0 for local development testing.
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => handleLogin("student")}
            disabled={loading !== null}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium rounded-xl transition-colors"
          >
            {loading === "student" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BookOpen className="h-4 w-4" />
            )}
            Login as Student (Grade 8)
          </button>

          <button
            onClick={() => handleLogin("teacher")}
            disabled={loading !== null}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium rounded-xl transition-colors"
          >
            {loading === "teacher" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <School className="h-4 w-4" />
            )}
            Login as Teacher
          </button>
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <p className="text-xs text-gray-400 text-center mt-6">
          Admin login →{" "}
          <a href="/admin/login" className="text-indigo-500 hover:underline">
            /admin/login
          </a>
        </p>
      </div>
    </div>
  );
}
