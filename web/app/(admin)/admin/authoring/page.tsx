"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/authoring/StatusBadge";
import {
  listProjects,
  createProject,
  type CreateProjectInput,
} from "@/lib/api/authoring";

const LANGS = ["en", "fr", "es"] as const;

export default function AuthoringListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["admin", "authoring", "projects"],
    queryFn: listProjects,
    staleTime: 15_000,
  });

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Sparkles className="h-6 w-6 text-indigo-600" />
            Curriculum Authoring Studio
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Paste a table of contents, structure and review the flow, generate content,
            and publish to the platform catalog. Super-admin only.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" /> New project
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : !projects || projects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">No authoring projects yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 text-sm font-medium text-indigo-600 hover:underline"
          >
            Create your first project
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Title</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Grade</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Languages
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Visibility
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {projects.map((p) => (
                <tr
                  key={p.project_id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/admin/authoring/${p.project_id}`)}
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    <Link
                      href={`/admin/authoring/${p.project_id}`}
                      className="hover:text-indigo-600"
                    >
                      {p.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.grade ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{p.languages.join(", ")}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.visibility}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(p.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateProjectModal
          onClose={() => setShowCreate(false)}
          onCreated={(id) => {
            void queryClient.invalidateQueries({
              queryKey: ["admin", "authoring", "projects"],
            });
            router.push(`/admin/authoring/${id}`);
          }}
        />
      )}
    </div>
  );
}

function CreateProjectModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [grade, setGrade] = useState<string>("");
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [rawToc, setRawToc] = useState("");

  const createMut = useMutation({
    mutationFn: (input: CreateProjectInput) => createProject(input),
    onSuccess: (res) => onCreated(res.project_id),
  });

  const canSubmit =
    title.trim().length > 0 && rawToc.trim().length > 0 && languages.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-bold text-gray-900">New authoring project</h2>

        <label className="mb-1 block text-sm font-medium text-gray-700">Title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Grade 9 Physics"
          className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
        />

        <div className="mb-4 flex gap-4">
          <div className="w-28">
            <label className="mb-1 block text-sm font-medium text-gray-700">Grade</label>
            <input
              type="number"
              min={1}
              max={12}
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              placeholder="9"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Languages
            </label>
            <div className="flex gap-2 pt-1.5">
              {LANGS.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() =>
                    setLanguages((prev) =>
                      prev.includes(l) ? prev.filter((x) => x !== l) : [...prev, l],
                    )
                  }
                  className={cn(
                    "rounded-full px-3 py-1 text-sm font-medium",
                    languages.includes(l)
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                  )}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        <label className="mb-1 block text-sm font-medium text-gray-700">
          Table of contents (paste free text)
        </label>
        <textarea
          value={rawToc}
          onChange={(e) => setRawToc(e.target.value)}
          rows={10}
          placeholder={
            "Chapter 1: Motion\n  1.1 Speed and velocity\n  1.2 Acceleration\nChapter 2: Forces\n  2.1 Newton's Laws"
          }
          className="mb-2 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:outline-none"
        />

        {createMut.isError && (
          <p className="mb-2 text-sm text-red-600">
            Could not create the project. Check the fields and try again.
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            disabled={!canSubmit || createMut.isPending}
            onClick={() =>
              createMut.mutate({
                title: title.trim(),
                grade: grade ? Number(grade) : null,
                languages,
                raw_toc: rawToc,
              })
            }
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {createMut.isPending ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
