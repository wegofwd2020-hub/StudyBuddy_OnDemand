import { describe, expect, it } from "vitest";
import { suggestEmailDomainFix } from "@/lib/utils/email-typo";

describe("suggestEmailDomainFix", () => {
  it("suggests the corrected domain and keeps the local part", () => {
    expect(suggestEmailDomainFix("venki.kt@gmal.com")).toBe("venki.kt@gmail.com");
  });

  it("matches the domain case-insensitively and keeps the local part's case", () => {
    expect(suggestEmailDomainFix("Venki@GMAL.COM")).toBe("Venki@gmail.com");
  });

  it("returns null for a domain that is already correct", () => {
    expect(suggestEmailDomainFix("venki@gmail.com")).toBeNull();
  });

  it("returns null for an unknown domain", () => {
    expect(suggestEmailDomainFix("venki@example.org")).toBeNull();
  });

  it("returns null when there is no local part or no @", () => {
    expect(suggestEmailDomainFix("@gmal.com")).toBeNull();
    expect(suggestEmailDomainFix("gmal.com")).toBeNull();
    expect(suggestEmailDomainFix("")).toBeNull();
  });
});
