"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getSchoolSubscription,
  createSchoolCheckout,
  cancelSchoolSubscription,
  createExtraBuildCheckout,
  createCreditsBundleCheckout,
} from "@/lib/api/school-admin";
import { SCHOOL_PLANS_LIST, formatPlanPrice } from "@/lib/pricing";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle, XCircle, CreditCard, Users, GraduationCap, AlertTriangle, Hammer, PackagePlus } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Seat usage bar ────────────────────────────────────────────────────────────

function SeatBar({
  label,
  used,
  max,
  icon,
}: {
  label: string;
  used: number;
  max: number;
  icon: React.ReactNode;
}) {
  const pct = max > 0 ? Math.min((used / max) * 100, 100) : 0;
  const isWarning = pct >= 80;
  const isFull = used >= max;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-gray-600">
          {icon}
          {label}
        </span>
        <span
          className={cn(
            "font-medium",
            isFull ? "text-red-600" : isWarning ? "text-amber-600" : "text-gray-700",
          )}
        >
          {used} / {max}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isFull ? "bg-red-500" : isWarning ? "bg-amber-400" : "bg-blue-500",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const styles: Record<string, string> = {
    active: "bg-green-100 text-green-700",
    trialing: "bg-blue-100 text-blue-700",
    past_due: "bg-amber-100 text-amber-700",
    cancelled_at_period_end: "bg-gray-100 text-gray-600",
    cancelled: "bg-gray-100 text-gray-500",
  };
  const labels: Record<string, string> = {
    active: "Active",
    trialing: "Trial",
    past_due: "Past due",
    cancelled_at_period_end: "Cancels at period end",
    cancelled: "Cancelled",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[status] ?? "bg-gray-100 text-gray-500",
      )}
    >
      {labels[status] ?? status}
    </span>
  );
}

// ── Cancel confirm dialog ─────────────────────────────────────────────────────

function CancelDialog({
  periodEnd,
  onConfirm,
  onDismiss,
  isPending,
}: {
  periodEnd: string | null;
  onConfirm: () => void;
  onDismiss: () => void;
  isPending: boolean;
}) {
  const endDate = periodEnd
    ? new Date(periodEnd).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
          <h2 className="text-base font-semibold text-gray-900">Cancel subscription?</h2>
        </div>
        <p className="mb-1 text-sm text-gray-600">
          Your school will retain access until{" "}
          <strong>{endDate ?? "the end of the billing period"}</strong>. After that, limits
          revert to the Starter plan.
        </p>
        <p className="mb-5 text-sm text-gray-500">
          You can resubscribe at any time before the period ends.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onDismiss} disabled={isPending}>
            Keep subscription
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isPending}
            className="gap-2 bg-red-600 text-white hover:bg-red-700"
          >
            {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Yes, cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SubscriptionPage() {
  const teacher = useTeacher();
  const queryClient = useQueryClient();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  // origin is only available in the browser
  const [origin, setOrigin] = useState("");
  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const [checkingOut, setCheckingOut] = useState<string | null>(null); // plan id being checked out
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelSuccess, setCancelSuccess] = useState(false);
  const [buyingExtraBuild, setBuyingExtraBuild] = useState(false);
  const [buyingBundle, setBuyingBundle] = useState<number | null>(null); // bundle size

  const { data: sub, isLoading } = useQuery({
    queryKey: ["school-subscription", schoolId],
    queryFn: () => getSchoolSubscription(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelSchoolSubscription(schoolId),
    onSuccess: () => {
      setShowCancelDialog(false);
      setCancelSuccess(true);
      void queryClient.invalidateQueries({ queryKey: ["school-subscription", schoolId] });
    },
  });

  async function handleCheckout(planId: string) {
    if (!origin) return;
    setCheckingOut(planId);
    setCheckoutError(null);
    try {
      const { checkout_url } = await createSchoolCheckout(
        schoolId,
        planId,
        `${origin}/school/subscription?success=1`,
        `${origin}/school/subscription?cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch (err: unknown) {
      const msg =
        err != null &&
        typeof err === "object" &&
        "response" in err &&
        err.response != null &&
        typeof err.response === "object" &&
        "data" in err.response &&
        err.response.data != null &&
        typeof err.response.data === "object" &&
        "detail" in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : "Could not start checkout. Please try again.";
      setCheckoutError(msg);
      setCheckingOut(null);
    }
  }

  async function handleExtraBuild() {
    if (!origin) return;
    setBuyingExtraBuild(true);
    setCheckoutError(null);
    try {
      const { checkout_url } = await createExtraBuildCheckout(
        schoolId,
        `${origin}/school/subscription?success=1`,
        `${origin}/school/subscription?cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch {
      setCheckoutError("Could not start checkout. Please try again.");
      setBuyingExtraBuild(false);
    }
  }

  async function handleCreditBundle(bundleSize: 3 | 10 | 25) {
    if (!origin) return;
    setBuyingBundle(bundleSize);
    setCheckoutError(null);
    try {
      const { checkout_url } = await createCreditsBundleCheckout(
        schoolId,
        bundleSize,
        `${origin}/school/subscription?success=1`,
        `${origin}/school/subscription?cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch {
      setCheckoutError("Could not start checkout. Please try again.");
      setBuyingBundle(null);
    }
  }

  const activePlan = sub?.plan ?? "none";
  const isActive = sub?.status === "active" || sub?.status === "trialing";
  const isCancelledAtEnd = sub?.status === "cancelled_at_period_end";
  const hasSub = isActive || isCancelledAtEnd;

  const periodEndDate = sub?.current_period_end
    ? new Date(sub.current_period_end).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Subscription</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your school plan and seat limits.
        </p>
      </div>

      {/* Current plan card */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Current plan</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading…
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-xl font-bold capitalize text-gray-900">
                  {activePlan === "none" ? "No subscription" : activePlan}
                </span>
                {sub?.status && <StatusBadge status={sub.status} />}
              </div>

              {hasSub && sub && (
                <>
                  <div className="space-y-3">
                    <SeatBar
                      label="Students"
                      used={sub.seats_used_students}
                      max={sub.max_students}
                      icon={<Users className="h-3.5 w-3.5 text-gray-400" />}
                    />
                    <SeatBar
                      label="Teachers"
                      used={sub.seats_used_teachers}
                      max={sub.max_teachers}
                      icon={<GraduationCap className="h-3.5 w-3.5 text-gray-400" />}
                    />
                    {sub.builds_included === -1 ? (
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <Hammer className="h-3.5 w-3.5 text-gray-400" />
                        Unlimited curriculum builds (Enterprise)
                      </div>
                    ) : (
                      <SeatBar
                        label="Curriculum builds / year"
                        used={sub.builds_used}
                        max={sub.builds_included}
                        icon={<Hammer className="h-3.5 w-3.5 text-gray-400" />}
                      />
                    )}
                  </div>

                  {periodEndDate && (
                    <p className="text-xs text-gray-500">
                      {isCancelledAtEnd ? (
                        <>
                          <span className="font-medium text-amber-600">Cancels</span> —
                          access continues until{" "}
                          <span className="font-medium text-gray-700">{periodEndDate}</span>
                        </>
                      ) : (
                        <>
                          Renews on{" "}
                          <span className="font-medium text-gray-700">{periodEndDate}</span>
                        </>
                      )}
                    </p>
                  )}

                  {isAdmin && isActive && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowCancelDialog(true)}
                      className="gap-2 border-red-200 text-red-600 hover:bg-red-50"
                    >
                      <XCircle className="h-4 w-4" />
                      Cancel subscription
                    </Button>
                  )}

                  {cancelSuccess && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="h-4 w-4 shrink-0" />
                      Cancellation confirmed. Access continues until {periodEndDate}.
                    </div>
                  )}
                </>
              )}

              {!hasSub && (
                <p className="text-sm text-gray-500">
                  Your school is on the free Starter plan. Upgrade to unlock more students,
                  teachers, and pipeline runs.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Extra builds / credit bundles — shown when admin has an active subscription */}
      {isAdmin && hasSub && sub && sub.builds_included !== -1 && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Curriculum builds</h2>
          <p className="text-sm text-gray-500">
            Your plan includes{" "}
            <span className="font-medium text-gray-700">
              {sub.builds_included} build{sub.builds_included !== 1 ? "s" : ""} / year
            </span>
            . You have used{" "}
            <span className="font-medium text-gray-700">{sub.builds_used}</span>.
            {sub.builds_credits_balance > 0 && (
              <>
                {" "}Rollover credit balance:{" "}
                <span className="font-medium text-blue-700">
                  {sub.builds_credits_balance} credit{sub.builds_credits_balance !== 1 ? "s" : ""}
                </span>.
              </>
            )}
          </p>

          {/* Single extra build CTA — shown when allowance is exhausted */}
          {sub.builds_remaining === 0 && (
            <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
              <p className="flex-1 text-sm text-amber-800">
                Plan allowance exhausted.
                {sub.builds_credits_balance > 0
                  ? ` You have ${sub.builds_credits_balance} rollover credit${sub.builds_credits_balance !== 1 ? "s" : ""} remaining.`
                  : " Purchase an extra build or a credit bundle below."}
              </p>
              {sub.builds_credits_balance === 0 && (
                <Button
                  size="sm"
                  className="gap-2 shrink-0"
                  disabled={buyingExtraBuild}
                  onClick={handleExtraBuild}
                >
                  {buyingExtraBuild ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CreditCard className="h-3.5 w-3.5" />
                  )}
                  Buy 1 build — $15
                </Button>
              )}
            </div>
          )}

          {/* Credit bundle cards */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {(
              [
                { size: 3,  price: "$39",  saving: null },
                { size: 10, price: "$119", saving: "Save 21%" },
                { size: 25, price: "$269", saving: "Save 28%" },
              ] as { size: 3 | 10 | 25; price: string; saving: string | null }[]
            ).map(({ size, price, saving }) => (
              <div
                key={size}
                className="flex flex-col gap-2 rounded-xl border border-gray-200 p-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">
                      {size} build credit{size !== 1 ? "s" : ""}
                    </p>
                    <p className="text-xs text-gray-500">Roll over — never expire</p>
                  </div>
                  {saving && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                      {saving}
                    </span>
                  )}
                </div>
                <p className="text-lg font-bold text-gray-900">{price}</p>
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-auto gap-2"
                  disabled={buyingBundle !== null || buyingExtraBuild}
                  onClick={() => handleCreditBundle(size)}
                >
                  {buyingBundle === size ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <PackagePlus className="h-3.5 w-3.5" />
                  )}
                  Buy bundle
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plan comparison */}
      {isAdmin && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Available plans</h2>

          {checkoutError && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {checkoutError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {SCHOOL_PLANS_LIST.map((plan) => {
              const isCurrent = activePlan === plan.id && hasSub;
              const isEnterprise = plan.id === "enterprise";

              return (
                <div
                  key={plan.id}
                  className={cn(
                    "relative flex flex-col rounded-xl border p-5 transition-shadow",
                    plan.highlight
                      ? "border-blue-400 shadow-md ring-1 ring-blue-400"
                      : "border-gray-200",
                    isCurrent && "border-green-400 ring-1 ring-green-400",
                  )}
                >
                  {plan.highlight && !isCurrent && (
                    <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-blue-500 px-3 py-0.5 text-xs font-semibold text-white">
                      Popular
                    </div>
                  )}
                  {isCurrent && (
                    <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-green-500 px-3 py-0.5 text-xs font-semibold text-white">
                      Current plan
                    </div>
                  )}

                  <div className="mb-1">
                    <h3 className="text-base font-semibold text-gray-900">{plan.name}</h3>
                    <p className="mt-0.5 text-sm text-gray-500">{formatPlanPrice(plan)}</p>
                  </div>

                  <ul className="mt-3 flex-1 space-y-1.5">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-1.5 text-xs text-gray-600">
                        <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <div className="mt-4">
                    {isCurrent ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        disabled
                      >
                        Current plan
                      </Button>
                    ) : isEnterprise ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full gap-2"
                        onClick={() =>
                          window.open("mailto:sales@studybuddy.example.com?subject=Enterprise%20Plan", "_blank")
                        }
                      >
                        Contact sales
                      </Button>
                    ) : plan.id === "starter" && !hasSub ? (
                      <Button variant="outline" size="sm" className="w-full" disabled>
                        Free plan
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        className={cn(
                          "w-full gap-2",
                          plan.highlight && "bg-blue-600 hover:bg-blue-700",
                        )}
                        disabled={!!checkingOut || isCurrent}
                        onClick={() => handleCheckout(plan.id)}
                      >
                        {checkingOut === plan.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <CreditCard className="h-3.5 w-3.5" />
                        )}
                        {isCancelledAtEnd ? "Resubscribe" : "Upgrade"}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Read-only notice for non-admins */}
      {!isAdmin && (
        <p className="text-center text-xs text-gray-400">
          Only school administrators can manage the subscription.
        </p>
      )}

      {/* Cancel dialog */}
      {showCancelDialog && (
        <CancelDialog
          periodEnd={sub?.current_period_end ?? null}
          onConfirm={() => cancelMutation.mutate()}
          onDismiss={() => setShowCancelDialog(false)}
          isPending={cancelMutation.isPending}
        />
      )}
    </div>
  );
}
