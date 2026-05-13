"use client";

import { Lock } from "lucide-react";
import { IS_DEMO_MODE } from "@/lib/demo-mode";

/**
 * Demo-mode banner shown on pages whose primary action is gated behind a paid
 * subscription. Renders nothing in non-demo (production / staging) — the page
 * shows its real controls. In demo mode it sits at the top of the page and
 * the controls below should be `disabled={IS_DEMO_MODE}`.
 */
export function PendingSubscriptionBanner({
  message,
}: {
  /**
   * Optional override for the banner copy. Defaults to a generic message
   * pointing the visitor at subscription as the unlock path.
   */
  message?: string;
}) {
  if (!IS_DEMO_MODE) return null;
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <Lock className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
      <div className="text-sm">
        <p className="font-semibold text-amber-900">Pending subscription</p>
        <p className="mt-0.5 text-amber-800">
          {message ??
            "This feature is available to schools with an active subscription. The controls below are read-only in this demo."}
        </p>
      </div>
    </div>
  );
}
