"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { School, Eye, EyeOff, Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { registerSchool } from "@/lib/api/auth";

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "GB", name: "United Kingdom" },
  { code: "AU", name: "Australia" },
  { code: "NZ", name: "New Zealand" },
  { code: "IN", name: "India" },
  { code: "NG", name: "Nigeria" },
  { code: "ZA", name: "South Africa" },
  { code: "KE", name: "Kenya" },
  { code: "GH", name: "Ghana" },
  { code: "OTHER", name: "Other" },
];

export default function SchoolRegisterPage() {
  const router = useRouter();

  const [schoolName, setSchoolName] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("CA");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await registerSchool({
        school_name: schoolName,
        contact_email: email,
        country,
        password,
      });

      // Store the JWT and set the session cookie — founder is now authenticated.
      localStorage.setItem("sb_teacher_token", res.access_token);
      const sessionPayload = btoa(JSON.stringify({ name: email, email }));
      document.cookie = `sb_local_teacher_session=${sessionPayload}; path=/; SameSite=Strict; Max-Age=86400`;

      router.push("/school/dashboard");
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setError("A school with that email already exists. Try signing in instead.");
      } else if (status === 422) {
        const detail = (err as { response?: { data?: { detail?: unknown } } })
          ?.response?.data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? (detail[0] as { msg?: string })?.msg ?? "Validation error."
            : "Invalid details. Please check your entries.";
        setError(msg);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  const canSubmit =
    !loading && schoolName && email && country && password && confirmPassword;

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
            <School className="h-6 w-6 text-indigo-600" />
          </div>
          <CardTitle className="text-2xl">Register Your School</CardTitle>
          <p className="text-sm text-gray-500">
            Create a school account to manage teachers and students.
          </p>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="school_name">School name</Label>
              <Input
                id="school_name"
                value={schoolName}
                onChange={(e) => { setSchoolName(e.target.value); setError(null); }}
                placeholder="Westview Academy"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="contact_email">Contact email</Label>
              <Input
                id="contact_email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(null); }}
                placeholder="admin@westview.edu"
                required
              />
              <p className="text-xs text-gray-400">
                This becomes your login email and is visible to teachers.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="country">Country</Label>
              <select
                id="country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="h-9 w-full rounded-md border border-gray-200 bg-white px-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                required
              >
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(null); }}
                  placeholder="At least 12 characters"
                  className="pr-10"
                  required
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
              <p className="text-xs text-gray-400">Minimum 12 characters</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirm_password">Confirm password</Label>
              <div className="relative">
                <Input
                  id="confirm_password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => { setConfirmPassword(e.target.value); setError(null); }}
                  placeholder="Repeat password"
                  className="pr-10"
                  required
                />
                {confirmPassword && password === confirmPassword && (
                  <Check className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-green-500" />
                )}
              </div>
            </div>

            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}

            <Button
              type="submit"
              disabled={!canSubmit}
              className="w-full bg-indigo-600 hover:bg-indigo-700"
            >
              {loading ? "Creating account…" : "Create school account"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link href="/school/login" className="text-indigo-600 hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
