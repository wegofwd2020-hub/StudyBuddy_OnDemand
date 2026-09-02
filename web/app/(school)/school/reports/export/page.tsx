"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getOverviewReport,
  getTrendsReport,
  getCurriculumHealth,
  type ReportPeriod,
  type ReportType,
  type TrendsPeriod,
} from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Check } from "lucide-react";
import Papa from "papaparse";

const REPORT_OPTIONS: { value: ReportType; label: string; description: string }[] = [
  {
    value: "overview",
    label: "Overview Report",
    description: "KPI summary for the selected period",
  },
  {
    value: "trends",
    label: "Trends Report",
    description: "Week-over-week lesson views and scores",
  },
  {
    value: "curriculum-health",
    label: "Unit Performance",
    description: "Per-unit pass rates and health tiers",
  },
];

// The period options differ per report, on purpose.
//
// A tester asked whether it is right that the dashboard offers 7 days / 30 days
// / this term while Trends offers 4 weeks / 12 weeks / this term. It is: the two
// reports are different KINDS of thing. The overview is a snapshot of a window,
// where days are the natural unit. Trends buckets into ISO weeks and plots them
// against each other, so "last 7 days" would be a single data point — not a
// trend at all.
//
// So this page offers each report ITS OWN periods rather than one shared
// selector. A shared control would have to either drop options that only make
// sense for one report, or imply a "7 days" trends export that cannot exist.
// The labels are copied verbatim from the two on-screen reports so a teacher
// picking "12 weeks" here gets the same thing "12 weeks" means there.
const OVERVIEW_PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "term", label: "This term" },
];

const TRENDS_PERIODS: { value: TrendsPeriod; label: string }[] = [
  { value: "4w", label: "4 weeks" },
  { value: "12w", label: "12 weeks" },
  { value: "term", label: "This term" },
];

type DownloadState = "idle" | "loading" | "done" | "error";

export default function ExportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [reportType, setReportType] = useState<ReportType>("overview");
  // One state per report rather than a shared union, so switching reports keeps
  // each choice and neither needs casting to the other's period type.
  const [overviewPeriod, setOverviewPeriod] = useState<ReportPeriod>("30d");
  const [trendsPeriod, setTrendsPeriod] = useState<TrendsPeriod>("12w");
  // Unit Performance has no period but it does have a grade filter, and the
  // export has to offer it. A filter that exists on screen and not in the
  // download recreates the defect this page's period selector was added to
  // fix — the teacher reads one population and downloads another.
  const [healthGrade, setHealthGrade] = useState<number | null>(null);
  const [state, setState] = useState<DownloadState>("idle");

  // Unfiltered, so the picker offers every grade the caller may choose. Shares
  // a cache key with the Unit Performance page's own unfiltered query, so
  // arriving here from that report costs no extra request.
  const { data: healthMeta } = useQuery({
    queryKey: ["curriculum-health", schoolId, null],
    queryFn: () => getCurriculumHealth(schoolId, null),
    enabled: !!schoolId && reportType === "curriculum-health",
    staleTime: 120_000,
  });
  const availableGrades = healthMeta?.available_grades ?? [];

  async function handleExport() {
    if (!schoolId) return;
    setState("loading");
    try {
      // Friendly column headers ("%", not "pct"). `fields` is kept explicit so an
      // empty dataset still produces a header row instead of a BOM-only file (which
      // Excel renders as the junk "\u00EF\u00BB\u00BF"). See feedback tickets #452 / #453.
      let rows: Record<string, unknown>[] = [];
      let fields: string[] = [];
      let filename = "export.csv";
      if (reportType === "overview") {
        const data = await getOverviewReport(schoolId, overviewPeriod);
        fields = [
          "Enrolled students",
          "Active students",
          "Active %",
          "Lessons viewed",
          "Quiz attempts",
          "First-attempt pass rate %",
          "Audio play rate %",
          "Unreviewed feedback",
        ];
        rows = [
          {
            "Enrolled students": data.enrolled_students,
            "Active students": data.active_students_period,
            "Active %": data.active_pct.toFixed(1),
            "Lessons viewed": data.lessons_viewed,
            "Quiz attempts": data.quiz_attempts,
            "First-attempt pass rate %": data.first_attempt_pass_rate_pct.toFixed(1),
            "Audio play rate %": data.audio_play_rate_pct.toFixed(1),
            "Unreviewed feedback": data.unreviewed_feedback_count,
          },
        ];
        filename = `overview_${data.period}.csv`;
      } else if (reportType === "trends") {
        const data = await getTrendsReport(schoolId, trendsPeriod);
        fields = [
          "Week start",
          "Active students",
          "Lessons viewed",
          "Quiz attempts",
          "Average score %",
          "First-attempt pass rate %",
        ];
        rows = data.weeks.map((w) => ({
          "Week start": w.week_start,
          "Active students": w.active_students,
          "Lessons viewed": w.lessons_viewed,
          "Quiz attempts": w.quiz_attempts,
          "Average score %": w.avg_score_pct.toFixed(1),
          "First-attempt pass rate %": w.first_attempt_pass_rate_pct.toFixed(1),
        }));
        filename = `trends_${trendsPeriod}.csv`;
      } else if (reportType === "curriculum-health") {
        const data = await getCurriculumHealth(schoolId, healthGrade);
        fields = [
          "Unit ID",
          "Unit name",
          "Subject",
          "Health tier",
          "First-attempt pass rate %",
          "Average score %",
          "Avg attempts to pass",
          "Feedback count",
          "Recommended action",
        ];
        rows = data.units.map((u) => ({
          "Unit ID": u.unit_id,
          "Unit name": u.unit_name ?? "",
          Subject: u.subject,
          "Health tier": u.health_tier,
          "First-attempt pass rate %": u.first_attempt_pass_rate_pct.toFixed(1),
          "Average score %": u.avg_score_pct.toFixed(1),
          "Avg attempts to pass": u.avg_attempts_to_pass.toFixed(2),
          "Feedback count": u.feedback_count,
          "Recommended action": u.recommended_action,
        }));
        // Feedback that names no unit has no row to live on, so without this the
        // file silently omits it and the total cannot be reconciled against the
        // dashboard — which is exactly what was reported. A labelled trailing
        // row is honest: it is visibly not a unit, and it accounts for the
        // difference rather than leaving the reader to find it.
        if (data.general_feedback_count) {
          rows.push({
            "Unit ID": "—",
            "Unit name": "General feedback (not tied to a unit)",
            Subject: "",
            "Health tier": "",
            "First-attempt pass rate %": "",
            "Average score %": "",
            "Avg attempts to pass": "",
            "Feedback count": data.general_feedback_count,
            "Recommended action": "",
          });
        }
        // The grade goes in the NAME, not only in the contents. Two downloads
        // an hour apart both called `unit_performance.csv` sit in the same
        // folder covering different populations, and nothing in the file says
        // which is which.
        filename =
          healthGrade === null
            ? "unit_performance.csv"
            : `unit_performance_grade_${healthGrade}.csv`;
      }
      const csv = Papa.unparse({ fields, data: rows });
      const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setState("done");
      setTimeout(() => setState("idle"), 3000);
    } catch {
      setState("error");
    }
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Export CSV</h1>
      <p className="text-sm text-gray-500">
        Download report data as a CSV file. Data is fetched from the API and generated
        in-browser — no server-side processing required for standard exports.
      </p>
      <Card className="border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Select report</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {REPORT_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${reportType === opt.value ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`}
            >
              <input
                type="radio"
                className="sr-only"
                name="report_type"
                value={opt.value}
                checked={reportType === opt.value}
                onChange={() => setReportType(opt.value)}
              />
              <div
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 ${reportType === opt.value ? "border-blue-600" : "border-gray-300"}`}
              >
                {reportType === opt.value && (
                  <div className="h-2 w-2 rounded-full bg-blue-600" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{opt.label}</p>
                <p className="mt-0.5 text-xs text-gray-400">{opt.description}</p>
              </div>
            </label>
          ))}
        </CardContent>
      </Card>

      {/* Period.
          Every export used to be hardcoded — the overview always 30 days, trends
          always 12 weeks — so a teacher who had just read "this term" on screen
          downloaded a file covering something else, with nothing saying so. */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Period</CardTitle>
        </CardHeader>
        <CardContent>
          {reportType === "overview" && (
            <div
              role="radiogroup"
              aria-label="Overview period"
              className="flex flex-wrap gap-2"
            >
              {OVERVIEW_PERIODS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  role="radio"
                  aria-checked={overviewPeriod === p.value}
                  onClick={() => setOverviewPeriod(p.value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    overviewPeriod === p.value
                      ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}

          {reportType === "trends" && (
            <>
              <div
                role="radiogroup"
                aria-label="Trends period"
                className="flex flex-wrap gap-2"
              >
                {TRENDS_PERIODS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    role="radio"
                    aria-checked={trendsPeriod === p.value}
                    onClick={() => setTrendsPeriod(p.value)}
                    className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                      trendsPeriod === p.value
                        ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                        : "border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <p className="mt-3 text-xs text-gray-500">
                Trends are measured in whole weeks, so this report offers weeks where the
                dashboard offers days — a seven-day trend would be a single point.
              </p>
            </>
          )}

          {/* Unit Performance genuinely has no period: the endpoint takes none and
              the figures cover all activity to date. Saying so is the point. A
              selector that silently did not apply is the same defect in a
              friendlier costume.

              It does take a GRADE, though, and that control belongs here for the
              same reason the period one does — whatever narrows the report on
              screen has to narrow the download too. */}
          {reportType === "curriculum-health" && (
            <>
              <p className="text-sm text-gray-600">
                Unit Performance covers{" "}
                <span className="font-medium">all activity to date</span> and is not
                filtered by period.
              </p>
              {availableGrades.length > 1 && (
                <div
                  role="radiogroup"
                  aria-label="Grade"
                  className="mt-3 flex flex-wrap items-center gap-2"
                >
                  <span className="text-sm text-gray-500">Grade</span>
                  {[null, ...availableGrades].map((g) => (
                    <button
                      key={g ?? "all"}
                      type="button"
                      role="radio"
                      aria-checked={healthGrade === g}
                      onClick={() => setHealthGrade(g)}
                      className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                        healthGrade === g
                          ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                          : "border-gray-200 text-gray-600 hover:border-gray-300"
                      }`}
                    >
                      {g === null ? "All grades" : `Grade ${g}`}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
      {state === "error" && (
        <p className="text-sm text-red-600">Export failed. Please try again.</p>
      )}
      {/* The visible label narrates progress ("Generating…", "Downloaded"), but
          the accessible name must not: a screen-reader user tabbing back to a
          control they just used should still hear what it DOES, not what it did
          three seconds ago. */}
      <Button
        onClick={handleExport}
        aria-label="Download CSV"
        disabled={state === "loading" || !schoolId}
        className="gap-2"
      >
        {state === "loading" ? (
          "Generating…"
        ) : state === "done" ? (
          <>
            <Check className="h-4 w-4" />
            Downloaded
          </>
        ) : (
          <>
            <Download className="h-4 w-4" />
            Download CSV
          </>
        )}
      </Button>
    </div>
  );
}
