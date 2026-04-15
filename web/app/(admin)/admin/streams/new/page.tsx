"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { createStream } from "@/lib/api/admin";

const CODE_PATTERN = /^[a-z0-9-]+$/;
const RESERVED_CODES = new Set(["none", "other", "all", "default", "null"]);

function validateCode(code: string): string | null {
  if (code.length < 3 || code.length > 30) return "Code must be 3–30 characters.";
  if (!CODE_PATTERN.test(code))
    return "Only lowercase letters, digits, and hyphens allowed.";
  if (RESERVED_CODES.has(code)) return `'${code}' is a reserved code.`;
  return null;
}

export default function AdminStreamsNewPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientError = validateCode(code);
  const canSubmit =
    !clientError && displayName.trim().length > 0 && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createStream({
        code: code.trim().toLowerCase(),
        display_name: displayName.trim(),
        description: description.trim() || undefined,
      });
      router.push(`/admin/streams/${code.trim().toLowerCase()}`);
    } catch (err: unknown) {
      const resp =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: unknown } } }).response
          : undefined;
      const detail = typeof resp?.data?.detail === "string" ? resp.data.detail : null;
      setError(detail ?? "Failed to create stream.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg p-8">
      <Link
        href="/admin/streams"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Streams
      </Link>
      <h1 className="mb-1 text-2xl font-bold text-gray-900">New Stream</h1>
      <p className="mb-6 text-sm text-gray-500">
        Custom streams can be referenced from the Upload page as soon as they're created.
      </p>

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-gray-200 bg-white p-6"
      >
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Code
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toLowerCase())}
            placeholder="e.g. vocational, ib-dp, montessori"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
          {code && clientError && (
            <p className="mt-1 text-xs text-red-600">{clientError}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">
            Lowercase, 3–30 chars. Hyphens allowed.
          </p>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Display name
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Vocational Track"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Description <span className="text-gray-400">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
        >
          {submitting ? "Creating…" : "Create Stream"}
        </button>
      </form>
    </div>
  );
}
