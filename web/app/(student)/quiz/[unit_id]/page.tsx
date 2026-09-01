"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useQuiz } from "@/lib/hooks/useQuiz";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { Skeleton } from "@/components/ui/skeleton";
import { AIContentDisclosure } from "@/components/content/AIContentDisclosure";
import { contentErrorMessage } from "@/lib/content-error";
import { startSession } from "@/lib/api/progress";
import { LinkButton } from "@/components/ui/link-button";
import { BookOpen } from "lucide-react";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function QuizPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startError, setStartError] = useState<unknown>(null);
  // The session is opened FIRST and the quiz is fetched for it (#567). The
  // session decides which of the three sets is served, so fetching content
  // before an attempt exists is what let a refetch rotate the questions
  // mid-attempt — the student saw one set and was graded against another.
  const { data: quiz, isLoading, isError, error } = useQuiz(unit_id, sessionId);

  // Open a fresh quiz attempt. Used on first load and on "Try Again" — the
  // latter previously navigated to this same URL, which never reset the player
  // (#459). Clearing sessionId first unmounts the finished QuizPlayer; the new
  // session id remounts it (also keyed below) so its state starts clean.
  const startNew = useCallback(() => {
    setSessionId(null);
    setStartError(null);
    startSession(unit_id)
      .then((r) => setSessionId(r.session_id))
      // Swallowing this used to be harmless, because the only realistic failure
      // was transient. It is not harmless now: the quiz requires the lesson
      // first, so a student arriving in the wrong order gets a 403 here — and a
      // swallowed 403 leaves sessionId null forever, i.e. a skeleton that never
      // resolves. A dead-end screen is worse than an error message.
      .catch((e) => setStartError(e));
  }, [unit_id]);

  useEffect(() => {
    startNew();
  }, [startNew]);

  // The gate can fire from EITHER call — the session start or the quiz fetch —
  // so both are funnelled through the same copy and the same way out.
  const gateError = startError ?? (isError ? error : null);
  const gate = gateError ? contentErrorMessage(gateError) : null;

  if (gate?.lessonRequired) {
    return (
      <div className="max-w-2xl p-6">
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-5">
          <div className="flex items-start gap-3">
            <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
            <div className="space-y-3">
              <div>
                <p className="font-semibold text-gray-900">Lesson first</p>
                {/* Says what to do next, not what went wrong. A student who
                    lands here has not made a mistake — they arrived in the
                    wrong order, and the way forward is one tap away. */}
                <p className="mt-1 text-sm text-gray-700">
                  Have a read through the lesson, then come back and take the quiz.
                </p>
              </div>
              <LinkButton href={`/lesson/${unit_id}`}>Go to the lesson</LinkButton>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (startError) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-500">{gate?.message}</p>
      </div>
    );
  }

  if (!sessionId || isLoading) {
    return (
      <div className="max-w-2xl space-y-4 p-6">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-32 rounded-lg" />
        <Skeleton className="h-10 w-1/3" />
      </div>
    );
  }

  if (isError || !quiz) {
    const { message, unavailable } = contentErrorMessage(error);
    return (
      <div className="p-6">
        <p className={`text-sm ${unavailable ? "text-gray-500" : "text-red-500"}`}>
          {message}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-2xl p-6">
        <h1 className="mb-6 text-xl font-bold text-gray-900">{quiz.title}</h1>
        {sessionId && (
          <QuizPlayer
            key={sessionId}
            quiz={quiz}
            sessionId={sessionId}
            onRetry={startNew}
          />
        )}
        <AIContentDisclosure />
      </div>
    </div>
  );
}
