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
import { BookOpen, School, ShieldCheck, Loader2, AlertCircle } from "lucide-react";

type DevRole = "student" | "teacher" | "school_admin";

async function loginAs(role: DevRole): Promise<void> {
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

interface LoginButtonProps {
  role: DevRole;
  label: string;
  sublabel: string;
  icon: React.ReactNode;
  colorClass: string;
  loading: DevRole | null;
  onClick: (role: DevRole) => void;
}

function LoginButton({ role, label, sublabel, icon, colorClass, loading, onClick }: LoginButtonProps) {
  const isLoading = loading === role;
  return (
    <button
      onClick={() => onClick(role)}
      disabled={loading !== null}
      className={`w-full flex items-center gap-3 px-4 py-3 ${colorClass} disabled:opacity-50 text-white font-medium rounded-xl transition-colors`}
    >
      <span className="shrink-0">
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      </span>
      <span className="text-left">
        <span className="block text-sm font-semibold">{label}</span>
        <span className="block text-xs opacity-80">{sublabel}</span>
      </span>
    </button>
  );
}

export default function DevLoginPage() {
  const [loading, setLoading] = useState<DevRole | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(role: DevRole) {
    setLoading(role);
    setError(null);
    try {
      await loginAs(role);
      const dest = role === "student" ? "/dashboard" : "/school/dashboard";
      window.location.href = dest;
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
          <LoginButton
            role="student"
            label="Student — Grade 8"
            sublabel="dev.student@studybuddy.dev"
            icon={<BookOpen className="h-4 w-4" />}
            colorClass="bg-indigo-600 hover:bg-indigo-500"
            loading={loading}
            onClick={handleLogin}
          />
          <LoginButton
            role="teacher"
            label="Teacher"
            sublabel="dev.teacher@studybuddy.dev"
            icon={<School className="h-4 w-4" />}
            colorClass="bg-emerald-600 hover:bg-emerald-500"
            loading={loading}
            onClick={handleLogin}
          />
          <LoginButton
            role="school_admin"
            label="School Admin"
            sublabel="dev.schooladmin@studybuddy.dev"
            icon={<ShieldCheck className="h-4 w-4" />}
            colorClass="bg-violet-600 hover:bg-violet-500"
            loading={loading}
            onClick={handleLogin}
          />
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div className="mt-6 pt-5 border-t border-gray-100 text-center space-y-1">
          <p className="text-xs text-gray-400">
            Super Admin →{" "}
            <a href="/admin/login" className="text-indigo-500 hover:underline">
              /admin/login
            </a>
            {" "}· password: <code className="text-gray-600">DevAdmin1234!</code>
          </p>
          <p className="text-xs text-gray-400">
            Email: <code className="text-gray-600">dev.admin@studybuddy.dev</code>
          </p>
        </div>
      </div>
    </div>
  );
}
