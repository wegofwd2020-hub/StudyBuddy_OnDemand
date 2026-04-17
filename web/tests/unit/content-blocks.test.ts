/**
 * Epic 12 T-1a — TypeScript content block types.
 *
 * Exercises the discriminated union, the `isBlock<T>` type guard, and the
 * `ALL_BLOCK_TYPES` parity list. Renderer-side tests land in T-1b with
 * the per-type React components.
 */

import { describe, it, expect } from "vitest";
import {
  ALL_BLOCK_TYPES,
  type ContentBlock,
  type ContentBlockType,
  type ContentDocument,
  type FigureBlock,
  type HeadingBlock,
  isBlock,
  SCHEMA_VERSION,
} from "@/lib/content/blocks";

describe("content block types — Epic 12 T-1a", () => {
  it("ALL_BLOCK_TYPES contains 17 entries", () => {
    expect(ALL_BLOCK_TYPES).toHaveLength(17);
  });

  it("ALL_BLOCK_TYPES has no duplicates", () => {
    const unique = new Set(ALL_BLOCK_TYPES);
    expect(unique.size).toBe(ALL_BLOCK_TYPES.length);
  });

  it("SCHEMA_VERSION is '1.0'", () => {
    expect(SCHEMA_VERSION).toBe("1.0");
  });

  it("isBlock narrows the union for Heading", () => {
    const block: ContentBlock = {
      type: "Heading",
      id: "heading-intro",
      data: { level: 2, text: "Intro" },
    };
    if (isBlock(block, "Heading")) {
      // TypeScript should narrow; accessing HeadingBlock-only fields proves it
      const asHeading: HeadingBlock = block;
      expect(asHeading.data.level).toBe(2);
      expect(asHeading.data.text).toBe("Intro");
    } else {
      throw new Error("expected Heading narrowing");
    }
  });

  it("isBlock narrows the union for Figure", () => {
    const block: ContentBlock = {
      type: "Figure",
      id: "b-0001",
      data: {
        src: "curricula/x/u/media/a.png",
        alt: "A labelled diagram",
      },
    };
    if (isBlock(block, "Figure")) {
      const asFigure: FigureBlock = block;
      expect(asFigure.data.src).toBe("curricula/x/u/media/a.png");
      expect(asFigure.data.alt).toBe("A labelled diagram");
    } else {
      throw new Error("expected Figure narrowing");
    }
  });

  it("isBlock returns false for a mismatched type", () => {
    const block: ContentBlock = {
      type: "Paragraph",
      id: "b-0001",
      data: { markdown: "Hello" },
    };
    expect(isBlock(block, "Heading")).toBe(false);
    expect(isBlock(block, "Paragraph")).toBe(true);
  });

  it("ContentDocument composes with valid blocks", () => {
    const doc: ContentDocument = {
      schema_version: "1.0",
      blocks: [
        { type: "Heading", id: "h", data: { level: 2, text: "Intro" } },
        { type: "Paragraph", id: "b-0001", data: { markdown: "Hello **world**." } },
      ],
    };
    expect(doc.blocks).toHaveLength(2);
    expect(doc.blocks[0].type).toBe("Heading");
  });

  it("exhaustive switch on ContentBlockType compiles", () => {
    // This is primarily a compile-time check. The function below would
    // fail to type-check if a new block type were added without updating
    // the switch (TS exhaustiveness via `never` on default).
    function label(block: ContentBlock): string {
      switch (block.type) {
        case "Heading":
          return "h";
        case "Paragraph":
          return "p";
        case "List":
          return "list";
        case "Callout":
          return "callout";
        case "Figure":
          return "figure";
        case "Quote":
          return "quote";
        case "Code":
          return "code";
        case "Definition":
          return "def";
        case "KeyConcept":
          return "concept";
        case "WorkedExample":
          return "worked";
        case "TryThis":
          return "try";
        case "Summary":
          return "summary";
        case "CrossReference":
          return "xref";
        case "Formula":
          return "formula";
        case "DataTable":
          return "table";
        case "Diagram":
          return "diagram";
        case "MediaPlaceholder":
          return "media";
        default: {
          const _exhaustive: never = block;
          return _exhaustive;
        }
      }
    }

    const h: ContentBlock = { type: "Heading", id: "h", data: { level: 2, text: "x" } };
    expect(label(h)).toBe("h");
  });

  it("narrowed types enforce data shape at compile time", () => {
    // Construct an array of every block type to exercise each variant.
    const blocks: ContentBlock[] = [
      { type: "Heading", id: "h1", data: { level: 2, text: "x" } },
      { type: "Paragraph", id: "b-0001", data: { markdown: "x" } },
      { type: "List", id: "b-0002", data: { style: "bullet", items: ["a"] } },
      {
        type: "Callout",
        id: "b-0003",
        data: { variant: "info", body: "note" },
      },
      {
        type: "Figure",
        id: "b-0004",
        data: { src: "x", alt: "valid alt" },
      },
      { type: "Quote", id: "b-0005", data: { markdown: "cite" } },
      { type: "Code", id: "b-0006", data: { source: "x=1" } },
      { type: "Definition", id: "def-x", data: { term: "X", body: "body" } },
      { type: "KeyConcept", id: "concept-x", data: { title: "X", body: "b" } },
      {
        type: "WorkedExample",
        id: "b-0007",
        data: { title: "x", prompt: "p", steps: [{ body: "s" }] },
      },
      { type: "TryThis", id: "b-0008", data: { prompt: "p" } },
      { type: "Summary", id: "b-0009", data: { points: ["p"] } },
      {
        type: "CrossReference",
        id: "b-0010",
        data: { target_id: "def-x" },
      },
      { type: "Formula", id: "b-0011", data: { latex: "x=1" } },
      {
        type: "DataTable",
        id: "b-0012",
        data: { headers: ["a"], rows: [["1"]] },
      },
      {
        type: "Diagram",
        id: "b-0013",
        data: { format: "mermaid", source: "x", alt: "flow" },
      },
      {
        type: "MediaPlaceholder",
        id: "b-0014",
        data: {
          media_type: "video",
          url: "https://example.com/v",
          caption: "cap",
        },
      },
    ];
    expect(blocks.map((b) => b.type as ContentBlockType)).toEqual([
      ...ALL_BLOCK_TYPES,
    ]);
  });
});
