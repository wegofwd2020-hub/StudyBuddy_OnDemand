// Stream-derived accent colors for adopted curricula on /school/library.
// Curriculum names follow patterns like "Grade 8 STEM 2026", "Grade 11 Commerce",
// "Grade 9 English (2026)". The stream is the descriptive token — used to color
// book spines so a school admin can scan a shelf and see subject character at a glance.
// Distinct from DEFAULT_THEME.subjects (which keys on real subject names like Math/Science
// for the student curriculum tree).

export const STREAM_ACCENT: Record<string, string> = {
  STEM: "#0891b2", // cyan-600
  Science: "#059669", // emerald-600
  Commerce: "#ca8a04", // yellow-600
  Humanities: "#7c3aed", // violet-600
  English: "#db2777", // pink-600
  Advanced: "#dc2626", // red-600
  General: "#6b7280", // gray-500
  Other: "#4f46e5", // indigo-600 fallback
};

const STREAM_PATTERNS: Array<[RegExp, keyof typeof STREAM_ACCENT]> = [
  [/\bstem\b/i, "STEM"],
  [/\bscience\b/i, "Science"],
  [/\bcommerce\b/i, "Commerce"],
  [/\bhumanities\b/i, "Humanities"],
  [/\benglish\b/i, "English"],
  [/\badvanced\b/i, "Advanced"],
  [/\bgeneral\b/i, "General"],
];

export function deriveStreamKey(name: string): keyof typeof STREAM_ACCENT {
  for (const [pattern, key] of STREAM_PATTERNS) {
    if (pattern.test(name)) return key;
  }
  return "Other";
}

export function deriveStreamAccent(name: string): string {
  return STREAM_ACCENT[deriveStreamKey(name)];
}
