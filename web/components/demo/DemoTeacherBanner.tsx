"use client";

import { useDemoTeacher } from "@/lib/hooks/useDemoTeacher";
import { demoTeacherLogout } from "@/lib/api/demo";
import { LinkButton } from "@/components/ui/link-button";
import { AlertTriangle, Clock, GraduationCap, LogOut } from "lucide-react";

function demoTeacherTimeRemaining(expiresAt: string): {
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
      ? `${hours}h ${minutes}m left in your teacher demo`
      : `${minutes} minute${minutes === 1 ? "" : "s"} left in your teacher demo`;

  return { label, urgent };
}

async function handleTeacherDemoSignOut(demoAccountId: string): Promise<void> {
  const token = localStorage.getItem("sb_teacher_token");
  if (token) {
    try {
      await demoTeacherLogout(token);
    } catch {
      // best-effort — proceed with local cleanup regardless
    }
  }
  localStorage.removeItem("sb_teacher_token");
  document.cookie = "sb_teacher_session=; path=/; max-age=0; SameSite=Lax";
  void demoAccountId;
  window.location.href = "/";
}

export function DemoTeacherBanner() {
  const demo = useDemoTeacher();
  if (!demo) return null;

  const { label, urgent } = demoTeacherTimeRemaining(demo.demo_expires_at);

  return (
    <div
      role="status"
      aria-label="Demo teacher account status"
      className={`flex items-center justify-between gap-3 px-4 py-2 text-sm ${
        urgent
          ? "border-b border-red-200 bg-red-50 text-red-800"
          : "border-b border-cyan-200 bg-cyan-50 text-cyan-900"
      }`}
    >
      <span className="flex items-center gap-2">
        {urgent ? (
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <GraduationCap className="h-4 w-4 shrink-0" aria-hidden="true" />
        )}
        <span>
          {urgent && (
            <span className="mr-1 text-xs font-bold tracking-wide uppercase">
              Urgent:
            </span>
          )}
          <span className="font-medium">Teacher demo account</span>
          {" — "}
          <Clock className="mr-0.5 inline h-3 w-3 align-middle" aria-hidden="true" />
          {label}
        </span>
      </span>

      <div className="flex shrink-0 items-center gap-2">
        <LinkButton href="/signup/teacher" size="sm" className="h-7 text-xs">
          Get full access
        </LinkButton>
        <button
          onClick={() => handleTeacherDemoSignOut(demo.demo_account_id)}
          aria-label="Sign out of teacher demo"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium opacity-70 transition-opacity hover:opacity-100"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </div>
  );
}
