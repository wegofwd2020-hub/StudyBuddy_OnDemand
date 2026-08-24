import { useQuery } from "@tanstack/react-query";
import { getQuiz } from "@/lib/api/content";

/**
 * Fetch the quiz for a unit.
 *
 * `sessionId` is required before fetching (#567): the session decides which of
 * the three quiz sets is served, so asking for content before an attempt exists
 * would leave the server to pick — which is what used to rotate the questions
 * out from under a student mid-attempt.
 *
 * Keyed by session as well as unit, so a new attempt fetches its own set rather
 * than reading the previous attempt's from cache.
 */
export function useQuiz(unitId: string, sessionId: string | null) {
  return useQuery({
    queryKey: ["quiz", unitId, sessionId],
    queryFn: () => getQuiz(unitId, sessionId as string),
    enabled: !!unitId && !!sessionId,
  });
}
