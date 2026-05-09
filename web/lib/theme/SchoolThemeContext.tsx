"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSubjectPalette, type SubjectPalette } from "./getSubjectPalette";
import { DEFAULT_THEME, type SchoolTheme } from "./defaults";
import schoolApi from "@/lib/api/school-client";
import studentApi from "@/lib/api/client";

// ── Context ───────────────────────────────────────────────────────────────────

const SchoolThemeContext = createContext<SchoolTheme>(DEFAULT_THEME);

// ── Internal fetchers ─────────────────────────────────────────────────────────

async function fetchSchoolTheme(schoolId: string): Promise<SchoolTheme | null> {
  const res = await schoolApi.get<{ theme: SchoolTheme | null }>(
    `/schools/${schoolId}/theme`,
  );
  return res.data.theme;
}

async function fetchStudentSchoolTheme(): Promise<SchoolTheme | null> {
  const res = await studentApi.get<{ theme: SchoolTheme | null }>(
    "/student/school-theme",
  );
  return res.data.theme;
}

// ── School portal provider (uses teacher JWT → school_id) ─────────────────────

export function SchoolPortalThemeProvider({ children }: { children: ReactNode }) {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data } = useQuery({
    queryKey: ["school-theme", schoolId],
    queryFn: () => fetchSchoolTheme(schoolId),
    enabled: !!schoolId,
    staleTime: 5 * 60_000,
    retry: false,
  });

  return (
    <SchoolThemeContext.Provider value={data ?? DEFAULT_THEME}>
      {children}
    </SchoolThemeContext.Provider>
  );
}

// ── Student portal provider (resolves school via enrollment) ──────────────────

export function StudentPortalThemeProvider({ children }: { children: ReactNode }) {
  const { data } = useQuery({
    queryKey: ["student-school-theme"],
    queryFn: fetchStudentSchoolTheme,
    staleTime: 5 * 60_000,
    retry: false,
  });

  return (
    <SchoolThemeContext.Provider value={data ?? DEFAULT_THEME}>
      {children}
    </SchoolThemeContext.Provider>
  );
}

// ── Explicit-value provider for live preview in Customize page ────────────────

export function SchoolThemeProvider({
  children,
  value,
}: {
  children: ReactNode;
  value: SchoolTheme;
}) {
  return (
    <SchoolThemeContext.Provider value={value}>{children}</SchoolThemeContext.Provider>
  );
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSchoolTheme(): SchoolTheme {
  return useContext(SchoolThemeContext);
}

export function useSubjectPalette(subjectKey: string): SubjectPalette {
  const theme = useSchoolTheme();
  const subject = theme.subjects[subjectKey];
  const accent =
    subject?.accent ?? DEFAULT_THEME.subjects[subjectKey]?.accent ?? "#4f46e5";
  return getSubjectPalette(accent);
}
