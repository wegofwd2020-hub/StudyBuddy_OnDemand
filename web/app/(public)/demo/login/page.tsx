"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { BookOpen, AlertCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { demoLogin, resendDemoVerification } from "@/lib/api/demo";

const schema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(1, "Password required"),
});

type FormData = z.infer<typeof schema>;

type LoginError =
  | "login_error_invalid"
  | "login_error_expired"
  | "login_error_generic";

function resolveLoginError(status: number | undefined, code: string | undefined): LoginError {
  if (status === 401) return "login_error_invalid";
  if (status === 403 && code === "demo_expired") return "login_error_expired";
  return "login_error_generic";
}

/** Write the demo session cookie so the server-side student layout can read name/email. */
function setDemoSessionCookie(email: string): void {
  const payload = btoa(JSON.stringify({ name: "Demo Student", email }));
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `sb_dev_session=${payload}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax${secure}`;
}

export default function DemoLoginPage() {
  const t = useTranslations("demo");
  const router = useRouter();
  const [errorKey, setErrorKey] = useState<LoginError | null>(null);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setErrorKey(null);
    try {
      const result = await demoLogin(data.email, data.password);
      localStorage.setItem("sb_token", result.access_token);
      setDemoSessionCookie(data.email);
      router.push("/dashboard");
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { status?: number; data?: { error?: string } };
      };
      setErrorKey(resolveLoginError(axiosErr.response?.status, axiosErr.response?.data?.error));
    }
  }

  async function handleResend() {
    const email = getValues("email");
    if (!email) return;
    setResendState("sending");
    try {
      await resendDemoVerification(email);
      setResendState("sent");
    } catch {
      setResendState("failed");
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        {/* Logo mark */}
        <div className="mb-8 flex items-center justify-center gap-2">
          <BookOpen className="h-6 w-6 text-blue-600" />
          <span className="text-lg font-bold text-gray-900">StudyBuddy</span>
          <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-semibold text-blue-700">
            Demo
          </span>
        </div>

        <div className="rounded-xl border bg-white p-8 shadow-sm">
          <h1 className="mb-1 text-center text-lg font-semibold text-gray-900">
            {t("login_title")}
          </h1>
          <p className="mb-6 text-center text-sm text-gray-500">{t("login_subtitle")}</p>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="demo-email">{t("email_label")}</Label>
              <Input
                id="demo-email"
                type="email"
                autoComplete="email"
                placeholder={t("email_placeholder")}
                aria-invalid={!!errors.email}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="demo-password">{t("password_label")}</Label>
              <Input
                id="demo-password"
                type="password"
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            {errorKey && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{t(errorKey)}</span>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? t("login_loading") : t("login_btn")}
            </Button>
          </form>

          {/* Resend credentials */}
          <div className="mt-5 border-t pt-4 text-center text-xs text-gray-500">
            {resendState === "sent" ? (
              <p className="text-green-600">Credentials email resent. Check your inbox.</p>
            ) : resendState === "failed" ? (
              <p className="text-red-500">Resend failed. Please try again.</p>
            ) : (
              <p>
                {t("resend_label")}{" "}
                <button
                  type="button"
                  disabled={resendState === "sending"}
                  onClick={handleResend}
                  className="text-blue-600 underline underline-offset-2 hover:text-blue-800 disabled:opacity-50"
                >
                  {resendState === "sending" ? "Sending…" : t("resend_link")}
                </button>
              </p>
            )}
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-gray-400">
          {t("already_have_demo")}{" "}
          <Link href="/" className="text-blue-600 underline underline-offset-2 hover:text-blue-800">
            {t("sign_in_demo")} →
          </Link>
        </p>
      </div>
    </div>
  );
}
