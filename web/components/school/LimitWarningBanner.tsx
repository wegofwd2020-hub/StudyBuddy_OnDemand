"use client";

/**
 * LimitWarningBanner
 *
 * Fetches subscription + storage data for the current school and renders
 * a dismissible amber banner when any resource crosses the 80% threshold.
 * Renders nothing when all resources are healthy or data is loading.
 *
 * Placed inside the school layout so it appears on every school page.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolSubscription, getSchoolStorage } from "@/lib/api/school-admin";
import { AlertTriangle, X } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface Warning {
  key: string;
  message: string;
  href: string;
  linkLabel: string;
}

function pct(used: number, max: number): number {
  return max > 0 ? (used / max) * 100 : 0;
}

export function LimitWarningBanner() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const { data: sub } = useQuery({
    queryKey: ["school-subscription", schoolId],
    queryFn: () => getSchoolSubscription(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const { data: storage } = useQuery({
    queryKey: ["school-storage", schoolId],
    queryFn: () => getSchoolStorage(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  if (!schoolId || !isAdmin) return null;

  const warnings: Warning[] = [];

  // ── Seat warnings ──────────────────────────────────────────────────────────
  if (sub && sub.status === "active") {
    const studentPct = pct(sub.seats_used_students, sub.max_students);
    const teacherPct = pct(sub.seats_used_teachers, sub.max_teachers);

    if (studentPct >= 100) {
      warnings.push({
        key: "students-full",
        message: `Student seats are full (${sub.seats_used_students} / ${sub.max_students}). New enrolments are blocked.`,
        href: "/school/subscription",
        linkLabel: "Upgrade plan",
      });
    } else if (studentPct >= 80) {
      warnings.push({
        key: "students-near",
        message: `${sub.seats_used_students} of ${sub.max_students} student seats used (${Math.round(studentPct)}%).`,
        href: "/school/subscription",
        linkLabel: "View plan",
      });
    }

    if (teacherPct >= 100) {
      warnings.push({
        key: "teachers-full",
        message: `Teacher seats are full (${sub.seats_used_teachers} / ${sub.max_teachers}). New invites are blocked.`,
        href: "/school/subscription",
        linkLabel: "Upgrade plan",
      });
    } else if (teacherPct >= 80) {
      warnings.push({
        key: "teachers-near",
        message: `${sub.seats_used_teachers} of ${sub.max_teachers} teacher seats used (${Math.round(teacherPct)}%).`,
        href: "/school/subscription",
        linkLabel: "View plan",
      });
    }
  }

  // ── Storage warnings ───────────────────────────────────────────────────────
  if (storage) {
    if (storage.over_quota) {
      warnings.push({
        key: "storage-over",
        message: `Storage quota exceeded (${storage.used_gb.toFixed(1)} GB / ${storage.total_gb} GB). Pipeline builds are blocked.`,
        href: "/school/storage",
        linkLabel: "Buy storage",
      });
    } else if (storage.used_pct >= 80) {
      warnings.push({
        key: "storage-near",
        message: `Storage is ${storage.used_pct.toFixed(0)}% full (${storage.used_gb.toFixed(1)} GB / ${storage.total_gb} GB).`,
        href: "/school/storage",
        linkLabel: "View storage",
      });
    }
  }

  const visible = warnings.filter((w) => !dismissed.has(w.key));
  if (visible.length === 0) return null;

  return (
    <div className="space-y-1 px-6 pt-4">
      {visible.map((w) => (
        <div
          key={w.key}
          className={cn(
            "flex items-start gap-3 rounded-lg border px-4 py-3 text-sm",
            w.key.endsWith("-over") || w.key.endsWith("-full")
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-amber-200 bg-amber-50 text-amber-800",
          )}
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="flex-1">
            {w.message}{" "}
            <Link href={w.href} className="font-semibold underline underline-offset-2">
              {w.linkLabel} →
            </Link>
          </span>
          <button
            onClick={() => setDismissed((prev) => new Set([...prev, w.key]))}
            className="shrink-0 opacity-60 hover:opacity-100"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
