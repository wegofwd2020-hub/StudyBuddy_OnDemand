"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getOverviewReport, type ReportPeriod } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "term", label: "This term" },
];

export default function OverviewReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [period, setPeriod] = useState<ReportPeriod>("7d");

  const { data, isLoading } = useQuery({
    queryKey: ["report-overview", schoolId, period],
    queryFn: () => getOverviewReport(schoolId, period),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Overview Report</h1>
        <div className="flex gap-1 rounded-lg border bg-white p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={cn(
                "rounded px-3 py-1.5 text-xs font-medium transition-colors",
                period === p.value
                  ? "bg-blue-600 text-white"
                  : "text-gray-500 hover:text-gray-900",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {[
              { label: "Enrolled", value: data.enrolled_students },
              {
                label: "Active",
                value: `${data.active_pct.toFixed(0)}%`,
                sub: `${data.active_students_period} students`,
              },
              { label: "Lessons viewed", value: data.lessons_viewed },
              { label: "Quiz attempts", value: data.quiz_attempts },
              {
                label: "1st-attempt pass rate",
                value: `${data.first_attempt_pass_rate_pct.toFixed(0)}%`,
                highlight: data.first_attempt_pass_rate_pct < 60 ? "red" : "green",
              },
              {
                label: "Audio play rate",
                value: `${data.audio_play_rate_pct.toFixed(0)}%`,
              },
            ].map(({ label, value, sub, highlight }) => (
              <Card key={label} className="border shadow-sm">
                <CardContent className="p-4">
                  <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                    {label}
                  </p>
                  <p
                    className={cn(
                      "mt-0.5 text-2xl font-bold",
                      highlight === "red" && "text-red-500",
                      highlight === "green" && "text-green-600",
                      !highlight && "text-gray-900",
                    )}
                  >
                    {value}
                  </p>
                  {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-orange-700">
                  Units with struggles
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.units_with_struggles.length === 0 ? (
                  <p className="text-xs text-gray-400">None — all units healthy.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {data.units_with_struggles.map((u) => (
                      <Badge
                        key={u}
                        className="border-orange-200 bg-orange-50 text-xs text-orange-700"
                      >
                        {u}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500">
                  Units with no activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.units_no_activity.length === 0 ? (
                  <p className="text-xs text-gray-400">All units have activity.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {data.units_no_activity.map((u) => (
                      <Badge
                        key={u}
                        className="border-gray-200 bg-gray-100 text-xs text-gray-500"
                      >
                        {u}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
