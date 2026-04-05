"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useSubscription, trialDaysRemaining } from "@/lib/hooks/useSubscription";
import {
  createCheckout,
  getBillingPortalUrl,
  cancelSubscription,
  type PlanId,
} from "@/lib/api/subscription";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

import {
  Check,
  CheckCircle2,
  CreditCard,
  AlertCircle,
  Clock,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DemoGate } from "@/components/demo/DemoGate";

const PLAN_FEATURES = [
  "Unlimited lessons",
  "Audio narration",
  "All 3 languages",
  "Offline access",
  "Experiment guides",
  "Progress tracking",
];

type BillingToggle = "monthly" | "annual";

export default function SubscriptionPage() {
  return (
    <DemoGate
      heading="Subscription not available in demo"
      description="Demo accounts access Grade 8 content for 24 hours. Sign up for full, ongoing access."
    >
      <SubscriptionPageInner />
    </DemoGate>
  );
}

function SubscriptionPageInner() {
  const t = useTranslations("subscription_screen");
  const { data: sub, isLoading } = useSubscription();
  const qc = useQueryClient();
  const [billing, setBilling] = useState<BillingToggle>("monthly");
  const [submitting, setSubmitting] = useState(false);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [cancelDone, setCancelDone] = useState(false);

  async function handleSubscribe() {
    setSubmitting(true);
    try {
      const planId: PlanId = billing === "annual" ? "student_annual" : "student_monthly";
      const url = await createCheckout(planId, billing);
      window.location.href = url;
    } catch {
      setSubmitting(false);
    }
  }

  async function handleManage() {
    setSubmitting(true);
    try {
      const url = await getBillingPortalUrl();
      window.location.href = url;
    } catch {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    setSubmitting(true);
    try {
      await cancelSubscription();
      await qc.invalidateQueries({ queryKey: ["subscription"] });
      setCancelDone(true);
      setCancelConfirm(false);
    } catch {
      setSubmitting(false);
    }
  }

  const trialDays = trialDaysRemaining(sub?.trial_ends_at ?? null);
  const isActive = sub?.status === "active";
  const isTrial = sub?.status === "trial";
  const isCancelled = sub?.status === "cancelled" || sub?.cancel_at_period_end;

  return (
    <div className="max-w-3xl space-y-8 p-6">
      <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>

      {isLoading && <Skeleton className="h-40 rounded-lg" />}

      {/* Current plan status card */}
      {!isLoading && sub && (
        <Card className="border shadow-sm">
          <CardContent className="flex items-center justify-between gap-4 p-5">
            <div className="space-y-1">
              <p className="text-sm text-gray-500">Current plan</p>
              <div className="flex items-center gap-2">
                <p className="font-semibold text-gray-900">
                  {isActive || isCancelled
                    ? sub.plan === "student_annual"
                      ? "Student — Annual"
                      : "Student — Monthly"
                    : isTrial
                      ? "Free Trial"
                      : t("current_plan_free")}
                </p>
                <Badge
                  className={cn(
                    "inline-flex items-center gap-1 text-xs",
                    isActive &&
                      !isCancelled &&
                      "border-green-200 bg-green-100 text-green-700",
                    isTrial && "border-blue-200 bg-blue-100 text-blue-700",
                    (sub.status === "free" || isCancelled) && "bg-gray-100 text-gray-600",
                    sub.status === "past_due" && "bg-red-100 text-red-700",
                  )}
                >
                  {isActive && !isCancelled && (
                    <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />
                  )}
                  {isTrial && <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />}
                  {isCancelled && (
                    <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
                  )}
                  {sub.status === "past_due" && (
                    <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />
                  )}
                  {sub.status === "free" && !isCancelled && (
                    <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />
                  )}
                  {isCancelled
                    ? "Cancels at period end"
                    : sub.status === "past_due"
                      ? "Payment overdue"
                      : sub.status}
                </Badge>
              </div>
              {isTrial && trialDays !== null && (
                <p className="flex items-center gap-1 text-xs text-blue-600">
                  <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />
                  {trialDays} day{trialDays !== 1 ? "s" : ""} remaining in trial
                </p>
              )}
              {(isActive || isCancelled) && sub.current_period_end && (
                <p className="text-xs text-gray-400">
                  {isCancelled ? "Access until" : "Renews"}{" "}
                  {new Date(sub.current_period_end).toLocaleDateString()}
                </p>
              )}
            </div>
            {(isActive || isCancelled) && (
              <Button variant="outline" onClick={handleManage} disabled={submitting}>
                <CreditCard className="mr-1.5 h-4 w-4" />
                Manage billing
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Cancel confirmation */}
      {cancelConfirm && (
        <div className="space-y-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Cancel your subscription?</p>
              <p className="mt-0.5 text-sm text-red-600">
                You&apos;ll keep access until the end of your current billing period.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              disabled={submitting}
            >
              {submitting ? "Cancelling…" : "Yes, cancel"}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setCancelConfirm(false)}>
              Keep subscription
            </Button>
          </div>
        </div>
      )}

      {cancelDone && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          Subscription cancelled. You&apos;ll keep full access until your billing period
          ends.
        </div>
      )}

      {/* Plan selector — shown for free/trial/cancelled */}
      {!isLoading &&
        sub &&
        (sub.status === "free" || sub.status === "trial" || isCancelled) && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">Choose a plan</h2>
              {/* Billing toggle */}
              <div className="ml-auto flex gap-1 rounded-lg border bg-white p-1">
                {(["monthly", "annual"] as BillingToggle[]).map((b) => (
                  <button
                    key={b}
                    onClick={() => setBilling(b)}
                    className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                      billing === b
                        ? "bg-blue-600 text-white"
                        : "text-gray-500 hover:text-gray-900"
                    }`}
                  >
                    {b === "monthly" ? "Monthly" : "Annual"}
                    {b === "annual" && <span className="ml-1 text-green-400">−17%</span>}
                  </button>
                ))}
              </div>
            </div>

            <Card className="border-2 border-blue-600 shadow-md">
              <CardHeader className="pb-2">
                <CardTitle>Student Plan</CardTitle>
                <div className="mt-1">
                  {billing === "monthly" ? (
                    <span className="text-3xl font-bold">
                      $9.99
                      <span className="text-base font-normal text-gray-500">/month</span>
                    </span>
                  ) : (
                    <span className="text-3xl font-bold">
                      $99.99
                      <span className="text-base font-normal text-gray-500">/year</span>
                    </span>
                  )}
                </div>
                {billing === "annual" && (
                  <p className="text-xs text-green-600">Save $19.89 vs monthly</p>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-2">
                  {PLAN_FEATURES.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                      <Check className="h-4 w-4 shrink-0 text-green-500" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className="w-full"
                  onClick={handleSubscribe}
                  disabled={submitting}
                >
                  {submitting ? "Redirecting to checkout…" : t("subscribe_btn")}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

      {/* Cancel link — shown for active non-cancelling subscriptions */}
      {isActive && !isCancelled && !cancelConfirm && !cancelDone && (
        <p className="text-center text-sm text-gray-400">
          Want to cancel?{" "}
          <button
            className="text-red-500 hover:underline"
            onClick={() => setCancelConfirm(true)}
          >
            Cancel subscription
          </button>
        </p>
      )}
    </div>
  );
}
