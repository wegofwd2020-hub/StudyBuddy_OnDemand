"use client";

import { use, useEffect, useRef } from "react";
import { useLesson } from "@/lib/hooks/useLesson";
import { LessonRenderer } from "@/components/content/LessonRenderer";
import { AudioPlayer } from "@/components/content/AudioPlayer";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { startSession } from "@/lib/api/progress";
import { startLessonView, endLessonView } from "@/lib/api/analytics";
import { FlaskConical, FileQuestion } from "lucide-react";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function LessonPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const { data: lesson, isLoading, isError } = useLesson(unit_id);

  const sessionIdRef = useRef<string | null>(null);
  const viewIdRef = useRef<string | null>(null);
  const startTimeRef = useRef<number>(0);
  const audioPlayedRef = useRef(false);

  // Start session + analytics view on mount
  useEffect(() => {
    if (!lesson) return;
    const curriculumId = "default"; // resolved from JWT in production
    startSession(unit_id, curriculumId)
      .then((r) => {
        sessionIdRef.current = r.session_id;
      })
      .catch(() => {});
    startLessonView(unit_id, curriculumId)
      .then((r) => {
        viewIdRef.current = r.view_id;
      })
      .catch(() => {});
    startTimeRef.current = Date.now();

    return () => {
      // Fire-and-forget on unmount
      if (viewIdRef.current) {
        const duration = Math.round((Date.now() - startTimeRef.current) / 1000);
        endLessonView(viewIdRef.current, duration, audioPlayedRef.current, false).catch(
          () => {},
        );
      }
    };
  }, [lesson, unit_id]);

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
    return (
      <div className="p-6">
        <p className="text-sm text-red-500">Could not load lesson. Please try again.</p>
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
