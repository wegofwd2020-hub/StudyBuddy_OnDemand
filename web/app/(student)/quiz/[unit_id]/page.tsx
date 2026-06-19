"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useQuiz } from "@/lib/hooks/useQuiz";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { Skeleton } from "@/components/ui/skeleton";
import { AIContentDisclosure } from "@/components/content/AIContentDisclosure";
import { contentErrorMessage } from "@/lib/content-error";
import { startSession } from "@/lib/api/progress";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function QuizPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const { data: quiz, isLoading, isError, error } = useQuiz(unit_id);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Open a fresh quiz attempt. Used on first load and on "Try Again" — the
  // latter previously navigated to this same URL, which never reset the player
  // (#459). Clearing sessionId first unmounts the finished QuizPlayer; the new
  // session id remounts it (also keyed below) so its state starts clean.
  const startNew = useCallback(() => {
    setSessionId(null);
    startSession(unit_id, "default")
      .then((r) => setSessionId(r.session_id))
      .catch(() => {});
  }, [unit_id]);

  useEffect(() => {
    if (!quiz) return;
    startNew();
  }, [quiz, startNew]);

  if (isLoading || (quiz && !sessionId)) {
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
            curriculumId="default"
            onRetry={startNew}
          />
        )}
        <AIContentDisclosure />
      </div>
    </div>
  );
}
