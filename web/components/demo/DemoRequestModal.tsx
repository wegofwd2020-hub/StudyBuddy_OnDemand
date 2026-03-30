"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { CheckCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { requestDemo, resendDemoVerification } from "@/lib/api/demo";

const schema = z.object({
  email: z.string().email("Valid email required"),
});

type FormData = z.infer<typeof schema>;

type ErrorKey =
  | "error_rate_limited"
  | "error_pending"
  | "error_already_active"
  | "error_generic";

function resolveErrorKey(status: number | undefined, code: string | undefined): ErrorKey {
  if (status === 429) return "error_rate_limited";
  if (status === 409 && code === "verification_pending") return "error_pending";
  if (status === 409 && code === "demo_already_active") return "error_already_active";
  return "error_generic";
}

export function DemoRequestModal() {
  const t = useTranslations("demo");
  const [open, setOpen] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [errorKey, setErrorKey] = useState<ErrorKey | null>(null);
  const [pendingEmail, setPendingEmail] = useState("");
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      // Reset form state when dialog closes
      reset();
      setErrorKey(null);
      setSubmittedEmail("");
      setPendingEmail("");
      setResendState("idle");
    }
  }

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
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button size="lg" variant="outline">
            {t("hero_cta")}
          </Button>
        }
      />

      <DialogContent className="sm:max-w-md">
        {submittedEmail ? (
          /* ── Success state ─────────────────────────────────────────── */
          <>
            <DialogHeader>
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-50">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <DialogTitle className="text-center">{t("success_title")}</DialogTitle>
              <DialogDescription className="text-center">
                {t("success_body", { email: submittedEmail })}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button className="w-full" onClick={() => handleOpenChange(false)}>
                {t("success_close")}
              </Button>
            </DialogFooter>
          </>
        ) : (
          /* ── Request form ──────────────────────────────────────────── */
          <>
            <DialogHeader>
              <DialogTitle>{t("modal_title")}</DialogTitle>
              <DialogDescription>{t("modal_description")}</DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="demo-email">{t("email_label")}</Label>
                <Input
                  id="demo-email"
                  type="email"
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
                        <p className="text-green-600">Verification email resent. Check your inbox.</p>
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
                  )}
                </div>
              )}

              <DialogFooter showCloseButton={false} className="flex-col gap-2">
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? t("submitting") : t("submit_btn")}
                </Button>
                <p className="text-center text-xs text-gray-500">
                  {t("already_have_demo")}{" "}
                  <Link
                    href="/demo/login"
                    className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
                    onClick={() => handleOpenChange(false)}
                  >
                    {t("sign_in_demo")}
                  </Link>
                </p>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
