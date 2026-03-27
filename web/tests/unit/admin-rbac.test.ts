import { describe, it, expect } from "vitest";
import { hasPermission, type AdminRole } from "@/lib/hooks/useAdmin";

// ---------------------------------------------------------------------------
// hasPermission — role rank checks
// ---------------------------------------------------------------------------

describe("hasPermission", () => {
  it("developer passes developer requirement", () => {
    expect(hasPermission("developer", "developer")).toBe(true);
  });

  it("developer fails product_admin requirement", () => {
    expect(hasPermission("developer", "product_admin")).toBe(false);
  });

  it("tester passes developer requirement", () => {
    expect(hasPermission("tester", "developer")).toBe(true);
  });

  it("tester fails product_admin requirement", () => {
    expect(hasPermission("tester", "product_admin")).toBe(false);
  });

  it("product_admin passes product_admin requirement", () => {
    expect(hasPermission("product_admin", "product_admin")).toBe(true);
  });

  it("product_admin fails super_admin requirement", () => {
    expect(hasPermission("product_admin", "super_admin")).toBe(false);
  });

  it("super_admin passes all requirements", () => {
    const roles: AdminRole[] = ["developer", "tester", "product_admin", "super_admin"];
    for (const r of roles) {
      expect(hasPermission("super_admin", r)).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// RBAC sidebar item filtering — pure logic
// ---------------------------------------------------------------------------

interface NavItem {
  label: string;
  minRole?: AdminRole;
}

function filterNavItems(items: NavItem[], role: AdminRole): NavItem[] {
  return items.filter((item) => !item.minRole || hasPermission(role, item.minRole));
}

const ITEMS: NavItem[] = [
  { label: "Dashboard" },
  { label: "Analytics" },
  { label: "Pipeline" },
  { label: "Content Review" },
  { label: "Feedback", minRole: "product_admin" },
  { label: "Audit Log", minRole: "product_admin" },
  { label: "Health" },
];

describe("AdminNav RBAC filtering", () => {
  it("developer sees items without minRole only", () => {
    const visible = filterNavItems(ITEMS, "developer");
    const labels = visible.map((i) => i.label);
    expect(labels).toContain("Dashboard");
    expect(labels).toContain("Pipeline");
    expect(labels).not.toContain("Feedback");
    expect(labels).not.toContain("Audit Log");
  });

  it("tester sees same items as developer", () => {
    const devVisible = filterNavItems(ITEMS, "developer").map((i) => i.label);
    const testerVisible = filterNavItems(ITEMS, "tester").map((i) => i.label);
    expect(testerVisible).toEqual(devVisible);
  });

  it("product_admin sees all items including Feedback and Audit Log", () => {
    const visible = filterNavItems(ITEMS, "product_admin");
    const labels = visible.map((i) => i.label);
    expect(labels).toContain("Feedback");
    expect(labels).toContain("Audit Log");
    expect(labels).toHaveLength(ITEMS.length);
  });

  it("super_admin sees all items", () => {
    const visible = filterNavItems(ITEMS, "super_admin");
    expect(visible).toHaveLength(ITEMS.length);
  });
});
