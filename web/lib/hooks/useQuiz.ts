import { useQuery } from "@tanstack/react-query";
import { getQuiz } from "@/lib/api/content";

export function useQuiz(unitId: string) {
  return useQuery({
    queryKey: ["quiz", unitId],
    queryFn: () => getQuiz(unitId),
    enabled: !!unitId,
  });
}
