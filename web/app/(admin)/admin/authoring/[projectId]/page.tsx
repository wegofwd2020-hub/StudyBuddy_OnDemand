"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Boxes,
  Camera,
  RotateCcw,
  Sparkles,
  Wand2,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/authoring/StatusBadge";
import { StructuredTocEditor } from "@/components/authoring/StructuredTocEditor";
import { TopicReviewPanel } from "@/components/authoring/TopicReviewPanel";
import {
  analyzeProject,
  createSnapshot,
  flowRecheck,
  generate,
  getProject,
  listSnapshots,
  listTopics,
  materialize,
  publishProject,
  restoreSnapshot,
  saveStructure,
  type StructuredTOC,
  type TopicListItem,
} from "@/lib/api/authoring";

const POLLING = new Set(["analyzing", "generating"]);

export default function AuthoringWorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const queryClient = useQueryClient();
  const [selectedTopic, setSelectedTopic] = useState<TopicListItem | null>(null);

  const { data: project, isLoading } = useQuery({
    queryKey: ["admin", "authoring", projectId],
    queryFn: () => getProject(projectId),
    refetchInterval: (q) =>
      POLLING.has((q.state.data?.status as string) ?? "") ? 2500 : false,
  });

  const { data: topicData } = useQuery({
    queryKey: ["admin", "authoring", projectId, "topics"],
    queryFn: () => listTopics(projectId),
    enabled: !!project?.curriculum_id,
    refetchInterval: project?.status === "generating" ? 3000 : false,
  });

  const { data: snapshots } = useQuery({
    queryKey: ["admin", "authoring", projectId, "snapshots"],
    queryFn: () => listSnapshots(projectId),
    enabled: !!project,
  });

  const invalidate = (...extra: string[]) =>
    void queryClient.invalidateQueries({
      queryKey: ["admin", "authoring", projectId, ...extra],
    });
  const invalidateAll = () => {
    invalidate();
    invalidate("topics");
    invalidate("snapshots");
  };

  const analyzeMut = useMutation({
    mutationFn: () => analyzeProject(projectId),
    onSuccess: () => invalidate(),
  });
  const saveStructMut = useMutation({
    mutationFn: (toc: StructuredTOC) => saveStructure(projectId, toc),
    onSuccess: () => invalidate(),
  });
  const materializeMut = useMutation({
    mutationFn: () => materialize(projectId),
    onSuccess: invalidateAll,
  });
  const generateMut = useMutation({
    mutationFn: () => generate(projectId),
    onSuccess: () => invalidate(),
  });
  const snapshotMut = useMutation({
    mutationFn: () => createSnapshot(projectId),
    onSuccess: () => invalidate("snapshots"),
  });
  const restoreMut = useMutation({
    mutationFn: (sid: string) => restoreSnapshot(projectId, sid),
    onSuccess: invalidateAll,
  });
  const recheckMut = useMutation({
    mutationFn: () => flowRecheck(projectId),
    onSuccess: () => invalidate(),
  });
  const publishMut = useMutation({
    mutationFn: (v: "private" | "catalog") => publishProject(projectId, v),
    onSuccess: invalidateAll,
  });

  if (isLoading || !project) {
    return (
      <div className="mx-auto max-w-5xl p-8">
        <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
      </div>
    );
  }

  const topics = topicData?.topics ?? [];
  const allAccepted =
    topics.length > 0 &&
    topics.every((t) => t.content_count > 0 && t.accepted_count === t.content_count);
  const flow = project.flow_report;

  return (
    <div className="mx-auto max-w-5xl p-8">
      <Link
        href="/admin/authoring"
        className="mb-3 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" /> All projects
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Grade {project.grade ?? "—"} · {project.languages.join(", ")} ·{" "}
            <StatusBadge status={project.status} /> · {project.visibility}
          </p>
        </div>
      </div>

      {/* ── Stage 1: TOC + analyze ─────────────────────────────────────── */}
      <Section title="1 · Table of contents" icon={<Sparkles className="h-4 w-4" />}>
        <pre className="mb-3 max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-700">
          {project.raw_toc}
        </pre>
        <button
          disabled={analyzeMut.isPending || project.status === "analyzing"}
          onClick={() => analyzeMut.mutate()}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Wand2 className="h-4 w-4" />
          {project.status === "analyzing"
            ? "Analyzing…"
            : project.structured_toc
              ? "Re-analyze"
              : "Analyze TOC"}
        </button>
        {project.analyze_error && (
          <p className="mt-2 text-sm text-red-600">
            Analysis error: {project.analyze_error}
          </p>
        )}
      </Section>

      {/* ── Flow report ────────────────────────────────────────────────── */}
      {flow && (flow.summary || flow.warnings.length > 0) && (
        <Section title="Flow analysis (advisory)" icon={<Workflow className="h-4 w-4" />}>
          {flow.summary && <p className="mb-2 text-sm text-gray-600">{flow.summary}</p>}
          {flow.warnings.length === 0 ? (
            <p className="text-sm text-emerald-600">No flow issues found.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {flow.warnings.map((w, i) => (
                <li key={i} className="rounded-md bg-amber-50 px-3 py-1.5 text-amber-800">
                  <span className="font-medium">{w.kind}</span>
                  {w.unit ? ` · ${w.unit}` : ""} — {w.detail}
                </li>
              ))}
            </ul>
          )}
          <button
            disabled={recheckMut.isPending}
            onClick={() => recheckMut.mutate()}
            className="mt-2 text-xs font-medium text-indigo-600 hover:underline disabled:opacity-50"
          >
            Re-run full flow analysis
          </button>
        </Section>
      )}

      {/* ── Stage 2: structured TOC editor + materialize ───────────────── */}
      {project.structured_toc && (
        <Section title="2 · Structure & edit topics" icon={<Boxes className="h-4 w-4" />}>
          <StructuredTocEditor
            value={project.structured_toc}
            saving={saveStructMut.isPending}
            onSave={(toc) => saveStructMut.mutate(toc)}
          />
          {!project.curriculum_id && (
            <div className="mt-4 border-t border-gray-100 pt-4">
              <button
                disabled={materializeMut.isPending}
                onClick={() => materializeMut.mutate()}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {materializeMut.isPending
                  ? "Saving to library…"
                  : "Save to library (materialize)"}
              </button>
              <p className="mt-1 text-xs text-gray-500">
                Creates a staged platform curriculum, separate from school content.
              </p>
            </div>
          )}
        </Section>
      )}

      {/* ── Stage 3: generate + topic review ───────────────────────────── */}
      {project.curriculum_id && (
        <Section
          title="3 · Generate & review content"
          icon={<Sparkles className="h-4 w-4" />}
        >
          <div className="mb-3 flex items-center gap-3">
            <button
              disabled={generateMut.isPending || project.status === "generating"}
              onClick={() => generateMut.mutate()}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {project.status === "generating"
                ? "Generating…"
                : topics.some((t) => t.content_count > 0)
                  ? "Regenerate all"
                  : "Generate all topics"}
            </button>
            {project.status === "generating" && (
              <span className="text-xs text-gray-500">
                Generating content — this can take a few minutes.
              </span>
            )}
          </div>

          {topics.length === 0 ? (
            <p className="text-sm text-gray-400">
              No topics yet — generate content above.
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Topic</th>
                    <th className="px-3 py-2 text-left font-medium">Content</th>
                    <th className="px-3 py-2 text-left font-medium">Accepted</th>
                    <th className="w-20" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {topics.map((t) => (
                    <tr key={t.unit_id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium text-gray-900">{t.title}</td>
                      <td className="px-3 py-2 text-gray-600">
                        {t.content_count > 0
                          ? t.contents.map((c) => c.content_type).join(", ")
                          : "—"}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={cn(
                            t.content_count > 0 && t.accepted_count === t.content_count
                              ? "text-emerald-600"
                              : "text-gray-500",
                          )}
                        >
                          {t.accepted_count}/{t.content_count}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        {t.content_count > 0 && (
                          <button
                            onClick={() => setSelectedTopic(t)}
                            className="text-xs font-medium text-indigo-600 hover:underline"
                          >
                            Review
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      )}

      {/* ── Snapshots + publish ─────────────────────────────────────────── */}
      {project.curriculum_id && (
        <Section title="4 · Versions & publish" icon={<Camera className="h-4 w-4" />}>
          <div className="mb-4 flex items-center gap-3">
            <button
              disabled={snapshotMut.isPending}
              onClick={() => snapshotMut.mutate()}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Camera className="h-4 w-4" /> Snapshot now
            </button>
            <span className="text-xs text-gray-500">
              {snapshots?.length ?? 0} snapshot(s)
            </span>
          </div>
          {snapshots && snapshots.length > 0 && (
            <ul className="mb-4 space-y-1 text-sm">
              {snapshots.map((s) => (
                <li key={s.snapshot_id} className="flex items-center gap-3">
                  <span className="font-mono text-xs text-gray-500">
                    #{s.snapshot_number}
                  </span>
                  <span className="text-gray-700">{s.label ?? "(no label)"}</span>
                  <span className="text-xs text-gray-400">
                    {new Date(s.created_at).toLocaleString()}
                  </span>
                  <button
                    disabled={restoreMut.isPending}
                    onClick={() => restoreMut.mutate(s.snapshot_id)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:underline disabled:opacity-50"
                  >
                    <RotateCcw className="h-3 w-3" /> Restore
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="border-t border-gray-100 pt-4">
            {!allAccepted && (
              <p className="mb-2 text-xs text-amber-600">
                Accept every topic&apos;s content before publishing.
              </p>
            )}
            <div className="flex items-center gap-2">
              <button
                disabled={!allAccepted || publishMut.isPending}
                onClick={() => publishMut.mutate("private")}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Publish (private)
              </button>
              <button
                disabled={!allAccepted || publishMut.isPending}
                onClick={() => publishMut.mutate("catalog")}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Publish to school catalog
              </button>
            </div>
            {project.status === "published" && (
              <p className="mt-2 text-sm text-emerald-600">
                Published ({project.visibility}). Curriculum: {project.curriculum_id}
              </p>
            )}
          </div>
        </Section>
      )}

      {selectedTopic && (
        <TopicReviewPanel
          projectId={projectId}
          topic={selectedTopic}
          onClose={() => setSelectedTopic(null)}
          onChanged={() => invalidate("topics")}
        />
      )}
    </div>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-6 rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold tracking-wide text-gray-500 uppercase">
        {icon} {title}
      </h2>
      {children}
    </section>
  );
}
