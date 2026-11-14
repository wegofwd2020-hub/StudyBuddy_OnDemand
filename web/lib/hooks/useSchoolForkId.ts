import { useQuery } from "@tanstack/react-query";
import { getLibrary } from "@/lib/api/school-admin";

export function useSchoolForkId(schoolId: string, curriculumId: string) {
  const library = useQuery({
    queryKey: ["library", schoolId],
    queryFn: () => getLibrary(schoolId),
    enabled: !!schoolId && !!curriculumId,
    staleTime: 30_000,
  });

  const adoptions = library.data?.adoptions ?? [];
  const forkId =
    adoptions.find((a) => a.curriculum_id === curriculumId)?.forked_curriculum_id ??
    (adoptions.some((a) => a.forked_curriculum_id === curriculumId)
      ? curriculumId
      : null);

  return { forkId, isLoading: library.isLoading };
}
