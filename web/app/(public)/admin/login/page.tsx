"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin } from "@/lib/api/admin";
import { BookOpen, AlertCircle } from "lucide-react";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { token } = await adminLogin(email, password);
      localStorage.setItem("sb_admin_token", token);
      router.push("/admin/dashboard");
    } catch (err: unknown) {
      const apiMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(apiMsg ?? "Invalid credentials. Please check your email and password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="h-7 w-7 text-indigo-400" />
          <span className="text-xl font-bold text-white">StudyBuddy</span>
          <span className="text-sm text-gray-400 font-medium mt-0.5">Admin</span>
        </div>

        <div className="bg-gray-800 rounded-xl border border-gray-700 p-8">
          <h1 className="text-lg font-semibold text-white mb-6 text-center">
            Sign in to admin console
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-300 mb-1.5"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-600 text-white placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="admin@studybuddy.ca"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-300 mb-1.5"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-600 text-white placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-gray-600">
          Internal access only. All activity is logged.
        </p>
      </div>
    </div>
  );
}
