"use client";

import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getOverviewReport,
  getTrendsReport,
  getCurriculumHealth,
  type ReportType,
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

type DownloadState = "idle" | "loading" | "done" | "error";

export default function ExportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [reportType, setReportType] = useState<ReportType>("overview");
  const [state, setState] = useState<DownloadState>("idle");

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
        const data = await getOverviewReport(schoolId, "30d");
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
        const data = await getTrendsReport(schoolId, "12w");
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
        filename = "trends_12w.csv";
      } else if (reportType === "curriculum-health") {
        const data = await getCurriculumHealth(schoolId);
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
        filename = "unit_performance.csv";
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
      {state === "error" && (
        <p className="text-sm text-red-600">Export failed. Please try again.</p>
      )}
      <Button
        onClick={handleExport}
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
