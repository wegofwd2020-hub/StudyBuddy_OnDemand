// Default theme used when a school has not customized yet.
// Matches SUBJECT_PALETTES_DEFAULT from SBS_2/handoff/reference/LibraryShared.jsx.

export type SubjectKey = "Reading" | "Math" | "Science" | "World";

export interface SubjectThemeEntry {
  accent: string;
  label: string;
}

export interface SchoolIdentity {
  name: string;
  logoText: string;
  logoUrl: string | null;
}

export interface SchoolTheme {
  school: SchoolIdentity;
  subjects: Record<string, SubjectThemeEntry>;
}

export const DEFAULT_THEME: SchoolTheme = {
  school: {
    name: "StudyBuddy",
    logoText: "StudyBuddy",
    logoUrl: null,
  },
  subjects: {
    Reading: { accent: "#ea580c", label: "Reading" },
    Math: { accent: "#4f46e5", label: "Math" },
    Science: { accent: "#059669", label: "Science" },
    World: { accent: "#e11d48", label: "World" },
  },
};

export const SUBJECT_ORDER: SubjectKey[] = ["Reading", "Math", "Science", "World"];
