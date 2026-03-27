"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  uploadCurriculumXlsx,
  triggerPipeline,
  downloadXlsxTemplate,
  type UploadError,
} from "@/lib/api/curriculum-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { LinkButton } from "@/components/ui/link-button";
import { Upload, Download, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

type UploadState = "idle" | "uploading" | "success" | "error";

export default function CurriculumPage() {
  const teacher = useTeacher();
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
    if (!file || !teacher?.school_id) return;

    setUploadState("uploading");
    setUploadErrors([]);

    try {
      const result = await uploadCurriculumXlsx(file, grade, year, name || `Grade ${grade} — ${year}`);

      if (result.errors.length > 0 || !result.curriculum_id) {
        setUploadErrors(result.errors);
        setUploadState("error");
        return;
      }

      setUnitCount(result.unit_count);
      setUploadState("success");

      // Auto-trigger pipeline and navigate to status page
      const { job_id } = await triggerPipeline(result.curriculum_id);
      router.push(`/school/curriculum/pipeline/${job_id}`);
    } catch {
      setUploadState("error");
      setUploadErrors([{ row: 0, field: "file", message: "Upload failed. Check the file format and try again." }]);
    }
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Curriculum Management</h1>
      <p className="text-sm text-gray-500">
        Upload a custom curriculum for your school. After upload, content will be generated
        automatically via the AI pipeline.
      </p>

      {/* Template download */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Step 1 — Download the template</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-3">
            Fill in the XLSX template with your unit titles, subjects, and grade. Each row is one unit.
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
                className="w-full h-9 rounded-md border border-gray-200 px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
                  <option key={g} value={g}>Grade {g}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="year">Academic year</Label>
              <Input
                id="year"
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
              placeholder={`e.g. Grade ${grade} STEM — ${year}`}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="xlsx_file">XLSX file</Label>
            <input
              id="xlsx_file"
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls"
              className="block w-full text-sm text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-gray-200 file:text-xs file:font-medium file:bg-white hover:file:bg-gray-50 cursor-pointer"
            />
          </div>

          <Button
            onClick={handleUpload}
            disabled={uploadState === "uploading"}
            className="gap-2"
          >
            {uploadState === "uploading" ? (
              <><Loader2 className="h-4 w-4 animate-spin" />Uploading…</>
            ) : (
              <><Upload className="h-4 w-4" />Upload & generate content</>
            )}
          </Button>

          {/* Success state */}
          {uploadState === "success" && unitCount !== null && (
            <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">
              <CheckCircle className="h-4 w-4 shrink-0" />
              Uploaded {unitCount} unit{unitCount !== 1 ? "s" : ""}. Redirecting to pipeline status…
            </div>
          )}
        </CardContent>
      </Card>

      {/* Per-row error table */}
      {uploadErrors.length > 0 && (
        <Card className="border border-red-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              {uploadErrors.length} upload error{uploadErrors.length !== 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-red-50">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 w-16">Row</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 w-32">Field</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {uploadErrors.map((err, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-500">{err.row > 0 ? err.row : "—"}</td>
                    <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">{err.field}</td>
                    <td className="px-4 py-2.5 text-red-600">{err.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Pipeline history link */}
      <p className="text-xs text-gray-400 text-center">
        To check a previous pipeline run, go to{" "}
        <LinkButton href="/school/dashboard" variant="outline" size="sm" className="text-xs h-6 px-2">
          Dashboard
        </LinkButton>
      </p>
    </div>
  );
}
