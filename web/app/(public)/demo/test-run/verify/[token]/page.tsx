"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle, XCircle, Clock, Users, Loader2, AlertCircle } from "lucide-react";
import { LinkButton } from "@/components/ui/link-button";
import { verifyTestRunEmail } from "@/lib/api/demo";

type VerifyState =
  | "loading"
  | "success"
  | "used"
  | "expired"
  | "invalid"
  | "capacity"
  | "error";

interface StateConfig {
  icon: React.ReactNode;
  title: string;
  body: string;
  ctaLabel: string;
  ctaHref: string;
  iconBg: string;
}

const STATE_CONFIG: Record<Exclude<VerifyState, "loading">, StateConfig> = {
  success: {
    icon: <CheckCircle className="h-7 w-7 text-green-600" />,
    title: "You're all set",
    body: "We've emailed you two sets of login credentials — one for the teacher portal and one for the student portal. Check your inbox, then sign in using either set.",
    ctaLabel: "Go to sign in",
    ctaHref: "/signin",
    iconBg: "bg-green-50",
  },
  used: {
    icon: <AlertCircle className="h-7 w-7 text-amber-600" />,
    title: "This link was already used",
    body: "Your test-run credentials were already emailed to you. Check your inbox or sign in directly.",
    ctaLabel: "Go to sign in",
    ctaHref: "/signin",
    iconBg: "bg-amber-50",
  },
  expired: {
    icon: <Clock className="h-7 w-7 text-red-500" />,
    title: "This link has expired",
    body: "Verification links are valid for a limited time. Please request a new test run from the home page.",
    ctaLabel: "Back to home",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
  invalid: {
    icon: <XCircle className="h-7 w-7 text-red-500" />,
    title: "This link is not valid",
    body: "We couldn't find a test-run request for this link. Try requesting a new test run from the home page.",
    ctaLabel: "Back to home",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
  capacity: {
    icon: <Users className="h-7 w-7 text-orange-500" />,
    title: "All demo slots are full",
    body: "We're at capacity right now. Please try again in a little while — slots free up regularly.",
    ctaLabel: "Back to home",
    ctaHref: "/",
    iconBg: "bg-orange-50",
  },
  error: {
    icon: <XCircle className="h-7 w-7 text-red-500" />,
    title: "Something went wrong",
    body: "We couldn't complete your test-run setup. Please try requesting a new test run.",
    ctaLabel: "Back to home",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
};

function resolveState(err: unknown): Exclude<VerifyState, "loading" | "success"> {
  const code = (err as { response?: { data?: { error?: string } } })?.response?.data
    ?.error;
  if (code === "token_not_found") return "invalid";
  if (code === "token_already_used" || code === "already_verified") return "used";
  if (code === "token_expired") return "expired";
  if (code === "demo_capacity_reached") return "capacity";
  return "error";
}

export default function TestRunVerifyPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<VerifyState>(() =>
    token ? "loading" : "invalid",
  );

  useEffect(() => {
    if (!token) return;
    verifyTestRunEmail(token)
      .then(() => setState("success"))
      .catch((err) => setState(resolveState(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state === "loading") {
    return (
      <div className="flex min-h-[70vh] items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">Setting up your test run…</p>
        </div>
      </div>
    );
  }

  const cfg = STATE_CONFIG[state];

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border bg-white p-8 text-center shadow-sm">
        <div
          className={`mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full ${cfg.iconBg}`}
        >
          {cfg.icon}
        </div>

        <h1 className="text-xl font-bold text-gray-900">{cfg.title}</h1>
        <p className="mt-2 text-sm text-gray-500">{cfg.body}</p>

        <LinkButton href={cfg.ctaHref} className="mt-6 w-full justify-center">
          {cfg.ctaLabel}
        </LinkButton>
      </div>
    </div>
  );
}
