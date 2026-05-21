/**
 * Unit test for /demo/login.
 *
 * The demo login form was folded into the unified /signin page (universal
 * login). /demo/login is now a redirect stub kept alive for demo credential
 * emails issued before the cutover. The former login-form tests are obsolete;
 * this verifies the redirect.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import DemoLoginRedirect from "@/app/(public)/demo/login/page";

const mockRedirect = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (path: string) => mockRedirect(path),
}));

describe("DemoLoginRedirect — folded into /signin", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects to /signin", () => {
    render(<DemoLoginRedirect />);
    expect(mockRedirect).toHaveBeenCalledWith("/signin");
  });
});
