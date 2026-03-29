/**
 * Unit tests for section 4.13 — RBAC Sidebar Filtering
 * Covers TC-IDs: ADM-66, ADM-67, ADM-68, ADM-69, ADM-70
 *
 * Run with:
 *   npm test -- admin-nav-rbac
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AdminNav } from "@/components/layout/AdminNav";
import {
  MOCK_DEVELOPER,
  MOCK_PRODUCT_ADMIN,
  MOCK_SUPER_ADMIN,
  ADMIN_NAV_STRINGS,
} from "../e2e/data/admin-nav-rbac";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/admin/dashboard"),
}));

const mockUseAdmin = vi.fn();
vi.mock("@/lib/hooks/useAdmin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useAdmin")>();
  return { ...actual, useAdmin: vi.fn(() => mockUseAdmin()) };
});

// Stub localStorage for the sign-out test
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Stub window.location.href assignment
const locationMock = { href: "" };
Object.defineProperty(window, "location", { value: locationMock, writable: true });

// ---------------------------------------------------------------------------
// ADM-66 — developer role hides Feedback in nav
// ---------------------------------------------------------------------------

describe("ADM-66 — developer role hides Feedback in nav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
  });

  it("does NOT show Feedback nav item for developer", () => {
    render(<AdminNav />);
    expect(screen.queryByRole("link", { name: ADMIN_NAV_STRINGS.feedback })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-67 — developer role hides Audit Log in nav
// ---------------------------------------------------------------------------

describe("ADM-67 — developer role hides Audit Log in nav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
  });

  it("does NOT show Audit Log nav item for developer", () => {
    render(<AdminNav />);
    expect(screen.queryByRole("link", { name: ADMIN_NAV_STRINGS.auditLog })).toBeNull();
  });

  it("still shows Dashboard nav item for developer", () => {
    render(<AdminNav />);
    expect(
      screen.getByRole("link", { name: ADMIN_NAV_STRINGS.dashboard }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-68 — super_admin sees all nav items
// ---------------------------------------------------------------------------

describe("ADM-68 — super_admin sees all nav items", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_SUPER_ADMIN);
  });

  it("shows Feedback nav item for super_admin", () => {
    render(<AdminNav />);
    expect(
      screen.getByRole("link", { name: ADMIN_NAV_STRINGS.feedback }),
    ).toBeInTheDocument();
  });

  it("shows Audit Log nav item for super_admin", () => {
    render(<AdminNav />);
    expect(
      screen.getByRole("link", { name: ADMIN_NAV_STRINGS.auditLog }),
    ).toBeInTheDocument();
  });

  it("shows all 7 nav links for super_admin", () => {
    render(<AdminNav />);
    const navLinks = screen
      .getAllByRole("link")
      .filter((el) => el.getAttribute("href")?.startsWith("/admin/"));
    expect(navLinks.length).toBeGreaterThanOrEqual(7);
  });
});

// ---------------------------------------------------------------------------
// ADM-69 — product_admin sees Feedback and Audit Log
// ---------------------------------------------------------------------------

describe("ADM-69 — product_admin sees Feedback and Audit Log", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
  });

  it("shows Feedback nav item for product_admin", () => {
    render(<AdminNav />);
    expect(
      screen.getByRole("link", { name: ADMIN_NAV_STRINGS.feedback }),
    ).toBeInTheDocument();
  });

  it("shows Audit Log nav item for product_admin", () => {
    render(<AdminNav />);
    expect(
      screen.getByRole("link", { name: ADMIN_NAV_STRINGS.auditLog }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-70 — Sign out clears token and redirects
// ---------------------------------------------------------------------------

describe("ADM-70 — Sign out clears token", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
  });

  it("renders the Sign out button", () => {
    render(<AdminNav />);
    expect(screen.getByRole("button", { name: /Sign out/i })).toBeInTheDocument();
  });

  it("removes sb_admin_token from localStorage on sign out", () => {
    localStorageMock.setItem("sb_admin_token", "some-token");
    render(<AdminNav />);
    screen.getByRole("button", { name: /Sign out/i }).click();
    expect(localStorageMock.getItem("sb_admin_token")).toBeNull();
  });

  it("redirects to /admin/login on sign out", () => {
    localStorageMock.setItem("sb_admin_token", "some-token");
    render(<AdminNav />);
    screen.getByRole("button", { name: /Sign out/i }).click();
    expect(locationMock.href).toBe("/admin/login");
  });
});
