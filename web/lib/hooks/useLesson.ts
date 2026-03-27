import { useQuery } from "@tanstack/react-query";
import { getLesson, getLessonAudioUrl } from "@/lib/api/content";

export function useLesson(unitId: string) {
  return useQuery({
    queryKey: ["lesson", unitId],
    queryFn: () => getLesson(unitId),
    enabled: !!unitId,
  });
}

export function useLessonAudioUrl(unitId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["lesson-audio", unitId],
    queryFn: () => getLessonAudioUrl(unitId),
    enabled: enabled && !!unitId,
    staleTime: 10 * 60_000, // pre-signed URLs valid ~15 min
  });
}
