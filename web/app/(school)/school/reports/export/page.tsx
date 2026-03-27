"use client";

import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getOverviewReport, getTrendsReport, getCurriculumHealth, type ReportType } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Check } from "lucide-react";
import Papa from "papaparse";

const REPORT_OPTIONS: { value: ReportType; label: string; description: string }[] = [
  { value: "overview", label: "Overview Report", description: "KPI summary for the selected period" },
  { value: "trends", label: "Trends Report", description: "Week-over-week lesson views and scores" },
  { value: "curriculum-health", label: "Unit Performance", description: "Per-unit pass rates and health tiers" },
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
      let rows: Record<string, unknown>[] = [];
      let filename = "export.csv";
      if (reportType === "overview") {
        const data = await getOverviewReport(schoolId, "30d");
        rows = [{ enrolled_students: data.enrolled_students, active_students: data.active_students_period, active_pct: data.active_pct.toFixed(1), lessons_viewed: data.lessons_viewed, quiz_attempts: data.quiz_attempts, first_attempt_pass_rate_pct: data.first_attempt_pass_rate_pct.toFixed(1), audio_play_rate_pct: data.audio_play_rate_pct.toFixed(1), unreviewed_feedback: data.unreviewed_feedback_count }];
        filename = `overview_${data.period}.csv`;
      } else if (reportType === "trends") {
        const data = await getTrendsReport(schoolId, "12w");
        rows = data.weeks.map((w) => ({ week_start: w.week_start, active_students: w.active_students, lessons_viewed: w.lessons_viewed, quiz_attempts: w.quiz_attempts, avg_score_pct: w.avg_score_pct.toFixed(1), first_attempt_pass_rate_pct: w.first_attempt_pass_rate_pct.toFixed(1) }));
        filename = "trends_12w.csv";
      } else if (reportType === "curriculum-health") {
        const data = await getCurriculumHealth(schoolId);
        rows = data.units.map((u) => ({ unit_id: u.unit_id, unit_name: u.unit_name ?? "", subject: u.subject, health_tier: u.health_tier, first_attempt_pass_rate_pct: u.first_attempt_pass_rate_pct.toFixed(1), avg_score_pct: u.avg_score_pct.toFixed(1), avg_attempts_to_pass: u.avg_attempts_to_pass.toFixed(2), feedback_count: u.feedback_count, recommended_action: u.recommended_action }));
        filename = "unit_performance.csv";
      }
      const csv = Papa.unparse(rows);
      const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
      setState("done");
      setTimeout(() => setState("idle"), 3000);
    } catch {
      setState("error");
    }
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Export CSV</h1>
      <p className="text-sm text-gray-500">Download report data as a CSV file. Data is fetched from the API and generated in-browser — no server-side processing required for standard exports.</p>
      <Card className="border shadow-sm">
        <CardHeader className="pb-3"><CardTitle className="text-base">Select report</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {REPORT_OPTIONS.map((opt) => (
            <label key={opt.value} className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${reportType === opt.value ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`}>
              <input type="radio" className="sr-only" name="report_type" value={opt.value} checked={reportType === opt.value} onChange={() => setReportType(opt.value)} />
              <div className={`mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${reportType === opt.value ? "border-blue-600" : "border-gray-300"}`}>
                {reportType === opt.value && <div className="w-2 h-2 rounded-full bg-blue-600" />}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{opt.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{opt.description}</p>
              </div>
            </label>
          ))}
        </CardContent>
      </Card>
      {state === "error" && <p className="text-sm text-red-600">Export failed. Please try again.</p>}
      <Button onClick={handleExport} disabled={state === "loading" || !schoolId} className="gap-2">
        {state === "loading" ? "Generating…" : state === "done" ? <><Check className="h-4 w-4" />Downloaded</> : <><Download className="h-4 w-4" />Download CSV</>}
      </Button>
    </div>
  );
}
