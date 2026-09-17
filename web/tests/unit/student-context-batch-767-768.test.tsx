/**
 * #767 + #768 — student portal: sign out where people look for it, and say which
 * subject you are in.
 *
 * #767: "move logout option to top right hand side corner". The SCHOOL portal
 * already did this (#367 AP-4, AccountMenu); the student portal still had
 * "Sign out" at the bottom of the left rail.
 *
 * #768: "subject name is not displayed on certain pages" — lesson, quiz and
 * tutorial pages showed the unit title with nothing saying which subject it
 * belongs to. Tutorial content carries no `subject` field at all, so all three
 * pages resolve it the same way: from the curriculum tree, by unit id.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { CurriculumTree } from "@/lib/types/api";

const TREE: CurriculumTree = {
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
    {
      subject: "Economics",
      units: [
        {
          unit_id: "G11-ECON-001",
          title: "Statistics for Economics",
          subject: "Economics",
          grade: 11,
          sort_order: 1,
          has_lab: false,
        },
      ],
    },
  ],
} as CurriculumTree;

vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => ({ data: TREE, isLoading: false, isError: false }),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useParams: () => ({ unit_id: "G11-ACC-001" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/lib/hooks/useDemoStudent", () => ({ useDemoStudent: () => null }));

import { useUnitSubject } from "@/lib/hooks/useUnitSubject";
import { StudentNav } from "@/components/layout/StudentNav";
import { AccountMenu } from "@/components/layout/AccountMenu";
import { renderHook } from "@testing-library/react";

describe("#768 — a unit's subject comes from the curriculum tree", () => {
  it("resolves the subject for a unit", () => {
    expect(renderHook(() => useUnitSubject("G11-ACC-001")).result.current).toBe(
      "Accountancy",
    );
    expect(renderHook(() => useUnitSubject("G11-ECON-001")).result.current).toBe(
      "Economics",
    );
  });

  it("returns null for a unit the tree does not contain", () => {
    // A student can open a unit that is not in their resolved curriculum (#758
    // history). Showing a wrong subject would be worse than showing none.
    expect(renderHook(() => useUnitSubject("G5-ENG-001")).result.current).toBeNull();
  });
});

describe("#767 — student sign out lives in the top-right account menu", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("is offered by the account menu", () => {
    render(<AccountMenu userName="Venky_Gr11" portal="student" />);
    fireEvent.click(screen.getByRole("button", { name: /account menu/i }));
    expect(screen.getByRole("menuitem", { name: /sign out/i })).toBeInTheDocument();
  });

  it("offers the student's own settings and help links, not the school's", () => {
    render(<AccountMenu userName="Venky_Gr11" portal="student" />);
    fireEvent.click(screen.getByRole("button", { name: /account menu/i }));
    // The mocked next/link renders a plain <a>, so query anchors rather than the
    // menuitem role the real component sets.
    const links = screen.getAllByRole("link").map((el) => el.getAttribute("href"));
    expect(links).toContain("/account/settings");
    expect(links).toContain("/help");
    expect(links.some((h) => h?.startsWith("/school"))).toBe(false);
  });

  it("is no longer in the left rail", () => {
    render(<StudentNav />);
    expect(screen.queryByRole("button", { name: /sign out/i })).toBeNull();
    // The rail keeps navigation.
    expect(screen.getByRole("link", { name: /subjects/i })).toBeInTheDocument();
  });
});
