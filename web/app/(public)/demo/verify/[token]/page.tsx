"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CheckCircle, XCircle, Clock, Users, Loader2, AlertCircle } from "lucide-react";
import { LinkButton } from "@/components/ui/link-button";
import { verifyDemoEmail } from "@/lib/api/demo";

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
  titleKey: string;
  bodyKey: string;
  ctaKey: string;
  ctaHref: string;
  iconBg: string;
}

const STATE_CONFIG: Record<Exclude<VerifyState, "loading">, StateConfig> = {
  success: {
    icon: <CheckCircle className="h-7 w-7 text-green-600" />,
    titleKey: "verify_success_title",
    bodyKey: "verify_success_body",
    ctaKey: "verify_success_cta",
    ctaHref: "/demo/login",
    iconBg: "bg-green-50",
  },
  used: {
    icon: <AlertCircle className="h-7 w-7 text-amber-600" />,
    titleKey: "verify_used_title",
    bodyKey: "verify_used_body",
    ctaKey: "verify_used_cta",
    ctaHref: "/demo/login",
    iconBg: "bg-amber-50",
  },
  expired: {
    icon: <Clock className="h-7 w-7 text-red-500" />,
    titleKey: "verify_expired_title",
    bodyKey: "verify_expired_body",
    ctaKey: "verify_expired_cta",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
  invalid: {
    icon: <XCircle className="h-7 w-7 text-red-500" />,
    titleKey: "verify_invalid_title",
    bodyKey: "verify_invalid_body",
    ctaKey: "verify_error_cta",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
  capacity: {
    icon: <Users className="h-7 w-7 text-orange-500" />,
    titleKey: "verify_capacity_title",
    bodyKey: "verify_capacity_body",
    ctaKey: "verify_error_cta",
    ctaHref: "/",
    iconBg: "bg-orange-50",
  },
  error: {
    icon: <XCircle className="h-7 w-7 text-red-500" />,
    titleKey: "verify_error_title",
    bodyKey: "verify_error_body",
    ctaKey: "verify_error_cta",
    ctaHref: "/",
    iconBg: "bg-red-50",
  },
};

function resolveState(err: unknown): Exclude<VerifyState, "loading" | "success"> {
  const code = (err as { response?: { data?: { error?: string } } })?.response?.data
    ?.error;
  if (code === "token_not_found") return "invalid";
  if (code === "token_already_used") return "used";
  if (code === "token_expired") return "expired";
  if (code === "demo_capacity_reached") return "capacity";
  return "error";
}

export default function DemoVerifyPage() {
  const { token } = useParams<{ token: string }>();
  const t = useTranslations("demo");
  // Derive initial state: missing token → invalid immediately (avoids setState-in-effect lint error)
  const [state, setState] = useState<VerifyState>(() => (token ? "loading" : "invalid"));

  useEffect(() => {
    if (!token) return;
    verifyDemoEmail(token)
      .then(() => setState("success"))
      .catch((err) => setState(resolveState(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state === "loading") {
    return (
      <div className="flex min-h-[70vh] items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">{t("verify_loading")}</p>
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

        <h1 className="text-xl font-bold text-gray-900">
          {t(cfg.titleKey as Parameters<typeof t>[0])}
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          {t(cfg.bodyKey as Parameters<typeof t>[0])}
        </p>

        <LinkButton href={cfg.ctaHref} className="mt-6 w-full justify-center">
          {t(cfg.ctaKey as Parameters<typeof t>[0])}
        </LinkButton>
      </div>
    </div>
  );
}
