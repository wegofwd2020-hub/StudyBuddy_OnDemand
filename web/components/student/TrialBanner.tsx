"use client";

import { useSubscription, trialDaysRemaining } from "@/lib/hooks/useSubscription";
import { LinkButton } from "@/components/ui/link-button";
import { Clock } from "lucide-react";

export function TrialBanner() {
  const { data: sub } = useSubscription();

  if (!sub || sub.status !== "trial") return null;

  const days = trialDaysRemaining(sub.trial_ends_at);
  if (days === null) return null;

  const urgent = days <= 3;

  return (
    <div
      className={`flex items-center justify-between gap-3 px-4 py-2 text-sm ${
        urgent
          ? "border-b border-red-200 bg-red-50 text-red-800"
          : "border-b border-blue-100 bg-blue-50 text-blue-800"
      }`}
    >
      <span className="flex items-center gap-2">
        <Clock className="h-4 w-4 shrink-0" />
        {days === 0
          ? "Your free trial ends today."
          : `${days} day${days === 1 ? "" : "s"} left in your free trial.`}
      </span>
      <LinkButton href="/account/subscription" size="sm" className="h-7 shrink-0 text-xs">
        Upgrade now
      </LinkButton>
    </div>
  );
}
