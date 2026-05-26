"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, History, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { SBMarkdown } from "@/components/content/Markdown";
import {
  acceptTopic,
  getTopic,
  getTopicHistory,
  regenerateTopic,
  type ContentType,
  type TopicListItem,
} from "@/lib/api/authoring";

export function TopicReviewPanel({
  projectId,
  topic,
  onClose,
  onChanged,
}: {
  projectId: string;
  topic: TopicListItem;
  onClose: () => void;
  onChanged: () => void;
}) {
  const queryClient = useQueryClient();
  const types = topic.contents.map((c) => c.content_type);
  const [active, setActive] = useState<ContentType>(types[0] ?? "lesson");
  const [showHistory, setShowHistory] = useState(false);
  const [reason, setReason] = useState("");

  const key = ["admin", "authoring", projectId, "topic", topic.unit_id, active];
  const { data: version, isLoading } = useQuery({
    queryKey: key,
    queryFn: () => getTopic(projectId, topic.unit_id, active),
  });
  const { data: history } = useQuery({
    queryKey: [...key, "history"],
    queryFn: () => getTopicHistory(projectId, topic.unit_id, active),
    enabled: showHistory,
  });

  const refetch = () => {
    void queryClient.invalidateQueries({ queryKey: key });
    onChanged();
  };

  const acceptMut = useMutation({
    mutationFn: () => acceptTopic(projectId, topic.unit_id, active),
    onSuccess: refetch,
  });
  const regenMut = useMutation({
    mutationFn: (r: string) => regenerateTopic(projectId, topic.unit_id, active, r),
    onSuccess: () => {
      setReason("");
      refetch();
    },
  });

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col border-l border-gray-200 bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <div>
          <h3 className="font-semibold text-gray-900">{topic.title}</h3>
          <p className="text-xs text-gray-500">
            {topic.subject} · {topic.unit_id}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* content-type tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-gray-100 px-5 py-2">
        {types.map((t) => {
          const c = topic.contents.find((x) => x.content_type === t)!;
          return (
            <button
              key={t}
              onClick={() => {
                setActive(t);
                setShowHistory(false);
              }}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold ring-1",
                active === t
                  ? "bg-indigo-600 text-white ring-indigo-600"
                  : c.review_status === "accepted"
                    ? "bg-emerald-100 text-emerald-800 ring-emerald-300 hover:bg-emerald-200"
                    : "bg-gray-200 text-gray-700 ring-gray-300 hover:bg-gray-300",
              )}
            >
              {t}
              {c.review_status === "accepted" && (
                <Check className="ml-1 inline h-3 w-3" />
              )}
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {isLoading || !version ? (
          <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between text-xs text-gray-500">
              <span className="flex items-center gap-2">
                version {version.version_number}
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-semibold",
                    version.review_status === "accepted"
                      ? "bg-emerald-600 text-white"
                      : "bg-amber-500 text-white",
                  )}
                >
                  {version.review_status}
                </span>
              </span>
              <button
                onClick={() => setShowHistory((v) => !v)}
                className="inline-flex items-center gap-1 hover:text-gray-700"
              >
                <History className="h-3.5 w-3.5" /> {showHistory ? "Hide" : "History"}
              </button>
            </div>

            {showHistory && history && (
              <ul className="mb-4 space-y-1 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                {history.map((h) => (
                  <li key={h.topic_version_id} className="flex items-center gap-2">
                    <span className="font-mono">v{h.version_number}</span>
                    {h.is_active && <span className="text-indigo-600">active</span>}
                    {h.regen_reason && <span className="italic">“{h.regen_reason}”</span>}
                  </li>
                ))}
              </ul>
            )}

            <ContentBody contentType={active} body={version.body} />
          </>
        )}
      </div>

      {/* actions */}
      <div className="border-t border-gray-200 px-5 py-3">
        <div className="mb-2 flex items-center gap-2">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for regeneration (e.g. too terse — add a diagram)"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
          <button
            disabled={reason.trim().length === 0 || regenMut.isPending}
            onClick={() => regenMut.mutate(reason.trim())}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-4 w-4", regenMut.isPending && "animate-spin")} />{" "}
            Regenerate
          </button>
          <button
            disabled={acceptMut.isPending || version?.review_status === "accepted"}
            onClick={() => acceptMut.mutate()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Check className="h-4 w-4" /> Accept
          </button>
        </div>
        {regenMut.data && regenMut.data.flow_recheck.length > 0 && (
          <p className="text-xs text-amber-700">
            Flow recheck flagged {regenMut.data.flow_recheck.length} issue(s) — review
            topic ordering.
          </p>
        )}
        {regenMut.isError && <p className="text-xs text-red-600">Regeneration failed.</p>}
      </div>
    </div>
  );
}

// ── Per-content-type renderers ───────────────────────────────────────────────

function ContentBody({
  contentType,
  body,
}: {
  contentType: ContentType;
  body: Record<string, unknown> | null;
}) {
  if (!body) return <p className="text-sm text-gray-400">No content.</p>;

  if (contentType === "lesson") {
    const sections = (body.sections as { heading: string; body: string }[]) ?? [];
    const keyPoints = (body.key_points as string[]) ?? [];
    return (
      <div className="space-y-4">
        {typeof body.synopsis === "string" && (
          <p className="text-sm text-gray-500 italic">{body.synopsis}</p>
        )}
        {sections.map((s, i) => (
          <section key={i}>
            <h4 className="mb-1 font-semibold text-gray-900">{s.heading}</h4>
            <SBMarkdown className="text-sm">{s.body}</SBMarkdown>
          </section>
        ))}
        {keyPoints.length > 0 && (
          <div>
            <h4 className="mb-1 font-semibold text-gray-900">Key points</h4>
            <ul className="list-disc pl-5 text-sm text-gray-700">
              {keyPoints.map((k, i) => (
                <li key={i}>{k}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  if (contentType === "tutorial") {
    const sections =
      (body.sections as { title: string; content: string; examples?: string[] }[]) ?? [];
    return (
      <div className="space-y-4">
        {typeof body.title === "string" && (
          <h4 className="font-semibold text-gray-900">{body.title}</h4>
        )}
        {sections.map((s, i) => (
          <section key={i}>
            <h5 className="mb-1 font-medium text-gray-800">{s.title}</h5>
            <SBMarkdown className="text-sm">{s.content}</SBMarkdown>
            {(s.examples ?? []).map((ex, j) => (
              <SBMarkdown key={j} className="mt-1 text-sm">
                {ex}
              </SBMarkdown>
            ))}
          </section>
        ))}
      </div>
    );
  }

  if (contentType.startsWith("quiz_set_")) {
    const questions =
      (body.questions as {
        question_text: string;
        options: { option_id: string; text: string }[];
        correct_option: string;
        explanation: string;
        difficulty: string;
      }[]) ?? [];
    return (
      <ol className="space-y-4 text-sm">
        {questions.map((q, i) => (
          <li key={i}>
            <div className="flex items-start gap-1.5 font-medium text-gray-900">
              <span>{i + 1}.</span>
              {/* Render through SBMarkdown so embedded GFM tables / KaTeX / code
                  render instead of showing as raw freeform text. */}
              <div className="min-w-0 flex-1">
                <SBMarkdown className="text-sm">{q.question_text}</SBMarkdown>
              </div>
              <span className="shrink-0 text-xs text-gray-400">({q.difficulty})</span>
            </div>
            <ul className="mt-1 space-y-0.5 pl-4">
              {q.options.map((o) => (
                <li
                  key={o.option_id}
                  className={cn(
                    "flex gap-1.5",
                    o.option_id === q.correct_option
                      ? "font-medium text-emerald-700"
                      : "text-gray-600",
                  )}
                >
                  <span className="shrink-0">{o.option_id}.</span>
                  <div className="min-w-0 flex-1">
                    <SBMarkdown className="text-sm">{o.text}</SBMarkdown>
                  </div>
                  {o.option_id === q.correct_option && (
                    <span className="shrink-0">✓</span>
                  )}
                </li>
              ))}
            </ul>
            <div className="mt-1 text-xs text-gray-500 italic">
              <SBMarkdown className="text-xs">{q.explanation}</SBMarkdown>
            </div>
          </li>
        ))}
      </ol>
    );
  }

  // experiment / fallback
  return (
    <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
      {JSON.stringify(body, null, 2)}
    </pre>
  );
}
