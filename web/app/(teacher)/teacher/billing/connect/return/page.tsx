"use client";

/**
 * Stripe Connect return page — Stripe redirects here after onboarding.
 *
 * The page refetches the Connect status and shows either a success or
 * "still pending" message, then redirects back to the billing page.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";
import { getConnectStatus } from "@/lib/api/teacher";
import { useTeacherIdFromToken } from "@/lib/hooks/useIndependentTeacher";

export default function ConnectReturnPage() {
  const router = useRouter();
  const teacherId = useTeacherIdFromToken();
  const [checking, setChecking] = useState(true);
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    if (!teacherId) return;
    let cancelled = false;

    getConnectStatus(teacherId)
      .then((status) => {
        if (cancelled) return;
        setComplete(status.onboarding_complete);
        setChecking(false);
        // Redirect to billing page after short delay
        setTimeout(
          () => router.replace("/teacher/billing/connect"),
          complete ? 1500 : 2500,
        );
      })
      .catch(() => {
        if (!cancelled) {
          setChecking(false);
          setTimeout(() => router.replace("/teacher/billing/connect"), 2000);
        }
      });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teacherId]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        {checking ? (
          <>
            <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-indigo-500" />
            <p className="text-sm text-gray-600">Checking your Connect account…</p>
          </>
        ) : complete ? (
          <>
            <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-500" />
            <p className="text-base font-semibold text-gray-900">
              Connect account active!
            </p>
            <p className="mt-1 text-sm text-gray-500">Redirecting to your billing page…</p>
          </>
        ) : (
          <>
            <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-amber-500" />
            <p className="text-sm text-gray-600">
              Onboarding isn&apos;t fully complete yet — redirecting back…
            </p>
          </>
        )}
      </div>
    </div>
  );
}
