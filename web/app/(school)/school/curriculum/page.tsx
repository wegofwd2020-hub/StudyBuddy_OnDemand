"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  uploadCurriculumXlsx,
  triggerPipeline,
  downloadXlsxTemplate,
  type UploadError,
} from "@/lib/api/curriculum-admin";
import {
  uploadCurriculumJSON,
  triggerSchoolPipeline,
  getSchoolLimits,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { LinkButton } from "@/components/ui/link-button";
import {
  Upload,
  Download,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileJson,
  FileSpreadsheet,
} from "lucide-react";
import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "success" | "error";
type Tab = "json" | "xlsx";

// ── Quota indicator ───────────────────────────────────────────────────────────

function QuotaIndicator({ schoolId }: { schoolId: string }) {
  const { data } = useQuery({
    queryKey: ["school-limits", schoolId],
    queryFn: () => getSchoolLimits(schoolId),
    staleTime: 60_000,
  });

  if (!data) return null;

  const used = data.pipeline_runs_this_month;
  const total = data.pipeline_quota_monthly;
  const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0;
  const isWarning = pct >= 80;
  const isExhausted = used >= total;
  const resetDate = new Date(data.pipeline_resets_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        isExhausted
          ? "border-red-200 bg-red-50"
          : isWarning
            ? "border-amber-200 bg-amber-50"
            : "border-gray-200 bg-gray-50",
      )}
    >
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span
          className={cn(
            "font-medium",
            isExhausted ? "text-red-700" : isWarning ? "text-amber-700" : "text-gray-600",
          )}
        >
          Pipeline quota — {used} / {total} runs this month
        </span>
        <span className="text-gray-400">Resets {resetDate}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-200">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isExhausted ? "bg-red-500" : isWarning ? "bg-amber-400" : "bg-blue-500",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isExhausted && (
        <p className="mt-1.5 text-xs text-red-600">
          Quota exhausted. Upgrade your plan or wait until {resetDate}.
        </p>
      )}
    </div>
  );
}

// ── JSON upload section ───────────────────────────────────────────────────────

function JsonPipelineSection({ schoolId }: { schoolId: string }) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [year, setYear] = useState(new Date().getFullYear());
  const [langs, setLangs] = useState<Set<string>>(new Set(["en"]));
  const [force, setForce] = useState(false);
  const [state, setState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<{ grade: number; unitCount: number } | null>(null);

  const { data: limits } = useQuery({
    queryKey: ["school-limits", schoolId],
    queryFn: () => getSchoolLimits(schoolId),
    staleTime: 60_000,
  });
  const quotaExhausted =
    limits != null && limits.pipeline_runs_this_month >= limits.pipeline_quota_monthly;

  function toggleLang(lang: string) {
    setLangs((prev) => {
      const next = new Set(prev);
      if (next.has(lang)) {
        if (next.size === 1) return prev; // must have at least one
        next.delete(lang);
      } else {
        next.add(lang);
      }
      return next;
    });
  }

  function handleFileChange() {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setParsed(null);
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result as string);
        const grade = json.grade as number | undefined;
        const units: unknown[] = json.units ?? [];
        if (!grade || !Array.isArray(units)) throw new Error("bad shape");
        setParsed({ grade, unitCount: units.length });
        setError(null);
      } catch {
        setParsed(null);
        setError("Invalid JSON — expected { grade, units: [...] }");
      }
    };
    reader.readAsText(file);
  }

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setState("uploading");
    setError(null);
    try {
      const uploaded = await uploadCurriculumJSON(schoolId, file, year);
      const triggered = await triggerSchoolPipeline(schoolId, {
        langs: Array.from(langs).join(","),
        force,
        year,
      });
      setState("success");
      router.push(`/school/curriculum/jobs/${triggered.job_id}`);
    } catch (err: unknown) {
      setState("error");
      const msg =
        err != null &&
        typeof err === "object" &&
        "response" in err &&
        err.response != null &&
        typeof err.response === "object" &&
        "data" in err.response &&
        err.response.data != null &&
        typeof err.response.data === "object" &&
        "detail" in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : "Upload failed. Check the file and try again.";
      setError(msg);
    }
  }

  const canTrigger =
    !quotaExhausted && langs.size > 0 && !!fileRef.current?.files?.[0] && !error;

  return (
    <div className="space-y-4">
      <QuotaIndicator schoolId={schoolId} />

      <div className="space-y-1.5">
        <Label htmlFor="json_file">Grade JSON file</Label>
        <input
          id="json_file"
          ref={fileRef}
          type="file"
          accept=".json"
          onChange={handleFileChange}
          className="block w-full cursor-pointer text-sm text-gray-600 file:mr-3 file:rounded file:border file:border-gray-200 file:bg-white file:px-3 file:py-1.5 file:text-xs file:font-medium hover:file:bg-gray-50"
        />
        <p className="text-xs text-gray-400">
          Must match the pipeline JSON schema — <code>{`{ grade, units: [...] }`}</code>
        </p>
      </div>

      {parsed && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
          <CheckCircle className="h-3.5 w-3.5 shrink-0" />
          Grade {parsed.grade} — {parsed.unitCount} unit{parsed.unitCount !== 1 ? "s" : ""}{" "}
          detected
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="json_year">Academic year</Label>
          <Input
            id="json_year"
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            min={2024}
            max={2099}
          />
        </div>

        <div className="space-y-1.5">
          <Label>Languages</Label>
          <div className="flex gap-2">
            {(["en", "fr", "es"] as const).map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => toggleLang(lang)}
                className={cn(
                  "rounded border px-3 py-1.5 text-xs font-medium transition-colors",
                  langs.has(lang)
                    ? "border-blue-500 bg-blue-500 text-white"
                    : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50",
                )}
              >
                {lang.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={force}
          onChange={(e) => setForce(e.target.checked)}
          className="rounded border-gray-300"
        />
        Force rebuild (regenerate existing units)
      </label>

      <Button
        onClick={handleUpload}
        disabled={state === "uploading" || !canTrigger}
        className="gap-2"
      >
        {state === "uploading" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading…
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            Upload &amp; trigger pipeline
          </>
        )}
      </Button>

      {quotaExhausted && (
        <p className="text-xs text-red-600">
          Monthly quota exhausted — pipeline trigger disabled.
        </p>
      )}
    </div>
  );
}

// ── XLSX section (unchanged existing flow) ────────────────────────────────────

function XlsxSection({ schoolId }: { schoolId: string }) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [grade, setGrade] = useState(8);
  const [year, setYear] = useState(new Date().getFullYear());
  const [name, setName] = useState("");
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadErrors, setUploadErrors] = useState<UploadError[]>([]);
  const [unitCount, setUnitCount] = useState<number | null>(null);

  async function handleTemplateDownload() {
    try {
      const blob = await downloadXlsxTemplate();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "curriculum_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently fail — user can retry
    }
  }

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file || !schoolId) return;

    setUploadState("uploading");
    setUploadErrors([]);

    try {
      const result = await uploadCurriculumXlsx(
        file,
        grade,
        year,
        name || `Grade ${grade} — ${year}`,
      );

      if (result.errors.length > 0 || !result.curriculum_id) {
        setUploadErrors(result.errors);
        setUploadState("error");
        return;
      }

      setUnitCount(result.unit_count);
      setUploadState("success");

      const { job_id } = await triggerPipeline(result.curriculum_id);
      router.push(`/school/curriculum/pipeline/${job_id}`);
    } catch {
      setUploadState("error");
      setUploadErrors([
        {
          row: 0,
          field: "file",
          message: "Upload failed. Check the file format and try again.",
        },
      ]);
    }
  }

  return (
    <div className="space-y-4">
      {/* Template download */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Step 1 — Download the template</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-gray-600">
            Fill in the XLSX template with your unit titles, subjects, and grade. Each row
            is one unit.
          </p>
          <Button variant="outline" onClick={handleTemplateDownload} className="gap-2">
            <Download className="h-4 w-4" />
            Download XLSX template
          </Button>
        </CardContent>
      </Card>

      {/* Upload form */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Step 2 — Upload your curriculum</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="grade">Grade</Label>
              <select
                id="grade"
                value={grade}
                onChange={(e) => setGrade(Number(e.target.value))}
                className="h-9 w-full rounded-md border border-gray-200 bg-white px-3 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
                  <option key={g} value={g}>
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="xlsx_year">Academic year</Label>
              <Input
                id="xlsx_year"
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                min={2024}
                max={2099}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="curriculum_name">Curriculum name (optional)</Label>
            <Input
              id="curriculum_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. Grade ${grade} Curriculum — ${year}`}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="xlsx_file">XLSX file</Label>
            <input
              id="xlsx_file"
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls"
              className="block w-full cursor-pointer text-sm text-gray-600 file:mr-3 file:rounded file:border file:border-gray-200 file:bg-white file:px-3 file:py-1.5 file:text-xs file:font-medium hover:file:bg-gray-50"
            />
          </div>

          <Button
            onClick={handleUpload}
            disabled={uploadState === "uploading"}
            className="gap-2"
          >
            {uploadState === "uploading" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload &amp; generate content
              </>
            )}
          </Button>

          {uploadState === "success" && unitCount !== null && (
            <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              <CheckCircle className="h-4 w-4 shrink-0" />
              Uploaded {unitCount} unit{unitCount !== 1 ? "s" : ""}. Redirecting to
              pipeline status…
            </div>
          )}
        </CardContent>
      </Card>

      {uploadErrors.length > 0 && (
        <Card className="border border-red-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-red-700">
              <AlertCircle className="h-4 w-4" />
              {uploadErrors.length} upload error{uploadErrors.length !== 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-red-50">
                  <th className="w-16 px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Row
                  </th>
                  <th className="w-32 px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Field
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Error
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {uploadErrors.map((err, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-500">
                      {err.row > 0 ? err.row : "—"}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">
                      {err.field}
                    </td>
                    <td className="px-4 py-2.5 text-red-600">{err.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CurriculumPage() {
  const teacher = useTeacher();
  const [tab, setTab] = useState<Tab>("json");

  const schoolId = teacher?.school_id ?? "";

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Curriculum Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            Upload a custom curriculum and trigger AI content generation for your school.
          </p>
        </div>
        <LinkButton href="/school/curriculum/jobs" variant="outline" size="sm">
          View all jobs
        </LinkButton>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
        <button
          type="button"
          onClick={() => setTab("json")}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            tab === "json"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700",
          )}
        >
          <FileJson className="h-4 w-4" />
          JSON Upload
        </button>
        <button
          type="button"
          onClick={() => setTab("xlsx")}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            tab === "xlsx"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700",
          )}
        >
          <FileSpreadsheet className="h-4 w-4" />
          XLSX Upload
        </button>
      </div>

      {/* Tab content */}
      {tab === "json" ? (
        <Card className="border shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Upload grade JSON &amp; trigger pipeline</CardTitle>
            <p className="text-sm text-gray-500">
              Upload a pipeline-schema JSON file. Content will be generated for the
              selected languages.
            </p>
          </CardHeader>
          <CardContent>
            {schoolId ? (
              <JsonPipelineSection schoolId={schoolId} />
            ) : (
              <p className="text-sm text-gray-400">Loading…</p>
            )}
          </CardContent>
        </Card>
      ) : (
        schoolId && <XlsxSection schoolId={schoolId} />
      )}
    </div>
  );
}
