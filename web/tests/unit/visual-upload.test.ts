/**
 * Upload form feedback (#618).
 *
 * Venki chose a file, pressed Upload, and nothing happened. The button was
 * disabled because the three ID fields were empty — but their placeholders look
 * exactly like real values, so the form appeared complete. An inert button with
 * no message is indistinguishable from a broken one, and that is how it was
 * reported.
 */

import { describe, expect, it } from "vitest";
import { describeMissingUploadFields } from "@/lib/school/visual-upload";

const FILE = { name: "diagram.png", size: 1024, type: "image/png" } as unknown as File;

const COMPLETE = {
  file: FILE,
  curriculum: "default-2026-g11-science",
  unit: "G11-PHYS-002",
  section: "s1",
};

describe("describeMissingUploadFields", () => {
  it("passes a fully completed form", () => {
    expect(describeMissingUploadFields(COMPLETE)).toBeNull();
  });

  it("names the exact fields left blank — the reported case", () => {
    // A file chosen, IDs untouched because the placeholders looked filled in.
    const msg = describeMissingUploadFields({
      file: FILE,
      curriculum: "",
      unit: "",
      section: "",
    });

    expect(msg).toContain("Curriculum ID");
    expect(msg).toContain("Unit ID");
    expect(msg).toContain("Section ID");
  });

  it("names only the field actually missing", () => {
    const msg = describeMissingUploadFields({ ...COMPLETE, unit: "" });

    expect(msg).toContain("Unit ID");
    expect(msg).not.toContain("Curriculum ID");
    expect(msg).not.toContain("Section ID");
  });

  it("asks for a file when only the file is missing", () => {
    const msg = describeMissingUploadFields({ ...COMPLETE, file: null });
    expect(msg).toBe("Choose a file to upload.");
  });

  it("distinguishes a malformed ID from a blank one", () => {
    const msg = describeMissingUploadFields({ ...COMPLETE, section: "!!!" });

    expect(msg).toContain("Section ID");
    expect(msg).toContain("not a valid ID");
    expect(msg).not.toContain("Fill in");
  });

  it("reports blanks and malformed values together without conflating them", () => {
    const msg = describeMissingUploadFields({
      ...COMPLETE,
      curriculum: "",
      section: "!!!",
    });

    expect(msg).toContain("Fill in Curriculum ID");
    expect(msg).toContain("Section ID");
    expect(msg).toContain("not a valid ID");
  });

  it("accepts the values the placeholders suggest, so the examples are honest", () => {
    // If a user typed the placeholder text verbatim it must actually work —
    // otherwise the example is a lie.
    expect(
      describeMissingUploadFields({
        file: FILE,
        curriculum: "default-2026-g11-science",
        unit: "G11-PHYS-002",
        section: "s1",
      }),
    ).toBeNull();
  });

  it("ignores surrounding whitespace rather than treating it as content", () => {
    const msg = describeMissingUploadFields({ ...COMPLETE, unit: "   " });
    expect(msg).toContain("Unit ID");
  });
});
