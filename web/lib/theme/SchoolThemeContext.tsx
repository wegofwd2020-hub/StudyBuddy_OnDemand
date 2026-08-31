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
      {/* The warm-neutral scope for the school portal (see app/globals.css).
          It lives HERE rather than in app/(school)/layout.tsx because that
          layout returns from two branches — local-auth and Auth0 — and both
          already wrap in this provider. One wrapper cannot drift out of sync
          with the other the way two copies would.

          display:contents, so the portal's own `flex min-h-screen` shell stays
          a direct child and nothing about the layout changes. The per-school
          theme this provider carries is identity plus SUBJECT ACCENTS — hex
          values applied directly — so it does not interact with the neutral
          remap.

          Deliberately NOT applied to StudentPortalThemeProvider below: that is
          a separate surface and a separate decision. */}
      <div className="sb-warm-neutrals">{children}</div>
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
