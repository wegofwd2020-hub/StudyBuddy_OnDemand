"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getOverviewReport,
  getCurriculumHealth,
  type ReportPeriod,
} from "@/lib/api/reports";
import { groupByGradeThenSubject } from "@/lib/reports/grouping";
import { OVERVIEW_PERIODS, OVERVIEW_PERIOD_LABELS } from "@/lib/reports/periods";
import { NoGradesNotice, ScopeNote } from "@/components/school/ScopeNote";
import { KpiCard } from "@/components/school/KpiCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { TrendingDown, Users, AlertTriangle, TrendingUp } from "lucide-react";

/**
 * Engagement report (#770).
 *
 * Rebuilt on the dashboard's vocabulary rather than its own. Before this it was
 * bespoke markup that predated the #640 dashboard redesign and had drifted from
 * it in every way that matters to a reader:
 *
 *   - hand-rolled cards instead of `KpiCard`, so the same figure looked
 *     different depending on which screen you read it on;
 *   - "Last 30 days" hardcoded in prose, with no way to change the window —
 *     the dashboard has offered 7d / 30d / term since #640;
 *   - no `ScopeNote`, so a teacher could not tell whether the numbers covered
 *     their own grades or the whole school. That ambiguity is the defect the
 *     dashboard redesign was actually reported for (#640 §10), and this page
 *     still had it.
 *
 * Grouping by Grade then Subject (#776) already applies to the units list
 * below. The headline figures are school- or scope-wide totals rather than
 * per-grade, so they are NOT grouped: doing so would need a per-grade breakdown
 * the overview endpoint does not return.
 */
export default function EngagementReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [period, setPeriod] = useState<ReportPeriod>("30d");

  const { data: overview, isLoading: loadingOv } = useQuery({
    queryKey: ["report-overview", schoolId, period],
    queryFn: () => getOverviewReport(schoolId, period),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const { data: health, isLoading: loadingHealth } = useQuery({
    queryKey: ["curriculum-health", schoolId],
    queryFn: () => getCurriculumHealth(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const isLoading = loadingOv || loadingHealth;
  const dropoutRiskUnits =
    health?.units.filter((u) => u.health_tier === "no_activity") ?? [];
  const inactiveCount = overview
    ? overview.enrolled_students - overview.active_students_period
    : 0;

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">Engagement Report</h1>
            {/* WHO the numbers cover, beside WHEN — the dashboard has said both
                since #640; this page said neither. */}
            <ScopeNote scope={overview?.scope} />
          </div>
          <p className="mt-0.5 text-xs text-gray-400">
            Showing {OVERVIEW_PERIOD_LABELS[period]}. The units below are not filtered by
            it — a unit nobody has started has no activity in any window.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border bg-white p-1">
          {OVERVIEW_PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              aria-pressed={period === p.value}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
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

      <NoGradesNotice scope={overview?.scope} />

      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {!isLoading && overview && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <KpiCard
              title="Enrolled students"
              value={overview.enrolled_students}
              subtitle="total"
              icon={<Users className="h-5 w-5" />}
              accent="blue"
            />
            <KpiCard
              title="Active"
              value={`${overview.active_pct.toFixed(0)}%`}
              subtitle={OVERVIEW_PERIOD_LABELS[period]}
              icon={<TrendingUp className="h-5 w-5" />}
              accent={overview.active_pct >= 50 ? "green" : "red"}
            />
            <KpiCard
              title="Lessons viewed"
              value={overview.lessons_viewed}
              subtitle={OVERVIEW_PERIOD_LABELS[period]}
              icon={<Users className="h-5 w-5" />}
              accent="blue"
            />
            <KpiCard
              title="Pass rate"
              value={`${overview.first_attempt_pass_rate_pct.toFixed(1)}%`}
              subtitle="first attempt"
              icon={<TrendingUp className="h-5 w-5" />}
              accent={overview.first_attempt_pass_rate_pct >= 70 ? "green" : "red"}
            />
            <KpiCard
              title="Quiz attempts"
              value={overview.quiz_attempts}
              subtitle={OVERVIEW_PERIOD_LABELS[period]}
              icon={<Users className="h-5 w-5" />}
              accent="blue"
            />
            <KpiCard
              title="Unreviewed feedback"
              value={overview.unreviewed_feedback_count}
              subtitle="pending review"
              icon={<AlertTriangle className="h-5 w-5" />}
              accent={overview.unreviewed_feedback_count > 0 ? "red" : "gray"}
            />
          </div>

          {inactiveCount > 0 && (
            <Card className="border border-orange-100 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-orange-700">
                  <TrendingDown className="h-4 w-4" />
                  Inactive students
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  <span className="font-semibold text-orange-700">{inactiveCount}</span>{" "}
                  enrolled student{inactiveCount !== 1 ? "s" : ""} had no activity in{" "}
                  {OVERVIEW_PERIOD_LABELS[period]}.
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  Consider sending a nudge via the notification system.
                </p>
              </CardContent>
            </Card>
          )}

          {dropoutRiskUnits.length > 0 && (
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-gray-700">
                  <AlertTriangle className="h-4 w-4 text-gray-400" />
                  Units with no activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-xs text-gray-500">
                  These units have not been started by any student.
                </p>
                {/* Grouped by Grade, then subject (#776). A flat wall of badges
                    across every grade the school teaches cannot be read: the one
                    question this card exists to answer is "which of MY units are
                    untouched", and that needs the grades separated. */}
                <div className="space-y-4">
                  {groupByGradeThenSubject(dropoutRiskUnits).map(
                    ([gradeLabel, subjects]) => (
                      <div key={gradeLabel} className="space-y-2">
                        <h3 className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
                          {gradeLabel}
                        </h3>
                        {subjects.map(([subject, units]) => (
                          <div
                            key={subject}
                            className="flex flex-wrap items-baseline gap-2"
                          >
                            <span className="text-xs text-gray-400">{subject}</span>
                            {units.map((u) => (
                              <Badge
                                key={u.unit_id}
                                className="border-gray-200 bg-gray-100 text-xs text-gray-500"
                              >
                                {u.unit_name ?? u.unit_id}
                              </Badge>
                            ))}
                          </div>
                        ))}
                      </div>
                    ),
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
