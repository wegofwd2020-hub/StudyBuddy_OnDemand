// Academic-subject-derived accents for the open-book view (/school/content/[id]).
// Distinct from stream-accents (curriculum-stream-level) and status-accents
// (adoption-state-level). Resolves a unit's subject string to a WCAG-AA-safe color.

const SUBJECT_ACCENT_PATTERNS: Array<[RegExp, string]> = [
  [/\bmath/i, "#4f46e5"], // indigo-600
  [/\bscience\b|\bphysic|\bchemist|\bbiolog/i, "#059669"], // emerald-600
  [/\benglish\b|\blanguag/i, "#db2777"], // pink-600
  [/\bcommerce\b|\baccount|\beconom|\bbusiness|\bfinanc/i, "#ca8a04"], // yellow-600
  [/\bhumanit|\bsocial|\bhistor|\bgeograph|\bcivics?\b|\bpolit/i, "#7c3aed"], // violet-600
  [/\bcomputer|\bcs\b|\bcoding|\btechnolog|\binformat/i, "#0891b2"], // cyan-600
  [/\bart\b|\bmusic|\bdrama|\bdance/i, "#ea580c"], // orange-600
  [/\bphys\.?\s*ed|\bfitness|\bsport/i, "#dc2626"], // red-600
  [/\breading\b/i, "#ea580c"], // orange-600
  [/\bworld\b/i, "#e11d48"], // rose-600
];

export function deriveSubjectAccent(subject: string): string {
  for (const [pattern, color] of SUBJECT_ACCENT_PATTERNS) {
    if (pattern.test(subject)) return color;
  }
  return "#4f46e5"; // indigo fallback
}
