"use client";

import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { requestPasswordReset, resetPassword } from "@/lib/api/auth";
import { CheckCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const requestSchema = z.object({
  email: z.string().email("Valid email required"),
});

const resetSchema = z
  .object({
    password: z.string().min(8, "At least 8 characters"),
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
      setError("Reset failed. The link may have expired.");
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
          {token ? (
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
