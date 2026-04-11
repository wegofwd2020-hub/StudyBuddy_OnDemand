"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getConnectEarnings,
  getConnectStatus,
  refreshConnectLink,
  startConnectOnboarding,
  type ConnectStatus,
  type EarningsItem,
} from "@/lib/api/teacher";
import { useTeacherIdFromToken } from "@/lib/hooks/useIndependentTeacher";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  ArrowRight,
  BadgeDollarSign,
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

// ── Revenue share constants (mirrors backend REVENUE_SHARE) ──────────────────
const TEACHER_PCT = 70;
const PLATFORM_PCT = 30;
const STUDENT_PRICE_MONTHLY = "9.99";

// ── Onboarding status banner ──────────────────────────────────────────────────

function OnboardingBanner({
  status,
  onStart,
  onRefresh,
  isPending,
}: {
  status: ConnectStatus;
  onStart: () => void;
  onRefresh: () => void;
  isPending: boolean;
}) {
  if (status.onboarding_complete) {
    return (
      <div className="mb-6 flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4">
        <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
        <div>
          <p className="text-sm font-semibold text-green-900">Connect account active</p>
          <p className="mt-0.5 text-xs text-green-700">
            Stripe is sending {TEACHER_PCT}% of each student payment to your account.
          </p>
          {status.stripe_account_id && (
            <p className="mt-1 font-mono text-xs text-green-600">{status.stripe_account_id}</p>
          )}
        </div>
      </div>
    );
  }

  if (status.has_connect_account) {
    return (
      <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-amber-900">Onboarding incomplete</p>
          <p className="mt-0.5 text-xs text-amber-700">
            Your Stripe Connect account exists but payout capability is not yet
            enabled. Complete onboarding to start receiving student payments.
          </p>
          <button
            onClick={onRefresh}
            disabled={isPending}
            className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Continue onboarding
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-indigo-100 bg-indigo-50 p-6">
      <div className="flex items-start gap-4">
        <ShieldCheck className="mt-0.5 h-8 w-8 flex-shrink-0 text-indigo-500" />
        <div className="flex-1">
          <h2 className="text-base font-semibold text-indigo-900">
            Set up revenue-share billing
          </h2>
          <p className="mt-1 text-sm text-indigo-700">
            Connect your Stripe account to start receiving {TEACHER_PCT}% of each
            student&apos;s ${STUDENT_PRICE_MONTHLY}/month payment directly. No platform
            subscription fee — you earn as your students pay.
          </p>
          <ul className="mt-3 space-y-1.5 text-xs text-indigo-700">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-indigo-500" />
              {TEACHER_PCT}% of ${STUDENT_PRICE_MONTHLY}/mo per student paid to you
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-indigo-500" />
              {PLATFORM_PCT}% platform fee covers hosting, content generation &amp; support
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-indigo-500" />
              No monthly fee — lower barrier to entry
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-indigo-500" />
              Payouts directly to your bank via Stripe Express
            </li>
          </ul>
          <button
            onClick={onStart}
            disabled={isPending}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            Set up Stripe Connect
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Earnings table ────────────────────────────────────────────────────────────

function EarningsTable({ teacherId }: { teacherId: string }) {
  const { data: earnings, isLoading } = useQuery({
    queryKey: ["teacher-connect-earnings", teacherId],
    queryFn: () => getConnectEarnings(teacherId),
    staleTime: 60_000,
  });

  const fmt = (cents: number, currency: string) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(cents / 100);

  const fmtDate = (ts: number) =>
    new Date(ts * 1000).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  if (!earnings || earnings.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-400">
        No earnings yet. Student payments will appear here after they enrol.
      </p>
    );
  }

  const total = earnings.reduce((sum, t) => sum + t.amount_cents, 0);
  const currency = earnings[0].currency;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs text-gray-500">
          Last {earnings.length} transfer{earnings.length !== 1 ? "s" : ""}
        </p>
        <p className="font-mono text-sm font-semibold text-gray-900">
          Total: {fmt(total, currency)}
        </p>
      </div>
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                Date
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                Transfer ID
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">
                Amount
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {earnings.map((t) => (
              <tr key={t.transfer_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(t.created)}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{t.transfer_id}</td>
                <td className="px-4 py-3 text-right font-mono text-sm font-medium text-gray-900">
                  {fmt(t.amount_cents, t.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TeacherConnectBillingPage() {
  const teacherId = useTeacherIdFromToken();
  const queryClient = useQueryClient();

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["teacher-connect-status", teacherId],
    queryFn: () => getConnectStatus(teacherId!),
    enabled: !!teacherId,
    staleTime: 30_000,
  });

  const onboardMutation = useMutation({
    mutationFn: () => startConnectOnboarding(teacherId!),
    onSuccess: (data) => {
      window.location.href = data.onboarding_url;
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshConnectLink(teacherId!),
    onSuccess: (data) => {
      window.location.href = data.onboarding_url;
    },
  });

  const isPending = onboardMutation.isPending || refreshMutation.isPending;
  const mutationError = onboardMutation.error ?? refreshMutation.error;

  if (!teacherId || statusLoading) {
    return (
      <div className="mx-auto max-w-3xl p-8">
        <div className="space-y-4">
          <div className="h-8 w-64 animate-pulse rounded-lg bg-gray-100" />
          <div className="h-32 animate-pulse rounded-xl bg-gray-100" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Revenue-share billing</h1>
        <p className="mt-1 text-sm text-gray-500">
          Receive {TEACHER_PCT}% of each student&apos;s ${STUDENT_PRICE_MONTHLY}/month payment directly
          via Stripe Connect.
        </p>
      </div>

      {status && (
        <OnboardingBanner
          status={status}
          onStart={() => onboardMutation.mutate()}
          onRefresh={() => refreshMutation.mutate()}
          isPending={isPending}
        />
      )}

      {mutationError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          Something went wrong. Please try again.
        </div>
      )}

      {/* Earnings section — only shown once Connect account is active */}
      {status?.has_connect_account && (
        <section>
          <div className="mb-4 flex items-center gap-2">
            <BadgeDollarSign className="h-5 w-5 text-gray-400" />
            <h2 className="text-base font-semibold text-gray-900">Earnings history</h2>
          </div>
          <EarningsTable teacherId={teacherId} />
        </section>
      )}

      {/* Info block */}
      <div className="mt-8 rounded-xl border border-gray-100 bg-gray-50 p-5 text-xs text-gray-500">
        <p className="font-semibold text-gray-700">How it works</p>
        <ol className="mt-2 list-decimal space-y-1.5 pl-4">
          <li>Complete Stripe Express onboarding (takes ~5 minutes).</li>
          <li>
            Share your enrollment link with students — they pay ${STUDENT_PRICE_MONTHLY}/month.
          </li>
          <li>
            Stripe automatically sends {TEACHER_PCT}% (${(parseFloat(STUDENT_PRICE_MONTHLY) * TEACHER_PCT / 100).toFixed(2)}/student/month)
            to your bank. The platform keeps {PLATFORM_PCT}%.
          </li>
          <li>Payouts arrive on your normal Stripe payout schedule (usually 2 business days).</li>
        </ol>
        <p className="mt-3">
          Questions about Stripe Express?{" "}
          <a
            href="https://stripe.com/connect"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 text-indigo-600 hover:underline"
          >
            Learn more <ExternalLink className="h-3 w-3" />
          </a>
        </p>
      </div>
    </div>
  );
}
