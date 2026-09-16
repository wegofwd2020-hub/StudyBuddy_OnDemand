/**
 * #760 — one subject, one colour, on every student page.
 *
 * Venki: "Subjects section uses orange color while curriculum map uses blue color
 * for the same elements." Both pages draw subjects as BookSpines, but coloured
 * them from different sources:
 *
 *   Subjects page   deriveSubjectAccent(name)   regex on the subject name
 *   Curriculum map  useSubjectPalette(name)     theme palette, keyed by EXACT name
 *
 * The palette only knows "Reading", "Math", "Science" and "World", so every real
 * subject — Accountancy, Physics, Economics — fell through to indigo on the map
 * while the Subjects page gave it its own colour.
 *
 * The fix is one precedence order in the hook both pages use:
 *   school theme -> default theme (exact name) -> derived from the name -> indigo
 */
import type { ReactNode } from "react";
import { describe, it, expect, vi } from "vitest";
import { cleanup, render, renderHook } from "@testing-library/react";
import { SchoolThemeProvider, useSubjectPalette } from "@/lib/theme/SchoolThemeContext";
import { DEFAULT_THEME, type SchoolTheme } from "@/lib/theme/defaults";
import { deriveSubjectAccent } from "@/lib/theme/subject-accents";
import SubjectsPage from "@/app/(student)/subjects/page";
import CurriculumMapPage from "@/app/(student)/curriculum/page";
import type { CurriculumTree } from "@/lib/types/api";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/components/student/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));
vi.mock("@/lib/hooks/useProgressMap", () => ({
  useUnitStatuses: () => ({ statusByUnit: new Map<string, string>(), isLoading: false }),
}));

const COMMERCE_TREE: CurriculumTree = {
  curriculum_id: "default-2026-g11-commerce",
  grade: 11,
  subjects: [
    {
      subject: "Accountancy",
      units: [
        {
          unit_id: "G11-ACC-001",
          title: "Introduction to Accounting",
          subject: "Accountancy",
          grade: 11,
          sort_order: 1,
          has_lab: false,
        },
      ],
    },
  ],
} as CurriculumTree;

vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => ({ data: COMMERCE_TREE, isLoading: false, isError: false }),
}));

const YELLOW_600 = "#ca8a04";
const EMERALD_600 = "#059669";
const INDIGO_600 = "#4f46e5";

function accentFor(subject: string, theme: SchoolTheme = DEFAULT_THEME): string {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <SchoolThemeProvider value={theme}>{children}</SchoolThemeProvider>
  );
  return renderHook(() => useSubjectPalette(subject), { wrapper }).result.current.accent;
}

describe("#760 — useSubjectPalette precedence", () => {
  it("colours a subject the default theme does not name from its name", () => {
    // The reported case: Commerce subjects were indigo on the map.
    expect(accentFor("Accountancy")).toBe(YELLOW_600);
    expect(accentFor("Business Studies")).toBe(YELLOW_600);
    expect(accentFor("Physics")).toBe(EMERALD_600);
  });

  it("agrees with deriveSubjectAccent for any subject without a theme entry", () => {
    for (const subject of [
      "Accountancy",
      "Economics",
      "Chemistry",
      "History",
      "Coding",
    ]) {
      expect(accentFor(subject)).toBe(deriveSubjectAccent(subject));
    }
  });

  it("keeps the default theme colours for the four named subjects", () => {
    for (const [name, entry] of Object.entries(DEFAULT_THEME.subjects)) {
      expect(accentFor(name)).toBe(entry.accent);
    }
  });

  it("lets a school's own colour win over the derived one", () => {
    const theme: SchoolTheme = {
      ...DEFAULT_THEME,
      subjects: {
        ...DEFAULT_THEME.subjects,
        Accountancy: { accent: "#123456", label: "Accountancy" },
      },
    };
    expect(accentFor("Accountancy", theme)).toBe("#123456");
  });

  it("falls back to indigo for a subject nothing recognises", () => {
    expect(accentFor("Zzyzx")).toBe(INDIGO_600);
  });
});

describe("#760 — the same subject is the same colour on both pages", () => {
  function spineColours(ui: ReactNode): string[] {
    const { container } = render(<>{ui}</>);
    const colours = [
      ...container.querySelectorAll<HTMLElement>("button[data-spine]"),
    ].map((el) => el.style.borderColor);
    cleanup();
    return colours;
  }

  it("colours Accountancy identically on Subjects and the Curriculum map", () => {
    const onSubjects = spineColours(<SubjectsPage />);
    const onMap = spineColours(<CurriculumMapPage />);

    expect(onSubjects.length).toBeGreaterThan(0);
    expect(onMap.length).toBeGreaterThan(0);
    // yellow-600, as jsdom normalises it
    expect(new Set([...onSubjects, ...onMap])).toEqual(new Set(["rgb(202, 138, 4)"]));
  });
});
