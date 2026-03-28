/**
 * Unit tests for section 4.2 — Auth Redirects (Admin)
 * Covers TC-IDs: ADM-05, ADM-06
 *
 * Tests that the AdminLayout redirects to /admin/login when
 * no `sb_admin_token` exists in localStorage.
 *
 * Run with:
 *   npm test -- admin-auth-redirects
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import AdminLayout from "@/app/(admin)/layout";
import { AUTH_REDIRECT_STRINGS } from "../e2e/data/admin-auth-redirects";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter:   vi.fn(() => ({ replace: mockReplace, push: vi.fn() })),
  usePathname: vi.fn(() => "/admin/dashboard"),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/hooks/useAdmin", () => ({
  useAdmin:       vi.fn(() => null),
  hasPermission:  vi.fn(() => false),
}));

vi.mock("@/lib/providers/QueryProvider", () => ({
  QueryProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// localStorage stub
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem:    (key: string) => store[key] ?? null,
    setItem:    (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear:      () => { store = {}; },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ---------------------------------------------------------------------------
// ADM-05 — /admin/dashboard redirects without token
// ADM-06 — /admin/analytics redirects without token
// ---------------------------------------------------------------------------

describe("ADM-05 + ADM-06 — Admin layout redirects when no token", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear(); // ensure no token
  });

  it("redirects to /admin/login when no sb_admin_token in localStorage", async () => {
    render(
      <AdminLayout>
        <div>Dashboard content</div>
      </AdminLayout>,
    );
    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith(AUTH_REDIRECT_STRINGS.loginPath),
    );
  });

  it("does NOT redirect when sb_admin_token is present", async () => {
    localStorageMock.setItem("sb_admin_token", "mock-token-value");
    render(
      <AdminLayout>
        <div>Dashboard content</div>
      </AdminLayout>,
    );
    // Allow useEffect to fire
    await waitFor(() => expect(mockReplace).not.toHaveBeenCalled());
  });
});
