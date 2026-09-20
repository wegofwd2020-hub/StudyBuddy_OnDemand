/**
 * Group data by Grade > Subject hierarchy (EH-004)
 *
 * Used to transform flat report data into collapsible hierarchy.
 * Mirrors groupByGradeThenSubject but with generic items.
 */

import type { GroupedItem } from "./grouped-schemas";

export function groupByGradeAndSubject<T extends { grade: number; subject: string }>(
  items: T[],
): GroupedItem<T>[] {
  const map = new Map<string, T[]>();

  // Group by "grade|subject" key
  for (const item of items) {
    const key = `${item.grade}|${item.subject}`;
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key)!.push(item);
  }

  // Convert to sorted array
  return Array.from(map.entries())
    .map(([key, itemList]) => {
      const [grade, subject] = key.split("|");
      return {
        grade: parseInt(grade, 10),
        subject,
        items: itemList,
      };
    })
    .sort((a, b) => a.grade - b.grade || a.subject.localeCompare(b.subject));
}

export function getAvailableFilters<T extends { grade: number; subject: string }>(
  items: T[],
): {
  grades: number[];
  subjects: string[];
} {
  const grades = new Set<number>();
  const subjects = new Set<string>();

  for (const item of items) {
    grades.add(item.grade);
    subjects.add(item.subject);
  }

  return {
    grades: Array.from(grades).sort((a, b) => a - b),
    subjects: Array.from(subjects).sort(),
  };
}
