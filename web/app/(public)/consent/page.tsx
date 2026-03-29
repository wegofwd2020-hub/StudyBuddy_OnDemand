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
import { submitConsent } from "@/lib/api/auth";
import { CheckCircle, ShieldCheck } from "lucide-react";

const schema = z.object({
  parent_name: z.string().min(2, "Name is required"),
  parent_email: z.string().email("Valid email required"),
  consent: z.literal(true, { error: "You must agree to continue" }),
});

type FormData = z.infer<typeof schema>;

export default function ConsentPage() {
  const t = useTranslations("coppa");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    try {
      // student_id comes from the URL or session in production
      const params = new URLSearchParams(window.location.search);
      await submitConsent({
        student_id: params.get("student_id") ?? "",
        parent_name: data.parent_name,
        parent_email: data.parent_email,
      });
      setDone(true);
    } catch {
      setError("Submission failed. Please try again.");
    }
  }

  if (done) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4">
        <div className="space-y-3 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-2xl font-bold">{t("success_heading")}</h1>
          <p className="text-gray-500">{t("success_body")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-amber-50">
            <ShieldCheck className="h-6 w-6 text-amber-600" />
          </div>
          <CardTitle className="text-2xl">{t("heading")}</CardTitle>
          <p className="text-sm text-gray-500">{t("subheading")}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="parent_name">{t("parent_name_label")}</Label>
              <Input id="parent_name" {...register("parent_name")} />
              {errors.parent_name && (
                <p className="text-xs text-red-500">{errors.parent_name.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="parent_email">{t("parent_email_label")}</Label>
              <Input id="parent_email" type="email" {...register("parent_email")} />
              {errors.parent_email && (
                <p className="text-xs text-red-500">{errors.parent_email.message}</p>
              )}
            </div>
            <div className="flex items-start gap-2">
              <input
                id="consent"
                type="checkbox"
                className="mt-1"
                {...register("consent")}
              />
              <Label
                htmlFor="consent"
                className="cursor-pointer text-sm font-normal text-gray-600"
              >
                {t("consent_checkbox")}
              </Label>
            </div>
            {errors.consent && (
              <p className="text-xs text-red-500">{errors.consent.message}</p>
            )}
            {error && <p className="text-xs text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Submitting…" : t("submit_btn")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
