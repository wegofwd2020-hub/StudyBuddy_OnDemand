"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { BookOpen, CheckCircle } from "lucide-react";

import { requestDemo, resendDemoVerification } from "@/lib/api/demo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Request a demo account (#663).
 *
 * The public sign-in page has always linked here — `/demo` — but the route did
 * not exist: `app/(public)/demo/` held only subroutes (`login`, `verify/[token]`,
 * the story pages), so the link 404'd on the page in front of every prospective
 * school.
 *
 * The rest of the flow was already built and working: `POST /demo/request`, the
 * verification email, `/demo/verify/[token]`, and `/demo/login`. Even the form
 * existed, as `components/demo/DemoRequestModal` — which nothing rendered. So
 * the whole feature was reachable only by typing a URL nobody knew.
 *
 * This is the missing entry point rather than a new feature, and it reuses the
 * existing `demo.*` i18n keys and error handling rather than inventing a second
 * vocabulary for the same states.
 */

const schema = z.object({
  email: z.string().email("Valid email required"),
});

type FormData = z.infer<typeof schema>;

type ErrorKey =
  | "error_rate_limited"
  | "error_pending"
  | "error_already_active"
  | "error_generic";

/** Same mapping as the modal — the API's states, not new ones. */
function resolveErrorKey(status: number | undefined, code: string | undefined): ErrorKey {
  if (status === 429) return "error_rate_limited";
  if (status === 409 && code === "verification_pending") return "error_pending";
  if (status === 409 && code === "demo_already_active") return "error_already_active";
  return "error_generic";
}

export default function DemoRequestPage() {
  const t = useTranslations("demo");
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [errorKey, setErrorKey] = useState<ErrorKey | null>(null);
  const [pendingEmail, setPendingEmail] = useState("");
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "failed">(
    "idle",
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setErrorKey(null);
    setResendState("idle");
    try {
      await requestDemo(data.email);
      setSubmittedEmail(data.email);
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { status?: number; data?: { error?: string } };
      };
      const key = resolveErrorKey(
        axiosErr.response?.status,
        axiosErr.response?.data?.error,
      );
      setErrorKey(key);
      if (key === "error_pending") setPendingEmail(data.email);
    }
  }

  async function handleResend() {
    if (!pendingEmail) return;
    setResendState("sending");
    try {
      await resendDemoVerification(pendingEmail);
      setResendState("sent");
    } catch {
      setResendState("failed");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col justify-center px-4 py-16">
      <Card>
        <CardContent className="p-6">
          {submittedEmail ? (
            <div className="space-y-4 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-50">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">{t("success_title")}</h1>
              <p className="text-sm text-gray-500">
                {t("success_body", { email: submittedEmail })}
              </p>
              <Link
                href="/demo/login"
                className="inline-block text-sm text-blue-600 hover:underline"
              >
                {t("sign_in_demo")}
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-6 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
                  <BookOpen className="h-6 w-6 text-blue-600" />
                </div>
                <h1 className="text-xl font-bold text-gray-900">{t("modal_title")}</h1>
                <p className="mt-1 text-sm text-gray-500">{t("modal_description")}</p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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

                {errorKey && (
                  <div className="space-y-2">
                    <p className="text-sm text-red-500">{t(errorKey)}</p>
                    {errorKey === "error_pending" && (
                      <div className="text-xs text-gray-500">
                        {resendState === "sent" ? (
                          <p className="text-green-600">
                            Verification email resent. Check your inbox.
                          </p>
                        ) : resendState === "failed" ? (
                          <p className="text-red-500">Resend failed. Please try again.</p>
                        ) : (
                          <p>
                            {t("resend_label")}{" "}
                            <button
                              type="button"
                              disabled={resendState === "sending"}
                              onClick={handleResend}
                              className="text-blue-600 hover:underline disabled:opacity-50"
                            >
                              {t("resend_link")}
                            </button>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? t("submitting") : t("submit_btn")}
                </Button>
              </form>

              <div className="mt-6 space-y-1 text-center text-sm text-gray-500">
                <p>
                  {t("already_have_demo")}{" "}
                  <Link href="/demo/login" className="text-blue-600 hover:underline">
                    {t("sign_in_demo")}
                  </Link>
                </p>
                <p>
                  Looking for a school account?{" "}
                  <Link href="/signin" className="text-blue-600 hover:underline">
                    Sign in
                  </Link>
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
