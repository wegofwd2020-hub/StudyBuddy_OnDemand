"use client";

import { useDemoStudent } from "@/lib/hooks/useDemoStudent";
import { demoLogout } from "@/lib/api/demo";
import { LinkButton } from "@/components/ui/link-button";
import { AlertTriangle, Clock, FlaskConical, LogOut } from "lucide-react";

function demoTimeRemaining(expiresAt: string): {
  label: string;
  urgent: boolean;
} {
  const diffMs = new Date(expiresAt).getTime() - Date.now();
  if (diffMs <= 0) return { label: "Demo expired", urgent: true };

  const totalMinutes = Math.floor(diffMs / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const urgent = diffMs < 2 * 60 * 60 * 1_000; // < 2 hours

  const label =
    hours > 0
      ? `${hours}h ${minutes}m left in your demo`
      : `${minutes} minute${minutes === 1 ? "" : "s"} left in your demo`;

  return { label, urgent };
}

async function handleDemoSignOut(demoAccountId: string): Promise<void> {
  const token = localStorage.getItem("sb_token");
  if (token) {
    try {
      await demoLogout(token);
    } catch {
      // best-effort — proceed with local cleanup regardless
    }
  }
  localStorage.removeItem("sb_token");
  // Clear the dev session cookie used by the server layout
  document.cookie = "sb_dev_session=; path=/; max-age=0; SameSite=Lax";
  // Suppress unused-variable lint — demoAccountId used as param for future analytics
  void demoAccountId;
  window.location.href = "/";
}

export function DemoBanner() {
  const demo = useDemoStudent();
  if (!demo) return null;

  const { label, urgent } = demoTimeRemaining(demo.demo_expires_at);

  return (
    <div
      role="status"
      aria-label="Demo account status"
      className={`flex items-center justify-between gap-3 px-4 py-2 text-sm ${
        urgent
          ? "border-b border-red-200 bg-red-50 text-red-800"
          : "border-b border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <span className="flex items-center gap-2">
        {urgent ? (
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <FlaskConical className="h-4 w-4 shrink-0" aria-hidden="true" />
        )}
        <span>
          {urgent && (
            <span className="mr-1 font-bold uppercase tracking-wide text-xs">Urgent:</span>
          )}
          <span className="font-medium">Demo account</span>
          {" — "}
          <Clock className="inline h-3 w-3 align-middle mr-0.5" aria-hidden="true" />
          {label}
        </span>
      </span>

      <div className="flex shrink-0 items-center gap-2">
        <LinkButton href="/signup" size="sm" className="h-7 text-xs">
          Get full access
        </LinkButton>
        <button
          onClick={() => handleDemoSignOut(demo.demo_account_id)}
          aria-label="Sign out of demo"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium opacity-70 transition-opacity hover:opacity-100"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </div>
  );
}
