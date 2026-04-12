"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { School, Eye, EyeOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { localLogin } from "@/lib/api/auth";

export default function SchoolLoginPage() {
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
      const res = await localLogin({ email, password });
      // Store token in the key each portal reads from localStorage
      if (res.role === "student") {
        localStorage.setItem("sb_token", res.token);
      } else {
        // school_admin and teacher both use sb_teacher_token — school Axios
        // client and useTeacher hook read from this key.
        localStorage.setItem("sb_teacher_token", res.token);
        // Set a lightweight session cookie so the server layout can detect the
        // local-auth session and skip the Auth0 redirect. Encoded the same way
        // as sb_teacher_session (base64 JSON) for consistency.
        const sessionPayload = btoa(JSON.stringify({ name: email, email }));
        document.cookie = `sb_local_teacher_session=${sessionPayload}; path=/; SameSite=Strict; Max-Age=86400`;
      }
      if (res.first_login) {
        router.push("/school/change-password?required=1");
      } else if (res.role === "student") {
        router.push("/student");
      } else {
        router.push("/school/dashboard");
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError("Incorrect email or password.");
      } else if (status === 429) {
        setError("Too many attempts. Please wait a moment and try again.");
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
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
            <School className="h-6 w-6 text-indigo-600" />
          </div>
          <CardTitle className="text-2xl">School Sign In</CardTitle>
          <p className="text-sm text-gray-500">
            Sign in with the credentials your school provided
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
                onChange={(e) => { setEmail(e.target.value); setError(null); }}
                placeholder="you@school.edu"
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
                  onChange={(e) => { setPassword(e.target.value); setError(null); }}
                  placeholder="••••••••••••"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full bg-indigo-600 hover:bg-indigo-700"
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="text-center text-sm text-gray-500">
            Looking for student sign in?{" "}
            <Link href="/login" className="text-blue-600 hover:underline">
              Student login
            </Link>
          </p>
          <p className="text-center text-sm text-gray-500">
            Don&apos;t have a school account?{" "}
            <Link href="/contact" className="text-blue-600 hover:underline">
              Contact us
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
