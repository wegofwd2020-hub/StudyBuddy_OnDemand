"use client";

import { useProgressHistory } from "@/lib/hooks/useProgress";
import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle2, XCircle, Clock } from "lucide-react";

export default function ProgressPage() {
  const { data: history, isLoading } = useProgressHistory(50);
  // The history endpoint returns unit IDs, not titles, so the list read
  // "G10-MATH-002" where the rest of the product says "Permutations,
  // Combinations, and Probability". The tree already carries titles and is
  // cached by React Query, so this costs nothing the student is waiting on.
  const { data: tree } = useCurriculumTree();

  const titleByUnit = new Map<string, string>();
  tree?.subjects.forEach((s) =>
    s.units.forEach((u) => titleByUnit.set(u.unit_id, u.title)),
  );

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-3xl space-y-6 p-6">
        <h1 className="text-2xl font-bold text-gray-900">Progress History</h1>

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
        ) : !history?.sessions.length ? (
          <div className="space-y-3 py-16 text-center">
            <Clock className="mx-auto h-10 w-10 text-gray-300" />
            <p className="text-gray-400">
              No sessions yet. Start learning to track progress.
            </p>
            <LinkButton href="/subjects">Browse Subjects</LinkButton>
          </div>
        ) : (
          <div className="space-y-3">
            {history.sessions.map((session) => (
              // One line per attempt, score inline, actions on the right
              // (#670, Venki's mock-up). The old card spent three rows and a
              // whole line of buttons on each attempt, which is a lot of
              // vertical space for a view whose entire job is showing many
              // attempts at once.
              <Card key={session.session_id} className="border shadow-sm">
                <CardContent className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {titleByUnit.get(session.unit_id) ?? session.unit_title}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-gray-400">
                      <span>{session.subject}</span>
                      <span aria-hidden="true">·</span>
                      <span>
                        {new Date(session.started_at).toLocaleDateString(undefined, {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>Attempt #{session.attempt_number}</span>
                      {session.passed !== null && session.score !== null && (
                        <>
                          <span aria-hidden="true">·</span>
                          {/* The icon stays: 5/8 alone does not say whether it
                              was a pass, and the pass mark is not 60% at every
                              school (ADR-007). */}
                          {session.passed ? (
                            <CheckCircle2
                              className="h-3.5 w-3.5 text-green-500"
                              aria-hidden="true"
                            />
                          ) : (
                            <XCircle
                              className="h-3.5 w-3.5 text-red-400"
                              aria-hidden="true"
                            />
                          )}
                          <span className="font-medium text-gray-600">
                            Score{" "}
                            {session.total !== null && session.total > 0
                              ? Math.min(session.score, session.total)
                              : session.score}
                            /{session.total}
                          </span>
                          <span className="sr-only">
                            {session.passed ? "Passed" : "Not passed"}
                          </span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <LinkButton
                      href={`/lesson/${session.unit_id}`}
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                    >
                      Lesson
                    </LinkButton>
                    <LinkButton
                      href={`/quiz/${session.unit_id}`}
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                    >
                      Retry quiz
                    </LinkButton>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
