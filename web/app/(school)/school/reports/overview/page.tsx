"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getOverviewReport,
  type ReportPeriod,
  type OverviewUnitRef,
} from "@/lib/api/reports";
import { groupByGradeThenSubject } from "@/lib/reports/grouping";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "term", label: "This term" },
];

/** Units grouped by Grade, then subject (#773).
 *
 * Same shape as the Engagement report's card, via the same shared helper —
 * the issue asks for "display format similar to Reports->Engagement->Units with
 * zero activity", and two hand-rolled copies would drift apart invisibly. */
function GroupedUnits({
  units,
  badgeClass,
}: {
  units: OverviewUnitRef[];
  badgeClass: string;
}) {
  return (
    <div className="space-y-3">
      {groupByGradeThenSubject(units).map(([gradeLabel, subjects]) => (
        <div key={gradeLabel} className="space-y-1.5">
          <h3 className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
            {gradeLabel}
          </h3>
          {subjects.map(([subjectName, rows]) => (
            <div key={subjectName} className="flex flex-wrap items-baseline gap-1.5">
              <span className="text-xs text-gray-400">{subjectName}</span>
              {rows.map((u) => (
                <Badge key={u.unit_id} className={badgeClass} title={u.unit_id}>
                  {u.unit_name}
                </Badge>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function OverviewReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [period, setPeriod] = useState<ReportPeriod>("7d");
  // #773. Grade narrows the whole cohort; subject narrows only the two unit
  // lists — a subject is a property of a unit, not of a student.
  const [grade, setGrade] = useState<number | null>(null);
  const [subject, setSubject] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["report-overview", schoolId, period, grade, subject],
    queryFn: () => getOverviewReport(schoolId, period, grade, subject),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  // From the server's scope, never from the rows on screen.
  const availableGrades = data?.available_grades ?? [];
  const availableSubjects = data?.available_subjects ?? [];

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

      {/* Grade / Subject filters (#773). Each rendered only where there is a
          choice to make — a school with one grade gets no control rather than
          one that cannot change anything. */}
      {(availableGrades.length > 1 || availableSubjects.length > 1) && (
        <div className="flex flex-wrap items-center gap-4">
          {availableGrades.length > 1 && (
            <div
              role="radiogroup"
              aria-label="Filter by grade"
              className="flex flex-wrap items-center gap-2"
            >
              <span className="text-xs text-gray-500">Grade</span>
              {[null, ...availableGrades].map((g) => (
                <button
                  key={g ?? "all"}
                  type="button"
                  role="radio"
                  aria-checked={grade === g}
                  onClick={() => setGrade(g)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    grade === g
                      ? "bg-gray-900 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                  )}
                >
                  {g === null ? "All grades" : `Grade ${g}`}
                </button>
              ))}
            </div>
          )}
          {availableSubjects.length > 1 && (
            <div
              role="radiogroup"
              aria-label="Filter by subject"
              className="flex flex-wrap items-center gap-2"
            >
              <span className="text-xs text-gray-500">Subject</span>
              {[null, ...availableSubjects].map((sub) => (
                <button
                  key={sub ?? "all"}
                  type="button"
                  role="radio"
                  aria-checked={subject === sub}
                  onClick={() => setSubject(sub)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    subject === sub
                      ? "bg-gray-900 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                  )}
                >
                  {sub ?? "All subjects"}
                </button>
              ))}
            </div>
          )}
          {subject !== null && (
            <span className="text-xs text-gray-400">
              subject filters the unit lists only
            </span>
          )}
        </div>
      )}
      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {[
              { label: "Enrolled", value: data.enrolled_students ?? 0 },
              {
                label: "Active",
                value: data.active_pct != null ? `${data.active_pct.toFixed(0)}%` : "—",
                sub: `${data.active_students_period ?? 0} students`,
              },
              { label: "Lessons viewed", value: data.lessons_viewed ?? 0 },
              { label: "Quiz attempts", value: data.quiz_attempts ?? 0 },
              {
                label: "1st-attempt pass rate",
                value:
                  data.first_attempt_pass_rate_pct != null
                    ? `${data.first_attempt_pass_rate_pct.toFixed(0)}%`
                    : "—",
                highlight:
                  data.first_attempt_pass_rate_pct != null &&
                  data.first_attempt_pass_rate_pct < 60
                    ? "red"
                    : "green",
              },
              {
                label: "Audio play rate",
                value:
                  data.audio_play_rate_pct != null
                    ? `${data.audio_play_rate_pct.toFixed(0)}%`
                    : "—",
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
                {!data.units_with_struggles?.length ? (
                  <p className="text-xs text-gray-400">None — all units healthy.</p>
                ) : (
                  <GroupedUnits
                    units={data.units_with_struggles}
                    badgeClass="border-orange-200 bg-orange-50 text-xs text-orange-700"
                  />
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
                {!data.units_no_activity?.length ? (
                  <p className="text-xs text-gray-400">All units have activity.</p>
                ) : (
                  <GroupedUnits
                    units={data.units_no_activity}
                    badgeClass="border-gray-200 bg-gray-100 text-xs text-gray-500"
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
