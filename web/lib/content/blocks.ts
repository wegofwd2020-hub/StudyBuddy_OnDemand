/**
 * Epic 12 — Structured Content Block Taxonomy (v0, Layers 1–3).
 *
 * TypeScript mirror of pipeline/schemas/content_block.v0.schema.json and
 * pipeline/content_blocks.py. Hand-authored; the Python drift test (see
 * backend/tests/test_content_blocks.py) guards against JSON Schema ↔
 * Pydantic drift, and we follow the same shape here by construction.
 *
 * Do not add runtime validation to this file — validation lives on the
 * pipeline side. This module is types-only and the one `isBlock<T>` guard.
 */

export type BlockId = string;

/**
 * Markdown string restricted to *inline* constructs (bold, italic, code,
 * links, $...$ math). Block-level constructs (headings, tables, code
 * fences, triple-newlines) are forbidden; enforced at emit time by the
 * pipeline's second-pass validator.
 */
export type InlineMarkdown = string;

export const SCHEMA_VERSION = "1.0" as const;
export type SchemaVersion = `${number}.${number}`;

interface BlockBase<TType extends string, TData> {
  type: TType;
  id: BlockId;
  data: TData;
}

// ── Flow (7) ───────────────────────────────────────────────────────────────

export type HeadingBlock = BlockBase<
  "Heading",
  { level: 2 | 3 | 4; text: string }
>;

export type ParagraphBlock = BlockBase<
  "Paragraph",
  { markdown: InlineMarkdown }
>;

export type ListBlock = BlockBase<
  "List",
  { style: "bullet" | "ordered"; items: InlineMarkdown[] }
>;

export type CalloutBlock = BlockBase<
  "Callout",
  {
    variant: "info" | "warning" | "tip" | "note";
    title?: string;
    body: InlineMarkdown;
  }
>;

export type FigureBlock = BlockBase<
  "Figure",
  {
    src: string;
    alt: string;
    caption?: InlineMarkdown;
    attribution?: string;
    license?: string;
  }
>;

export type QuoteBlock = BlockBase<
  "Quote",
  { markdown: InlineMarkdown; attribution?: string; source?: string }
>;

export type CodeBlock = BlockBase<
  "Code",
  { language?: string; source: string }
>;

// ── Pedagogical (6) ────────────────────────────────────────────────────────

export type DefinitionBlock = BlockBase<
  "Definition",
  { term: string; body: InlineMarkdown }
>;

export type KeyConceptBlock = BlockBase<
  "KeyConcept",
  { title: string; body: InlineMarkdown }
>;

export interface WorkedExampleStep {
  label?: string;
  body: InlineMarkdown;
}

export type WorkedExampleBlock = BlockBase<
  "WorkedExample",
  {
    title: string;
    prompt: InlineMarkdown;
    steps: WorkedExampleStep[];
    answer?: InlineMarkdown;
  }
>;

export type TryThisBlock = BlockBase<
  "TryThis",
  { prompt: InlineMarkdown; hint?: InlineMarkdown; answer?: InlineMarkdown }
>;

export type SummaryBlock = BlockBase<"Summary", { points: InlineMarkdown[] }>;

export type CrossReferenceBlock = BlockBase<
  "CrossReference",
  { target_id: BlockId; label?: InlineMarkdown }
>;

// ── Structural (3) ────────────────────────────────────────────────────────

export type FormulaBlock = BlockBase<
  "Formula",
  { latex: string; label?: string; block?: boolean }
>;

export type DataTableBlock = BlockBase<
  "DataTable",
  {
    caption?: string;
    headers: string[];
    align?: Array<"left" | "center" | "right">;
    rows: InlineMarkdown[][];
    tabular_numbers?: boolean;
  }
>;

export type DiagramBlock = BlockBase<
  "Diagram",
  { format: "mermaid" | "svg"; source: string; alt: string }
>;

// ── Media reference (1, T-6) ───────────────────────────────────────────────

export type MediaPlaceholderBlock = BlockBase<
  "MediaPlaceholder",
  {
    media_type: "video" | "audio";
    url: string;
    caption: string;
    attribution?: string;
  }
>;

// ── Discriminated union + document ─────────────────────────────────────────

export type ContentBlock =
  | HeadingBlock
  | ParagraphBlock
  | ListBlock
  | CalloutBlock
  | FigureBlock
  | QuoteBlock
  | CodeBlock
  | DefinitionBlock
  | KeyConceptBlock
  | WorkedExampleBlock
  | TryThisBlock
  | SummaryBlock
  | CrossReferenceBlock
  | FormulaBlock
  | DataTableBlock
  | DiagramBlock
  | MediaPlaceholderBlock;

export type ContentBlockType = ContentBlock["type"];

export interface ContentDocument {
  schema_version: SchemaVersion;
  blocks: ContentBlock[];
}

/**
 * Type guard that narrows a ContentBlock to the specific variant matching
 * `type`. Lets callers write `if (isBlock(b, 'Figure')) { b.data.src ... }`
 * without a cast.
 */
export function isBlock<T extends ContentBlockType>(
  block: ContentBlock,
  type: T,
): block is Extract<ContentBlock, { type: T }> {
  return block.type === type;
}

/**
 * Exhaustive list of block types in the same order as the Python
 * definition — used by tests and the block renderer to guarantee parity.
 */
export const ALL_BLOCK_TYPES: readonly ContentBlockType[] = [
  "Heading",
  "Paragraph",
  "List",
  "Callout",
  "Figure",
  "Quote",
  "Code",
  "Definition",
  "KeyConcept",
  "WorkedExample",
  "TryThis",
  "Summary",
  "CrossReference",
  "Formula",
  "DataTable",
  "Diagram",
  "MediaPlaceholder",
] as const;
