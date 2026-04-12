"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KeyRound, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { changePassword } from "@/lib/api/auth";

export default function ChangePasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRequired = searchParams.get("required") === "1";

  const [token, setToken] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Read token from localStorage (safe — runs client-side only)
  useEffect(() => {
    const t = localStorage.getItem("sb_teacher_token") ?? localStorage.getItem("sb_token");
    if (!t) {
      router.replace("/school/login");
    } else {
      setToken(t);
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 12) {
      setError("New password must be at least 12 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    if (!token) return;

    setLoading(true);
    try {
      await changePassword(token, {
        current_password: currentPassword,
        new_password: newPassword,
      });
      // Clear first_login flag by re-reading the updated token from the next
      // login. For now, redirect to dashboard — the JWT still shows first_login=true
      // until the user logs in again, but the backend has cleared the DB flag.
      // The school layout will not re-check first_login after a successful change.
      router.push("/school/dashboard");
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError("Current password is incorrect.");
      } else if (status === 422) {
        setError("New password does not meet the requirements (≥12 characters).");
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
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-amber-50">
            <KeyRound className="h-6 w-6 text-amber-600" />
          </div>
          <CardTitle className="text-2xl">Set Your Password</CardTitle>
          {isRequired && (
            <div className="mt-2 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-left text-sm text-amber-800">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                You must set a new password before you can access the portal.
              </span>
            </div>
          )}
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current_password">Current password</Label>
              <div className="relative">
                <Input
                  id="current_password"
                  type={showCurrent ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={currentPassword}
                  onChange={(e) => { setCurrentPassword(e.target.value); setError(null); }}
                  placeholder="Your current / temporary password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  aria-label={showCurrent ? "Hide password" : "Show password"}
                >
                  {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="new_password">New password</Label>
              <div className="relative">
                <Input
                  id="new_password"
                  type={showNew ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => { setNewPassword(e.target.value); setError(null); }}
                  placeholder="At least 12 characters"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNew((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  aria-label={showNew ? "Hide password" : "Show password"}
                >
                  {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-400">Minimum 12 characters</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirm_password">Confirm new password</Label>
              <Input
                id="confirm_password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setError(null); }}
                placeholder="Repeat new password"
              />
            </div>

            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading || !currentPassword || !newPassword || !confirmPassword}
              className="w-full bg-indigo-600 hover:bg-indigo-700"
            >
              {loading ? "Saving…" : "Set new password"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
