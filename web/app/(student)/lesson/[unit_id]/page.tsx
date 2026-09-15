"use client";

import { use, useRef } from "react";
import { useLesson } from "@/lib/hooks/useLesson";
import { LessonRenderer } from "@/components/content/LessonRenderer";
import { AudioPlayer } from "@/components/content/AudioPlayer";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { useContentView } from "@/lib/hooks/useContentView";
import { AIContentDisclosure } from "@/components/content/AIContentDisclosure";
import { contentErrorMessage } from "@/lib/content-error";
import { FlaskConical, FileQuestion } from "lucide-react";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function LessonPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const { data: lesson, isLoading, isError, error } = useLesson(unit_id);

  const audioPlayedRef = useRef(false);

  // Records the view and flushes the duration. Shared with the tutorial and
  // experiment pages (#569) so the three cannot drift — this effect used to
  // live only here, which is exactly why the other two recorded nothing.
  useContentView(unit_id, !!lesson, "lesson", audioPlayedRef);

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4 p-6">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/5" />
      </div>
    );
  }

  if (isError || !lesson) {
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
      <div className="max-w-3xl space-y-6 p-6">
        {/* Audio player */}
        {lesson.has_audio && (
          <AudioPlayer
            unitId={unit_id}
            onPlayed={() => {
              audioPlayedRef.current = true;
            }}
          />
        )}

        {/* Lesson content */}
        <LessonRenderer lesson={lesson} />

        <AIContentDisclosure />

        {/* Action bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <FeedbackWidget unitId={unit_id} contentType="lesson" />
          <div className="flex gap-2">
            {lesson.has_audio && (
              <LinkButton
                href={`/tutorial/${unit_id}`}
                variant="outline"
                size="sm"
                className="gap-1"
              >
                <FlaskConical className="h-3.5 w-3.5" />
                Tutorial
              </LinkButton>
            )}
            <LinkButton href={`/quiz/${unit_id}`} size="sm" className="gap-1">
              <FileQuestion className="h-3.5 w-3.5" />
              Take Quiz
            </LinkButton>
          </div>
        </div>
      </div>
    </div>
  );
}
