"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle, Upload } from "lucide-react";
import { uploadGradeJson, triggerAdminPipeline, UploadGradeJsonResponse } from "@/lib/api/admin";

interface SubjectPreview {
  subject_id: string;
  name: string;
  unit_count: number;
}

interface GradeJsonPreview {
  grade: number;
  subjects: SubjectPreview[];
  total_units: number;
}

function parsePreview(data: unknown): GradeJsonPreview | string {
  if (typeof data !== "object" || data === null) return "File must be a JSON object.";
  const obj = data as Record<string, unknown>;
  const grade = obj.grade;
  if (typeof grade !== "number" || grade < 5 || grade > 12) {
    return "'grade' must be an integer between 5 and 12.";
  }
  const subjects = obj.subjects;
  if (!Array.isArray(subjects) || subjects.length === 0) {
    return "'subjects' must be a non-empty array.";
  }
  const previews: SubjectPreview[] = subjects.map((s: unknown, i: number) => {
    if (typeof s !== "object" || s === null) return { subject_id: `[${i}]`, name: `Subject ${i}`, unit_count: 0 };
    const subj = s as Record<string, unknown>;
    const units = Array.isArray(subj.units) ? subj.units : [];
    return {
      subject_id: String(subj.subject_id ?? `subject_${i}`),
      name: String(subj.name ?? `Subject ${i}`),
      unit_count: units.length,
    };
  });
  return {
    grade: grade as number,
    subjects: previews,
    total_units: previews.reduce((acc, s) => acc + s.unit_count, 0),
  };
}

export default function AdminPipelineUploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<1 | 2>(1);
  const [year, setYear] = useState(2026);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<GradeJsonPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadGradeJsonResponse | null>(null);

  const [langs, setLangs] = useState("en");
  const [force, setForce] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setPreview(null);
    setPreviewError(null);
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const result = parsePreview(parsed);
        if (typeof result === "string") {
          setPreviewError(result);
        } else {
          setPreview(result);
        }
      } catch {
        setPreviewError("File is not valid JSON.");
      }
    };
    reader.readAsText(file);
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile) return;
    setUploadError(null);
    setUploading(true);
    try {
      const result = await uploadGradeJson(selectedFile, year);
      setUploadResult(result);
      setStep(2);
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "response" in err &&
        err.response &&
        typeof err.response === "object" &&
        "data" in err.response
      ) {
        const data = (err as { response: { data: { detail?: string; errors?: string[] } } }).response.data;
        const msg = data.detail ?? "Upload failed.";
        const details = data.errors?.join(" ") ?? "";
        setUploadError(details ? `${msg} ${details}` : msg);
      } else {
        setUploadError("Upload failed. Check that the file is a valid grade JSON.");
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleTrigger(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadResult) return;
    setTriggerError(null);
    setTriggering(true);
    try {
      const { job_id } = await triggerAdminPipeline(uploadResult.grade, langs, force, year);
      router.push(`/admin/pipeline/${job_id}`);
    } catch {
      setTriggerError("Failed to trigger pipeline job. Try again.");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg p-8">
      <div className="mb-6">
        <Link
          href="/admin/pipeline"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Pipeline Jobs
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">Upload Grade JSON</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Upload a grade curriculum file, seed the database, then trigger a content build.
        </p>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <div
          className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
            step === 1 ? "bg-indigo-600 text-white" : "bg-green-500 text-white"
          }`}
        >
          {step > 1 ? <CheckCircle className="h-4 w-4" /> : "1"}
        </div>
        <span className={`text-sm font-medium ${step === 1 ? "text-gray-900" : "text-gray-400"}`}>
          Upload &amp; Seed
        </span>
        <div className="h-px flex-1 bg-gray-200" />
        <div
          className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
            step === 2 ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-400"
          }`}
        >
          2
        </div>
        <span className={`text-sm font-medium ${step === 2 ? "text-gray-900" : "text-gray-400"}`}>
          Configure &amp; Build
        </span>
      </div>

      {step === 1 && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <form onSubmit={handleUpload} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Grade JSON file
              </label>
              <div
                className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 px-4 py-8 transition-colors hover:border-indigo-400"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="mb-2 h-8 w-8 text-gray-400" />
                <p className="text-sm text-gray-600">
                  {selectedFile ? selectedFile.name : "Click to select a .json file"}
                </p>
                {selectedFile && (
                  <p className="mt-0.5 text-xs text-gray-400">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            {previewError && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{previewError}</span>
              </div>
            )}

            {preview && (
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
                <p className="mb-2 text-sm font-semibold text-indigo-800">
                  Grade {preview.grade} — {preview.subjects.length} subjects,{" "}
                  {preview.total_units} total units
                </p>
                <ul className="space-y-0.5">
                  {preview.subjects.map((s) => (
                    <li key={s.subject_id} className="flex justify-between text-xs text-indigo-700">
                      <span>{s.name}</span>
                      <span className="font-mono">{s.unit_count} units</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Academic year
              </label>
              <input
                type="number"
                value={year}
                min={2024}
                max={2040}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {uploadError && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!selectedFile || !!previewError || uploading}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
            >
              {uploading ? "Uploading…" : "Upload & Seed"}
            </button>
          </form>
        </div>
      )}

      {step === 2 && uploadResult && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <div className="mb-5 rounded-lg border border-green-200 bg-green-50 p-4">
            <p className="text-sm font-semibold text-green-800">
              Seeded successfully
            </p>
            <p className="mt-1 font-mono text-xs text-green-700">
              {uploadResult.curriculum_id}
            </p>
            <p className="mt-0.5 text-xs text-green-600">
              Grade {uploadResult.grade} · {uploadResult.subject_count} subjects ·{" "}
              {uploadResult.unit_count} units
            </p>
          </div>

          <form onSubmit={handleTrigger} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Languages (comma-separated)
              </label>
              <input
                type="text"
                value={langs}
                onChange={(e) => setLangs(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                placeholder="en,fr,es"
              />
              <p className="mt-1 text-xs text-gray-400">
                Supported: <code>en</code>, <code>fr</code>, <code>es</code>
              </p>
            </div>

            <div className="flex items-center gap-3">
              <input
                id="force"
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="force" className="text-sm text-gray-700">
                Force regenerate (overrides existing content)
              </label>
            </div>

            {triggerError && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{triggerError}</span>
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button
                type="submit"
                disabled={triggering}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
              >
                {triggering ? "Starting…" : "Build Content"}
              </button>
              <Link
                href="/admin/pipeline"
                className="px-5 py-2.5 text-sm text-gray-600 transition-colors hover:text-gray-900"
              >
                Done for now
              </Link>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
