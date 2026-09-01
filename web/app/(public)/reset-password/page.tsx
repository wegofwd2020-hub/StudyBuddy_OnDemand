"use client";

import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { checkResetToken, requestPasswordReset, resetPassword } from "@/lib/api/auth";
import { CheckCircle, AlertCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const requestSchema = z.object({
  email: z.string().email("Valid email required"),
});

const resetSchema = z
  .object({
    password: z.string().min(12, "At least 12 characters"),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

function ResetPasswordInner() {
  const t = useTranslations("auth");
  const params = useSearchParams();
  const token = params.get("token");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  // Whether the token in the URL is still usable.
  //
  // This page used to gate purely on the token being PRESENT, never on it being
  // valid, so an expired link rendered "Set new password" exactly like a good
  // one and the expiry only surfaced after the user had typed a new password
  // twice and pressed the button. A tester read that as "the link still works
  // hours later"; the link did not work, but nothing on screen said so.
  //
  // `undefined` = still asking. Rendering the form during that window would
  // reintroduce the same flash of a form that is about to be replaced.
  const [tokenValid, setTokenValid] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    checkResetToken(token).then((valid) => {
      if (!cancelled) setTokenValid(valid);
    });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const requestForm = useForm<z.infer<typeof requestSchema>>({
    resolver: zodResolver(requestSchema),
  });

  const resetForm = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
  });

  async function onRequestSubmit(data: z.infer<typeof requestSchema>) {
    try {
      await requestPasswordReset(data.email);
      setDone(true);
    } catch {
      // Always show success per security rule (backend always returns 200)
      setDone(true);
    }
  }

  async function onResetSubmit(data: z.infer<typeof resetSchema>) {
    try {
      await resetPassword(token!, data.password);
      setDone(true);
    } catch {
      // The token can lapse WHILE the form is being filled in — the TTL is an
      // hour from issue, not from page load. Re-ask rather than guess: if it is
      // genuinely gone, show the expired screen with its "request a new link"
      // action instead of an inline sentence that offers no way forward.
      const stillValid = await checkResetToken(token!);
      if (!stillValid) {
        setTokenValid(false);
        return;
      }
      setError("Reset failed. Please try again.");
    }
  }

  if (done) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4">
        <div className="space-y-3 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-xl font-bold">
            {token ? "Password updated!" : t("reset_email_sent")}
          </h1>
        </div>
      </div>
    );
  }

  // Expired, already used, or never valid. Say so here rather than letting the
  // student fill the form in and discover it at submit — and offer the one
  // action that actually helps, which is asking for a fresh link.
  if (token && tokenValid === false) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
        <Card className="w-full max-w-sm shadow-lg">
          <CardHeader className="text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-orange-500" />
            <CardTitle className="mt-2 text-xl">This link has expired</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-gray-600">
              Password reset links last one hour and can only be used once. Request a new
              one and we&apos;ll email it to you.
            </p>
            <LinkButton href="/reset-password" className="w-full">
              Request a new link
            </LinkButton>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">
            {token ? t("new_password_title") : t("reset_password_title")}
          </CardTitle>
          {!token && (
            <p className="text-sm text-gray-500">{t("reset_password_subtitle")}</p>
          )}
        </CardHeader>
        <CardContent>
          {token && tokenValid === undefined ? (
            // One round-trip. Showing the form first and swapping it for the
            // expired notice is the flash this whole change exists to remove.
            <p className="py-6 text-center text-sm text-gray-500">Checking your link…</p>
          ) : token ? (
            <form onSubmit={resetForm.handleSubmit(onResetSubmit)} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="password">{t("password_label")}</Label>
                <Input
                  id="password"
                  type="password"
                  {...resetForm.register("password")}
                />
                {resetForm.formState.errors.password && (
                  <p className="text-xs text-red-500">
                    {resetForm.formState.errors.password.message}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="confirm">Confirm password</Label>
                <Input id="confirm" type="password" {...resetForm.register("confirm")} />
                {resetForm.formState.errors.confirm && (
                  <p className="text-xs text-red-500">
                    {resetForm.formState.errors.confirm.message}
                  </p>
                )}
              </div>
              {error && <p className="text-xs text-red-500">{error}</p>}
              <Button
                type="submit"
                className="w-full"
                disabled={resetForm.formState.isSubmitting}
              >
                {t("set_new_password")}
              </Button>
            </form>
          ) : (
            <form
              onSubmit={requestForm.handleSubmit(onRequestSubmit)}
              className="space-y-4"
            >
              <div className="space-y-1">
                <Label htmlFor="email">{t("email_label")}</Label>
                <Input id="email" type="email" {...requestForm.register("email")} />
                {requestForm.formState.errors.email && (
                  <p className="text-xs text-red-500">
                    {requestForm.formState.errors.email.message}
                  </p>
                )}
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={requestForm.formState.isSubmitting}
              >
                {t("send_reset_link")}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordInner />
    </Suspense>
  );
}
