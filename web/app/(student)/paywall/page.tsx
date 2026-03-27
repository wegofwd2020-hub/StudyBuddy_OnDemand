import { useTranslations } from "next-intl";
import { LinkButton } from "@/components/ui/link-button";
import { Lock } from "lucide-react";

export default function PaywallPage() {
  const t = useTranslations("subscription_screen");

  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50 mb-4">
        <Lock className="h-8 w-8 text-amber-500" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">{t("title")}</h1>
      <p className="text-gray-500 max-w-md mb-8">
        {t("paywall_msg")}
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <LinkButton href="/account/subscription" size="lg">
          {t("subscribe_btn")} — $9.99/month
        </LinkButton>
        <LinkButton href="/dashboard" variant="outline" size="lg">
          Back to Dashboard
        </LinkButton>
      </div>
      <p className="mt-4 text-xs text-gray-400">
        Annual plan available at $99.99/year — {t("annual_savings")}
      </p>
    </div>
  );
}
