"use client";

import { useQuery } from "@tanstack/react-query";
import { HardDrive, Users, Zap } from "lucide-react";

import { getSchoolLimits, getSchoolStorage } from "@/lib/api/school-admin";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * Seats, storage and build runs on the school admin dashboard (#640, C3a).
 *
 * §10 lists this among "what is missing from both wireframes". It is the one
 * class of number on this page that is nobody's teaching concern and entirely
 * the admin's: the questions that end in a bill or a blocked action. A school
 * admin should not have to visit three settings pages to find out they are one
 * teacher away from their seat limit.
 *
 * school_admin only — a teacher has no reason to see commercial limits and
 * cannot act on them.
 *
 * No new endpoints: /limits and /storage already back the Subscription and
 * Storage pages. This surfaces what they return rather than adding a fourth
 * definition of "seats used".
 */

function Meter({ pct, danger }: { pct: number; danger: boolean }) {
  return (
    <div
      className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-100"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn("h-full rounded-full", danger ? "bg-red-500" : "bg-indigo-500")}
        style={{ width: `${Math.min(Math.max(pct, 0), 100)}%` }}
      />
    </div>
  );
}

function UsageTile({
  title,
  value,
  caption,
  pct,
  danger,
  icon,
}: {
  title: string;
  value: string;
  caption: string;
  pct: number;
  danger: boolean;
  icon: React.ReactNode;
}) {
  return (
    <Card className="border shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-gray-400">
          {icon}
          <p className="text-xs font-medium tracking-wide uppercase">{title}</p>
        </div>
        <p
          className={cn(
            "mt-1 text-xl font-bold",
            danger ? "text-red-600" : "text-gray-900",
          )}
        >
          {value}
        </p>
        <Meter pct={pct} danger={danger} />
        <p className="mt-1 text-xs text-gray-400">{caption}</p>
      </CardContent>
    </Card>
  );
}

export function CommercialStrip({ schoolId }: { schoolId: string }) {
  const { data: limits, isLoading: limitsLoading } = useQuery({
    queryKey: ["school-limits", schoolId],
    queryFn: () => getSchoolLimits(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });

  const { data: storage, isLoading: storageLoading } = useQuery({
    queryKey: ["school-storage", schoolId],
    queryFn: () => getSchoolStorage(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });

  if (limitsLoading || storageLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!limits && !storage) return null;

  // A limit of 0 means unlimited on this plan, not "full" — dividing by it
  // would render an unlimited plan as permanently over quota.
  const pct = (used: number, max: number) => (max > 0 ? (used / max) * 100 : 0);

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-gray-500 uppercase">
        Your plan
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {limits && (
          <>
            <UsageTile
              title="Student seats"
              value={`${limits.seats_used_students} / ${limits.max_students || "∞"}`}
              caption={limits.plan}
              pct={pct(limits.seats_used_students, limits.max_students)}
              danger={
                limits.max_students > 0 &&
                limits.seats_used_students >= limits.max_students
              }
              icon={<Users className="h-4 w-4" />}
            />
            <UsageTile
              title="Teacher seats"
              value={`${limits.seats_used_teachers} / ${limits.max_teachers || "∞"}`}
              caption={limits.plan}
              pct={pct(limits.seats_used_teachers, limits.max_teachers)}
              danger={
                limits.max_teachers > 0 &&
                limits.seats_used_teachers >= limits.max_teachers
              }
              icon={<Users className="h-4 w-4" />}
            />
            <UsageTile
              title="Content builds"
              value={`${limits.pipeline_runs_this_month} / ${limits.pipeline_quota_monthly || "∞"}`}
              caption="this month"
              pct={pct(limits.pipeline_runs_this_month, limits.pipeline_quota_monthly)}
              danger={
                limits.pipeline_quota_monthly > 0 &&
                limits.pipeline_runs_this_month >= limits.pipeline_quota_monthly
              }
              icon={<Zap className="h-4 w-4" />}
            />
          </>
        )}
        {storage && (
          <UsageTile
            title="Storage"
            value={`${storage.used_gb.toFixed(1)} / ${storage.total_gb} GB`}
            caption={storage.over_quota ? "over quota" : "in use"}
            pct={storage.used_pct}
            danger={storage.over_quota}
            icon={<HardDrive className="h-4 w-4" />}
          />
        )}
      </div>
    </section>
  );
}
