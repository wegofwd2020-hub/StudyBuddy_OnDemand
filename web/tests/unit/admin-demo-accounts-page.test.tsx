/**
 * Unit tests for Demo Accounts admin page (`/admin/demo-accounts`)
 * Covers TC-IDs: ADM-60, ADM-61, ADM-62, ADM-63, ADM-64, ADM-65
 *
 * Run with:
 *   npm test -- admin-demo-accounts-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminDemoAccountsPage from "@/app/(admin)/admin/demo-accounts/page";
import {
  MOCK_PRODUCT_ADMIN,
  MOCK_DEVELOPER,
  MOCK_DEMO_LIST,
  MOCK_DEMO_LIST_PAGE1,
  MOCK_EMPTY_LIST,
  MOCK_ACTIVE_ITEM,
  MOCK_PENDING_ITEM,
  DEMO_ACCOUNTS_STRINGS,
} from "../e2e/data/admin-demo-accounts-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAdmin = vi.fn();
vi.mock("@/lib/hooks/useAdmin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks/useAdmin")>();
  return { ...actual, useAdmin: vi.fn(() => mockUseAdmin()) };
});

const mockUseQuery = vi.fn();
const mockInvalidateQueries = vi.fn();
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((opts) => mockUseQuery(opts)),
    useQueryClient: vi.fn(() => ({ invalidateQueries: mockInvalidateQueries })),
  };
});

const mockGetDemoAccounts = vi.fn();
const mockExtendDemoAccount = vi.fn();
const mockRevokeDemoAccount = vi.fn();
const mockAdminResendDemoVerification = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    getDemoAccounts: (...args: unknown[]) => mockGetDemoAccounts(...args),
    extendDemoAccount: (...args: unknown[]) => mockExtendDemoAccount(...args),
    revokeDemoAccount: (...args: unknown[]) => mockRevokeDemoAccount(...args),
    adminResendDemoVerification: (...args: unknown[]) =>
      mockAdminResendDemoVerification(...args),
  };
});

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from "sonner";

// ---------------------------------------------------------------------------
// ADM-60 — Page renders for product_admin
// ---------------------------------------------------------------------------

describe("ADM-60 — Demo accounts page renders for product_admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
  });

  it("renders the page heading", () => {
    render(<AdminDemoAccountsPage />);
    expect(
      screen.getByRole("heading", { name: DEMO_ACCOUNTS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders rows for each demo account item", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByText(MOCK_ACTIVE_ITEM.email)).toBeInTheDocument();
    expect(screen.getByText(MOCK_PENDING_ITEM.email)).toBeInTheDocument();
  });

  it("renders status badge for active item", () => {
    render(<AdminDemoAccountsPage />);
    // { selector: 'span' } narrows to the badge — the filter tab is a <button>
    expect(screen.getByText("Active", { selector: "span" })).toBeInTheDocument();
  });

  it("renders status badge for pending item", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByText("Pending", { selector: "span" })).toBeInTheDocument();
  });

  it("renders total record count", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByText(/3 record/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-61 — Access denied for developer
// ---------------------------------------------------------------------------

describe("ADM-61 — Access denied for developer role", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_DEVELOPER);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
  });

  it("shows 'Access denied' message", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByText(DEMO_ACCOUNTS_STRINGS.accessDenied)).toBeInTheDocument();
  });

  it("does not render email rows for developer", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.queryByText(MOCK_ACTIVE_ITEM.email)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-62 — Row actions visibility
// ---------------------------------------------------------------------------

describe("ADM-62 — Row action button visibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
  });

  it("shows Extend and Revoke buttons for active (verified) accounts", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByTitle("Extend demo access")).toBeInTheDocument();
    expect(screen.getByTitle("Revoke demo access")).toBeInTheDocument();
  });

  it("shows Resend button for pending items with verification_pending=true", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByTitle("Resend verification email")).toBeInTheDocument();
  });

  it("does not show Extend/Revoke for pending (no account_id) items", () => {
    render(<AdminDemoAccountsPage />);
    // Only 1 active item → exactly 1 Extend button
    expect(screen.getAllByTitle("Extend demo access")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// ADM-63 — Extend modal flow
// ---------------------------------------------------------------------------

describe("ADM-63 — Extend demo modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
    mockExtendDemoAccount.mockResolvedValue({
      account_id: MOCK_ACTIVE_ITEM.account_id,
      expires_at: new Date().toISOString(),
      extended_at: new Date().toISOString(),
    });
  });

  it("opens extend modal on Extend button click", () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Extend demo access"));
    expect(screen.getByText("Extend demo")).toBeInTheDocument();
  });

  it("closes modal on Cancel click", () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Extend demo access"));
    fireEvent.click(screen.getByRole("button", { name: DEMO_ACCOUNTS_STRINGS.cancelBtn }));
    expect(screen.queryByText("Extend demo")).toBeNull();
  });

  it("calls extendDemoAccount with correct account_id and hours", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Extend demo access"));
    // Modal submit button is the last "Extend" button (row btn + modal btn)
    const extendBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.extendBtn });
    fireEvent.click(extendBtns[extendBtns.length - 1]);
    await waitFor(() =>
      expect(mockExtendDemoAccount).toHaveBeenCalledWith(MOCK_ACTIVE_ITEM.account_id, 24),
    );
  });

  it("shows success toast after successful extend", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Extend demo access"));
    const extendBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.extendBtn });
    fireEvent.click(extendBtns[extendBtns.length - 1]);
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("shows error toast when extend fails", async () => {
    mockExtendDemoAccount.mockRejectedValue(new Error("network error"));
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Extend demo access"));
    const extendBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.extendBtn });
    fireEvent.click(extendBtns[extendBtns.length - 1]);
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});

// ---------------------------------------------------------------------------
// ADM-64 — Revoke modal flow
// ---------------------------------------------------------------------------

describe("ADM-64 — Revoke demo modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
    mockRevokeDemoAccount.mockResolvedValue({
      email: MOCK_ACTIVE_ITEM.email,
      message: "revoked",
    });
  });

  it("opens revoke confirmation modal on Revoke button click", () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Revoke demo access"));
    expect(screen.getByText("Revoke demo?")).toBeInTheDocument();
  });

  it("closes revoke modal on Cancel click", () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Revoke demo access"));
    fireEvent.click(screen.getByRole("button", { name: DEMO_ACCOUNTS_STRINGS.cancelBtn }));
    expect(screen.queryByText("Revoke demo?")).toBeNull();
  });

  it("calls revokeDemoAccount with correct account_id on confirm", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Revoke demo access"));
    // Modal has two "Revoke" buttons (row + modal confirm) — pick the last
    const revokeBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.confirmRevokeBtn });
    fireEvent.click(revokeBtns[revokeBtns.length - 1]);
    await waitFor(() =>
      expect(mockRevokeDemoAccount).toHaveBeenCalledWith(MOCK_ACTIVE_ITEM.account_id),
    );
  });

  it("shows success toast after successful revoke", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Revoke demo access"));
    const revokeBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.confirmRevokeBtn });
    fireEvent.click(revokeBtns[revokeBtns.length - 1]);
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("invalidates query after revoke", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Revoke demo access"));
    const revokeBtns = screen.getAllByRole("button", { name: DEMO_ACCOUNTS_STRINGS.confirmRevokeBtn });
    fireEvent.click(revokeBtns[revokeBtns.length - 1]);
    await waitFor(() => expect(mockInvalidateQueries).toHaveBeenCalled());
  });
});

// ---------------------------------------------------------------------------
// ADM-65 — Resend verification and pagination
// ---------------------------------------------------------------------------

describe("ADM-65 — Resend verification", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST, isLoading: false });
    mockAdminResendDemoVerification.mockResolvedValue({ email: MOCK_PENDING_ITEM.email });
  });

  it("calls adminResendDemoVerification with correct request_id", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Resend verification email"));
    await waitFor(() =>
      expect(mockAdminResendDemoVerification).toHaveBeenCalledWith(MOCK_PENDING_ITEM.request_id),
    );
  });

  it("shows success toast after successful resend", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Resend verification email"));
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("shows error toast when resend fails", async () => {
    mockAdminResendDemoVerification.mockRejectedValue(new Error("smtp error"));
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByTitle("Resend verification email"));
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});

describe("ADM-65 — Pagination", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_DEMO_LIST_PAGE1, isLoading: false });
  });

  it("Previous button is disabled on page 1", () => {
    render(<AdminDemoAccountsPage />);
    expect(
      screen.getByRole("button", { name: DEMO_ACCOUNTS_STRINGS.prevBtn }),
    ).toBeDisabled();
  });

  it("Next button is enabled when a full page of results is returned", () => {
    render(<AdminDemoAccountsPage />);
    expect(
      screen.getByRole("button", { name: DEMO_ACCOUNTS_STRINGS.nextBtn }),
    ).not.toBeDisabled();
  });

  it("clicking Next triggers query with page=2", async () => {
    render(<AdminDemoAccountsPage />);
    fireEvent.click(screen.getByRole("button", { name: DEMO_ACCOUNTS_STRINGS.nextBtn }));
    await waitFor(() => {
      const lastCall = mockUseQuery.mock.calls.at(-1)?.[0];
      expect(lastCall?.queryKey).toContain(2);
    });
  });
});

describe("ADM-65 — Empty state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAdmin.mockReturnValue(MOCK_PRODUCT_ADMIN);
    mockUseQuery.mockReturnValue({ data: MOCK_EMPTY_LIST, isLoading: false });
  });

  it("shows empty state message when no results", () => {
    render(<AdminDemoAccountsPage />);
    expect(screen.getByText(DEMO_ACCOUNTS_STRINGS.emptyMsg)).toBeInTheDocument();
  });
});
