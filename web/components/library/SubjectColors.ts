export { useSubjectPalette } from "@/lib/theme/SchoolThemeContext";
export type { SubjectPalette } from "@/lib/theme/getSubjectPalette";

export function subjectAriaId(subjectKey: string): string {
  const slug = subjectKey
    .normalize("NFKD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `aisle-${slug || "subject"}`;
}
