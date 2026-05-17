"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpen, Eye, EyeOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  universalLogin,
  type AuthTrack,
  type UniversalLoginResponse,
} from "@/lib/api/auth";

/**
 * Apply the auth_track-specific localStorage + cookie writes so each downstream
 * portal layout finds the token + session in the place it expects.
 *
 *   - sb_token / sb_teacher_token  — Axios clients read these for Bearer.
 *   - sb_local_*_session / sb_dev_session / sb_teacher_session — server layouts
 *     read these cookies (Strict, base64-encoded {name, email} JSON) to short-
 *     circuit the Auth0 redirect.
 *
 * Keep these key names in sync with components/school/LocalAuthGuard.tsx, the
 * school portal server layout, and the demo session cookie writers in
 * (public)/demo/login + demo/teacher/login.
 */
function persistSession(res: UniversalLoginResponse, email: string): void {
  const display = res.name || email;
  const sessionPayload = btoa(JSON.stringify({ name: display, email }));
  const secure = location.protocol === "https:" ? "; Secure" : "";

  if (res.auth_track === "local") {
    if (res.role === "student") {
      localStorage.setItem("sb_token", res.token);
      document.cookie = `sb_local_student_session=${sessionPayload}; path=/; SameSite=Strict; Max-Age=86400${secure}`;
    } else {
      localStorage.setItem("sb_teacher_token", res.token);
      if (res.refresh_token) {
        localStorage.setItem("sb_teacher_refresh_token", res.refresh_token);
      }
      document.cookie = `sb_local_teacher_session=${sessionPayload}; path=/; SameSite=Strict; Max-Age=86400${secure}`;
    }
    return;
  }

  if (res.auth_track === "demo_student") {
    // Demo student layout reads sb_dev_session (same encoding as the existing
    // /demo/login page wrote).
    localStorage.setItem("sb_token", res.token);
    const demoPayload = btoa(JSON.stringify({ name: "Demo Student", email }));
    document.cookie = `sb_dev_session=${demoPayload}; path=/; SameSite=Lax; Max-Age=86400${secure}`;
    return;
  }

  // demo_teacher
  localStorage.setItem("sb_teacher_token", res.token);
  // 48-hour cookie to match DEMO_TEACHER_ACCOUNT_TTL_HOURS.
  document.cookie = `sb_teacher_session=${sessionPayload}; path=/; SameSite=Lax; Max-Age=${60 * 60 * 48}${secure}`;
}

function destinationFor(
  track: AuthTrack,
  role: string,
  firstLogin: boolean | null,
): string {
  if (track === "local" && firstLogin) {
    return "/school/change-password?required=1";
  }
  if (role === "student") {
    return "/dashboard";
  }
  return "/school/dashboard";
}

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await universalLogin({ email, password });
      persistSession(res, email);
      router.push(destinationFor(res.auth_track, res.role, res.first_login));
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError("Incorrect email or password.");
      } else if (status === 403) {
        setError(
          "This account is suspended or has expired. Please contact your administrator.",
        );
      } else if (status === 429) {
        setError("Too many sign-in attempts. Please wait a moment and try again.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
            <BookOpen className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-2xl">Sign in to StudyBuddy</CardTitle>
          <p className="text-sm text-gray-500">
            One sign-in for students, teachers, and school admins
          </p>
        </CardHeader>

        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setError(null);
                }}
                placeholder="you@example.com"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError(null);
                  }}
                  placeholder="••••••••••••"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute top-1/2 right-3 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full"
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="space-y-2 text-center text-sm text-gray-500">
            <p>
              <Link
                href="/reset-password"
                className="text-gray-500 hover:text-gray-900 hover:underline"
              >
                Forgot your password?
              </Link>
            </p>
            <p>
              New school?{" "}
              <Link href="/school/register" className="text-blue-600 hover:underline">
                Register your school
              </Link>
            </p>
            <p>
              Try the demo?{" "}
              <Link href="/demo" className="text-blue-600 hover:underline">
                Request a demo account
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
