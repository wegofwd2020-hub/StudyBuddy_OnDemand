import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils/cn";

describe("cn utility", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("deduplicates Tailwind conflicting classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("filters falsy values", () => {
    expect(cn("foo", false && "bar", undefined, "baz")).toBe("foo baz");
  });
});
