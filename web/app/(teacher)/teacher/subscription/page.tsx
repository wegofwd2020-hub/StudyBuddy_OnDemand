"use client";

/**
 * Independent teacher subscription page — seat-tiered flat-fee plans (#105).
 *
 * Shows:
 * - Current plan + seat usage bar
 * - Over-quota warning if seats_used > max_students
 * - Plan comparison cards (Solo / Growth / Pro) with upgrade / downgrade CTA
 * - Cancel subscription link
 */

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelTeacherSubscription,
  getTeacherSubscription,
  startTeacherCheckout,
  upgradeTeacherPlan,
  type TeacherSubscriptionStatus,
} from "@/lib/api/teacher-subscription";
import { useTeacherIdFromToken } from "@/lib/hooks/useIndependentTeacher";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Users,
} from "lucide-react";

// ── Plan definitions (mirrors pricing.py TEACHER_PLANS) ──────────────────────

const PLANS = [
  {
    id: "solo",
    name: "Solo",
    price: "29",
    max_students: 25,
    highlight: false,
    features: [
      "Up to 25 students",
      "Default curriculum (Grades 5–12)",
      "English content",
      "Progress dashboard",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    price: "59",
    max_students: 75,
    highlight: true,
    features: [
      "Up to 75 students",
      "EN + FR + ES content",
      "Teacher reporting dashboard",
      "Weekly digest emails",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "99",
    max_students: 200,
    highlight: false,
    features: [
      "Up to 200 students",
      "All languages",
      "Full reporting suite",
      "Priority support",
    ],
  },
] as const;

type PlanId = "solo" | "growth" | "pro";

// ── Sub-components ────────────────────────────────────────────────────────────

function SeatUsageBar({
  used,
  max,
  overQuota,
}: {
  used: number;
  max: number;
  overQuota: boolean;
}) {
  const pct = max > 0 ? Math.min((used / max) * 100, 100) : 0;
  const barColor = overQuota
    ? "bg-red-500"
    : pct >= 90
      ? "bg-amber-400"
      : "bg-indigo-500";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className={cn("font-medium", overQuota ? "text-red-700" : "text-gray-700")}>
          {used} / {max} students enrolled
        </span>
        {overQuota && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
            Over limit
          </span>
        )}
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function OverQuotaBanner({ since }: { since: string | null }) {
  const sinceStr = since
    ? new Date(since).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
      <div>
        <p className="text-sm font-semibold text-red-900">Student limit exceeded</p>
        <p className="mt-0.5 text-xs text-red-700">
          You have more enrolled students than your plan allows.
          {sinceStr && ` This has been the case since ${sinceStr}.`}
          {" "}Upgrade your plan to restore full access, or remove students to get back within your limit.
          After 7 days over-limit, new content access may be restricted.
        </p>
      </div>
    </div>
  );
}

function PlanCard({
  plan,
  currentPlanId,
  seatsUsed,
  onUpgrade,
  onCheckout,
  isPending,
  pendingPlanId,
  hasSubscription,
}: {
  plan: (typeof PLANS)[number];
  currentPlanId: string | null;
  seatsUsed: number;
  onUpgrade: (planId: PlanId) => void;
  onCheckout: (planId: PlanId) => void;
  isPending: boolean;
  pendingPlanId: string | null;
  hasSubscription: boolean;
}) {
  const isCurrent = plan.id === currentPlanId;
  const isLoading = isPending && pendingPlanId === plan.id;
  const tooSmall = seatsUsed > plan.max_students;

  return (
    <div
      className={cn(
        "relative rounded-xl border p-6 transition-shadow",
        isCurrent
          ? "border-indigo-500 bg-indigo-50 shadow-md"
          : "border-gray-200 bg-white hover:shadow-sm",
      )}
    >
      {plan.highlight && !isCurrent && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-indigo-600 px-3 py-0.5 text-xs font-semibold text-white">
          Popular
        </span>
      )}
      {isCurrent && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-green-600 px-3 py-0.5 text-xs font-semibold text-white">
          Current plan
        </span>
      )}

      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
        <p className="mt-1 text-3xl font-bold text-gray-900">
          ${plan.price}
          <span className="text-sm font-normal text-gray-500">/month</span>
        </p>
        <p className="mt-0.5 text-xs text-gray-500">Up to {plan.max_students} students</p>
      </div>

      <ul className="mb-5 space-y-2">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
            <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-indigo-500" />
            {f}
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="flex items-center gap-1.5 text-xs font-medium text-green-700">
          <CheckCircle2 className="h-4 w-4" />
          Active
        </div>
      ) : (
        <button
          onClick={() =>
            hasSubscription ? onUpgrade(plan.id) : onCheckout(plan.id)
          }
          disabled={isPending || (tooSmall && hasSubscription)}
          title={tooSmall && hasSubscription ? `You already have ${seatsUsed} students — this plan only allows ${plan.max_students}` : undefined}
          className={cn(
            "inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            tooSmall && hasSubscription
              ? "cursor-not-allowed bg-gray-100 text-gray-400"
              : "bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50",
          )}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          {hasSubscription ? "Switch to this plan" : "Get started"}
        </button>
      )}

      {tooSmall && hasSubscription && !isCurrent && (
        <p className="mt-1.5 text-center text-xs text-gray-400">
          Remove students to downgrade
        </p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TeacherSubscriptionPage() {
  const teacherId = useTeacherIdFromToken();
  const queryClient = useQueryClient();
  const [pendingPlanId, setPendingPlanId] = useState<string | null>(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);

  const { data: sub, isLoading } = useQuery({
    queryKey: ["teacher-subscription", teacherId],
    queryFn: () => getTeacherSubscription(teacherId!),
    enabled: !!teacherId,
    staleTime: 30_000,
  });

  const upgradeMutation = useMutation({
    mutationFn: ({ planId }: { planId: string }) =>
      upgradeTeacherPlan(teacherId!, planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher-subscription", teacherId] });
      setPendingPlanId(null);
    },
    onError: () => setPendingPlanId(null),
  });

  const checkoutMutation = useMutation({
    mutationFn: ({ planId }: { planId: string }) =>
      startTeacherCheckout(
        teacherId!,
        planId,
        `${window.location.origin}/teacher/subscription?success=1`,
        `${window.location.origin}/teacher/subscription`,
      ),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
    onError: () => setPendingPlanId(null),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelTeacherSubscription(teacherId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher-subscription", teacherId] });
      setCancelConfirm(false);
    },
  });

  const isPending =
    upgradeMutation.isPending ||
    checkoutMutation.isPending ||
    cancelMutation.isPending;
  const mutationError =
    upgradeMutation.error ?? checkoutMutation.error ?? cancelMutation.error;

  const hasSubscription =
    !!sub && sub.plan !== "none" && sub.status !== "cancelled";

  const handleUpgrade = (planId: PlanId) => {
    setPendingPlanId(planId);
    upgradeMutation.mutate({ planId });
  };

  const handleCheckout = (planId: PlanId) => {
    setPendingPlanId(planId);
    checkoutMutation.mutate({ planId });
  };

  if (!teacherId || isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <div className="space-y-4">
          <div className="h-8 w-64 animate-pulse rounded-lg bg-gray-100" />
          <div className="grid grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-64 animate-pulse rounded-xl bg-gray-100" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Subscription plan</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your independent teacher plan and enrolled student seats.
        </p>
      </div>

      {/* Over-quota warning */}
      {sub?.over_quota && <OverQuotaBanner since={sub.over_quota_since} />}

      {/* Seat usage */}
      {hasSubscription && sub && (
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <Users className="h-5 w-5 text-gray-400" />
            <h2 className="text-base font-semibold text-gray-900">
              Student seats —{" "}
              <span className="capitalize">{sub.plan}</span> plan
            </h2>
          </div>
          <SeatUsageBar
            used={sub.seats_used_students}
            max={sub.max_students}
            overQuota={sub.over_quota}
          />
          {sub.current_period_end && (
            <p className="mt-3 text-xs text-gray-400">
              {sub.status === "past_due" ? "Grace period ends" : "Renews"}{" "}
              {new Date(sub.current_period_end).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          )}
        </div>
      )}

      {/* Plan comparison */}
      {mutationError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          Something went wrong. Please try again.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {PLANS.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            currentPlanId={hasSubscription ? sub!.plan : null}
            seatsUsed={sub?.seats_used_students ?? 0}
            onUpgrade={handleUpgrade}
            onCheckout={handleCheckout}
            isPending={isPending}
            pendingPlanId={pendingPlanId}
            hasSubscription={hasSubscription}
          />
        ))}
      </div>

      {/* Cancel */}
      {hasSubscription && (
        <div className="mt-8 border-t border-gray-100 pt-6">
          {!cancelConfirm ? (
            <button
              onClick={() => setCancelConfirm(true)}
              className="text-sm text-gray-400 hover:text-red-600 hover:underline"
            >
              Cancel subscription
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <p className="text-sm text-gray-600">
                Cancel at end of billing period?
              </p>
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {cancelMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
                Yes, cancel
              </button>
              <button
                onClick={() => setCancelConfirm(false)}
                className="text-xs text-gray-500 hover:underline"
              >
                Never mind
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
