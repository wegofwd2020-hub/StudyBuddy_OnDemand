/**
 * Unit tests for section 3.17 — Teacher Management (`/school/teachers`)
 * Covers TC-IDs: SCH-41, SCH-42, SCH-43, SCH-44
 *
 * Run with:
 *   npm test -- teachers-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TeachersPage from "@/app/(school)/school/teachers/page";
import { SchoolNav } from "@/components/layout/SchoolNav";
import {
  MOCK_ADMIN,
  MOCK_TEACHER,
  TEACHERS_STRINGS,
  TEST_INVITE,
} from "../e2e/data/teachers-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/school/teachers"),
}));

const mockUseTeacher = vi.fn();
vi.mock("@/lib/hooks/useTeacher", () => ({
  useTeacher: vi.fn(() => mockUseTeacher()),
}));

const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    // useMutation without a QueryClient throws in RQ v5. Stub it so it invokes
    // mutationFn + onSuccess/onError, preserving the behaviour mutation tests assert.
    useMutation: vi.fn((opts: Record<string, unknown> = {}) => ({
      mutate: (vars: unknown) =>
        Promise.resolve()
          .then(() => (opts.mutationFn as ((v: unknown) => unknown))?.(vars))
          .then((data) => (opts.onSuccess as ((d: unknown, v: unknown) => void))?.(data, vars))
          .catch((err) => (opts.onError as ((e: unknown, v: unknown) => void))?.(err, vars)),
      mutateAsync: async (vars: unknown) => {
        const data = await (opts.mutationFn as ((v: unknown) => unknown))?.(vars);
        await (opts.onSuccess as ((d: unknown, v: unknown) => void))?.(data, vars);
        return data;
      },
      isPending: false,
      isError: false,
      isSuccess: false,
      data: undefined,
      error: null,
      reset: vi.fn(),
    })),
    useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
  };
});

const mockProvisionTeacher = vi.fn();
vi.mock("@/lib/api/school-admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/school-admin")>();
  return {
    ...actual,
    provisionTeacher: (...args: unknown[]) => mockProvisionTeacher(...args),
  };
});

// ---------------------------------------------------------------------------
// SCH-41 — Add-teacher form visible for school_admin
// (invite flow was replaced by Phase A provisioning)
// ---------------------------------------------------------------------------

describe("SCH-41 — Add-teacher form visible for school_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("heading", { name: TEACHERS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders the Add a teacher card", () => {
    render(<TeachersPage />);
    expect(screen.getByText(TEACHERS_STRINGS.addFormCard)).toBeInTheDocument();
  });

  it("renders the Full name input field", () => {
    render(<TeachersPage />);
    expect(screen.getByLabelText(TEACHERS_STRINGS.nameLabel)).toBeInTheDocument();
  });

  it("renders the Work email input field", () => {
    render(<TeachersPage />);
    expect(screen.getByLabelText(TEACHERS_STRINGS.emailLabel)).toBeInTheDocument();
  });

  it("renders the Add teacher button", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("button", { name: TEACHERS_STRINGS.addBtn }),
    ).toBeInTheDocument();
  });

  it("Add teacher button is disabled when fields are empty", () => {
    render(<TeachersPage />);
    expect(
      screen.getByRole("button", { name: TEACHERS_STRINGS.addBtn }),
    ).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// SCH-42 — Add form hidden for non-admin teacher
// ---------------------------------------------------------------------------

describe("SCH-42 — Add form hidden for non-admin teacher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_TEACHER);
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("does NOT render the add-teacher form for non-admin", () => {
    render(<TeachersPage />);
    expect(screen.queryByText(TEACHERS_STRINGS.addFormCard)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SCH-43 — Successful provisioning
// ---------------------------------------------------------------------------

describe("SCH-43 — Successful provisioning", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
    mockProvisionTeacher.mockResolvedValue({ email: TEST_INVITE.email });
  });

  it("calls provisionTeacher and shows the success message", async () => {
    render(<TeachersPage />);
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.nameLabel), {
      target: { value: TEST_INVITE.name },
    });
    fireEvent.change(screen.getByLabelText(TEACHERS_STRINGS.emailLabel), {
      target: { value: TEST_INVITE.email },
    });
    fireEvent.click(screen.getByRole("button", { name: TEACHERS_STRINGS.addBtn }));
    expect(await screen.findByText(TEACHERS_STRINGS.successMsg)).toBeInTheDocument();
    expect(mockProvisionTeacher).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// SCH-44 — Teachers nav item hidden for non-admin
// ---------------------------------------------------------------------------

describe("SCH-44 — Teachers nav item visibility in SchoolNav", () => {
  beforeEach(() => {
    mockUseQuery.mockReturnValue({ data: { alerts: [] }, isLoading: false });
  });

  it("shows Teachers nav item for school_admin", () => {
    mockUseTeacher.mockReturnValue(MOCK_ADMIN);
    render(<SchoolNav />);
    expect(screen.getByRole("link", { name: "Teachers" })).toBeInTheDocument();
  });

  it("does NOT show Teachers nav item for non-admin teacher", () => {
    mockUseTeacher.mockReturnValue(MOCK_TEACHER);
    render(<SchoolNav />);
    expect(screen.queryByRole("link", { name: "Teachers" })).toBeNull();
  });
});
