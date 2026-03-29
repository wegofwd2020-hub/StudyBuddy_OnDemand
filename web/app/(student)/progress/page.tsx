"use client";

import { useProgressHistory } from "@/lib/hooks/useProgress";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle2, XCircle, Clock } from "lucide-react";

export default function ProgressPage() {
  const { data: history, isLoading } = useProgressHistory(50);

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-3xl space-y-6 p-6">
        <h1 className="text-2xl font-bold text-gray-900">Progress History</h1>

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
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
              <Card key={session.session_id} className="border shadow-sm">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-gray-900">
                        {session.unit_title}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-400">
                        {session.subject} ·{" "}
                        {new Date(session.started_at).toLocaleDateString(undefined, {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        })}
                        {" · "}
                        Attempt #{session.attempt_number}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {session.passed !== null && (
                        <>
                          {session.passed ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-400" />
                          )}
                          {session.score !== null && (
                            <span className="text-sm font-medium text-gray-700">
                              {session.score}/{session.total}
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <LinkButton
                      href={`/lesson/${session.unit_id}`}
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                    >
                      Lesson
                    </LinkButton>
                    <LinkButton
                      href={`/quiz/${session.unit_id}`}
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
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
