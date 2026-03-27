import { useQuery } from "@tanstack/react-query";
import { getCurriculumTree } from "@/lib/api/curriculum";

export function useCurriculumTree() {
  return useQuery({
    queryKey: ["curriculum", "tree"],
    queryFn: getCurriculumTree,
    staleTime: 5 * 60_000,
  });
}
