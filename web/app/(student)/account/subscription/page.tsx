"use client";

import { useTranslations } from "next-intl";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { School } from "lucide-react";

/**
 * Students do not buy their own subscriptions.
 *
 * This page used to offer self-serve plans, checkout, cancellation and a
 * billing portal. Individual student subscriptions were removed in migration
 * 0027 (ADR-001) — the school is the billing entity — so every one of those
 * actions had been calling endpoints that no longer exist and returned 404
 * (#604). Rather than leave buttons that cannot work, the page now says who
 * actually controls access.
 */
export default function StudentSubscriptionPage() {
  const t = useTranslations("subscription_screen");

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <School className="h-5 w-5 text-gray-500" aria-hidden="true" />
            {t("school_managed_title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-600">{t("school_managed_body")}</p>
          <p className="text-sm text-gray-500">{t("school_managed_help")}</p>
          <LinkButton href="/dashboard" size="lg">
            {t("back_to_dashboard")}
          </LinkButton>
        </CardContent>
      </Card>
    </div>
  );
}
