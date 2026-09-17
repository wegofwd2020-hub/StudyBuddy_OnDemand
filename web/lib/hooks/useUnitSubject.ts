"use client";

import { useMemo } from "react";
import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";

/**
 * The subject a unit belongs to, or null (#768).
 *
 * Lesson and quiz bodies carry a `subject`, tutorials do not, and none of the
 * three agree on spelling for stream curricula (pitfall #32: the stored value is
 * a CODE like `G11-ACC`). The curriculum tree already resolves display names, so
 * all three student pages read the subject from one place and cannot disagree.
 *
 * Null rather than a guess when the unit is not in the student's tree — they can
 * still open a unit from an earlier curriculum (#758), and naming the wrong
 * subject is worse than naming none.
 */
export function useUnitSubject(unitId: string): string | null {
  const { data: tree } = useCurriculumTree();
  return useMemo(() => {
    for (const subject of tree?.subjects ?? []) {
      if (subject.units.some((u) => u.unit_id === unitId)) return subject.subject;
    }
    return null;
  }, [tree, unitId]);
}
