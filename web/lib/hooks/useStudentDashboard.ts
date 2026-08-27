import { useQuery } from "@tanstack/react-query";

import api from "@/lib/api/client";
import type { StudentDashboard } from "@/lib/types/api";

/**
 * The student dashboard payload (#640).
 *
 * One request for the whole page: subjects and scores, standing against the
 * grade cohort, and what to do next. The server resolves which curriculum the
 * student is actually served, so this is a single round trip rather than the
 * page assembling it from three partial endpoints.
 */
export function useStudentDashboard() {
  return useQuery({
    queryKey: ["student-dashboard"],
    queryFn: async () => {
      const res = await api.get<StudentDashboard>("/student/dashboard");
      return res.data;
    },
  });
}
