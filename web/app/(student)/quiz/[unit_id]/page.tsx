"use client";

import { use, useEffect, useState } from "react";
import { useQuiz } from "@/lib/hooks/useQuiz";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { Skeleton } from "@/components/ui/skeleton";
import { AIContentDisclosure } from "@/components/content/AIContentDisclosure";
import { startSession } from "@/lib/api/progress";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function QuizPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const { data: quiz, isLoading, isError } = useQuiz(unit_id);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    if (!quiz) return;
    startSession(unit_id, "default")
      .then((r) => setSessionId(r.session_id))
      .catch(() => {});
  }, [quiz, unit_id]);

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
    return (
      <div className="p-6">
        <p className="text-sm text-red-500">Could not load quiz. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-2xl p-6">
        <h1 className="mb-6 text-xl font-bold text-gray-900">{quiz.title}</h1>
        {sessionId && (
          <QuizPlayer quiz={quiz} sessionId={sessionId} curriculumId="default" />
        )}
        <AIContentDisclosure />
      </div>
    </div>
  );
}
