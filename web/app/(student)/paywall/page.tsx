import { useTranslations } from "next-intl";
import { LinkButton } from "@/components/ui/link-button";
import { Lock } from "lucide-react";

export default function PaywallPage() {
  const t = useTranslations("subscription_screen");

  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
        <Lock className="h-8 w-8 text-amber-500" />
      </div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        {t("school_managed_title")}
      </h1>
      <p className="mb-8 max-w-md text-gray-500">{t("paywall_msg_school")}</p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <LinkButton href="/dashboard" size="lg">
          {t("back_to_dashboard")}
        </LinkButton>
      </div>
      <p className="mt-4 max-w-md text-xs text-gray-400">{t("school_managed_help")}</p>
    </div>
  );
}
