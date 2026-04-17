"""
pipeline/content_blocks.py

Epic 12 — Structured Content Block Taxonomy (v0, Layers 1–3).

Pydantic v2 models mirroring pipeline/schemas/content_block.v0.schema.json.
Both validators are hand-authored and kept in sync by the drift test in
tests/test_content_blocks.py (per Q7(a) of the epic).

A ContentDocument is the top-level shape emitted by the pipeline once
T-2 lands; a renderer dispatches on block.type. See the epic file for
the semantic model behind each block type.

Public API:
    load_schema()             -> dict       JSON Schema as a dict
    validate_document(payload) -> ContentDocument
                                            Runs JSON Schema + Pydantic +
                                            second-pass InlineMarkdown check;
                                            raises ContentBlockValidationError
                                            on any failure.

    make_positional_id(n)      -> str       'b-0001' … for prose blocks
    make_slug_id(prefix, text) -> str       'def-balance-sheet' … for anchors
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias, Union

import jsonschema
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
)

SCHEMA_PATH = Path(__file__).parent / "schemas" / "content_block.v0.schema.json"
SCHEMA_VERSION = "1.0"


class ContentBlockValidationError(Exception):
    """Raised when a ContentDocument fails schema, Pydantic, or inline-markdown validation."""


# ── Shared field types ────────────────────────────────────────────────────────

BlockId: TypeAlias = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$"),
]

InlineMarkdown: TypeAlias = Annotated[
    str,
    StringConstraints(min_length=1, max_length=4000),
]


# Block-level markdown constructs forbidden inside an InlineMarkdown string.
# Enforced in _assert_inline_markdown() after JSON Schema + Pydantic pass.
_BLOCK_MARKDOWN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|\n)#{1,6}\s"), "ATX heading (# ...)"),
    (re.compile(r"```"), "fenced code block (```)"),
    (re.compile(r"(^|\n)\s*\|.+\|\s*\n\s*\|[\s:|-]+\|"), "GFM table"),
    (re.compile(r"\n{3,}"), "triple newline (paragraph break)"),
    (re.compile(r"(^|\n)\s*>\s"), "blockquote (> ...)"),
    (re.compile(r"(^|\n)\s*[-*+]\s{2,}"), "block-level list item"),
]


def _assert_inline_markdown(value: str, path: str) -> None:
    for pattern, label in _BLOCK_MARKDOWN_PATTERNS:
        if pattern.search(value):
            raise ContentBlockValidationError(
                f"block-level markdown construct not allowed in {path}: {label}"
            )


# ── Base block ────────────────────────────────────────────────────────────────


class _BlockData(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: BlockId


# ── Flow (7) ──────────────────────────────────────────────────────────────────


class HeadingData(_BlockData):
    level: int = Field(ge=2, le=4)
    text: Annotated[str, StringConstraints(min_length=1, max_length=240)]


class Heading(_Block):
    type: Literal["Heading"] = "Heading"
    data: HeadingData


class ParagraphData(_BlockData):
    markdown: InlineMarkdown


class Paragraph(_Block):
    type: Literal["Paragraph"] = "Paragraph"
    data: ParagraphData


class ListData(_BlockData):
    style: Literal["bullet", "ordered"]
    items: list[InlineMarkdown] = Field(min_length=1, max_length=50)


class List_(_Block):
    type: Literal["List"] = "List"
    data: ListData


class CalloutData(_BlockData):
    variant: Literal["info", "warning", "tip", "note"]
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None
    body: InlineMarkdown


class Callout(_Block):
    type: Literal["Callout"] = "Callout"
    data: CalloutData


class FigureData(_BlockData):
    src: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    alt: Annotated[str, StringConstraints(min_length=3, max_length=480)]
    caption: InlineMarkdown | None = None
    attribution: Annotated[str, StringConstraints(max_length=240)] | None = None
    license: Annotated[str, StringConstraints(max_length=120)] | None = None


class Figure(_Block):
    type: Literal["Figure"] = "Figure"
    data: FigureData


class QuoteData(_BlockData):
    markdown: InlineMarkdown
    attribution: Annotated[str, StringConstraints(max_length=240)] | None = None
    source: Annotated[str, StringConstraints(max_length=240)] | None = None


class Quote(_Block):
    type: Literal["Quote"] = "Quote"
    data: QuoteData


class CodeData(_BlockData):
    language: Annotated[str, StringConstraints(max_length=40)] | None = None
    source: Annotated[str, StringConstraints(min_length=1, max_length=8000)]


class Code(_Block):
    type: Literal["Code"] = "Code"
    data: CodeData


# ── Pedagogical (6) ──────────────────────────────────────────────────────────


class DefinitionData(_BlockData):
    term: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    body: InlineMarkdown


class Definition(_Block):
    type: Literal["Definition"] = "Definition"
    data: DefinitionData


class KeyConceptData(_BlockData):
    title: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    body: InlineMarkdown


class KeyConcept(_Block):
    type: Literal["KeyConcept"] = "KeyConcept"
    data: KeyConceptData


class WorkedExampleStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Annotated[str, StringConstraints(min_length=1, max_length=80)] | None = None
    body: InlineMarkdown


class WorkedExampleData(_BlockData):
    title: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    prompt: InlineMarkdown
    steps: list[WorkedExampleStep] = Field(min_length=1, max_length=40)
    answer: InlineMarkdown | None = None


class WorkedExample(_Block):
    type: Literal["WorkedExample"] = "WorkedExample"
    data: WorkedExampleData


class TryThisData(_BlockData):
    prompt: InlineMarkdown
    hint: InlineMarkdown | None = None
    answer: InlineMarkdown | None = None


class TryThis(_Block):
    type: Literal["TryThis"] = "TryThis"
    data: TryThisData


class SummaryData(_BlockData):
    points: list[InlineMarkdown] = Field(min_length=1, max_length=20)


class Summary(_Block):
    type: Literal["Summary"] = "Summary"
    data: SummaryData


class CrossReferenceData(_BlockData):
    target_id: BlockId
    label: InlineMarkdown | None = None


class CrossReference(_Block):
    type: Literal["CrossReference"] = "CrossReference"
    data: CrossReferenceData


# ── Structural (3) ───────────────────────────────────────────────────────────


class FormulaData(_BlockData):
    latex: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    label: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None
    block: bool | None = None


class Formula(_Block):
    type: Literal["Formula"] = "Formula"
    data: FormulaData


class DataTableData(_BlockData):
    caption: Annotated[str, StringConstraints(min_length=1, max_length=240)] | None = None
    headers: list[Annotated[str, StringConstraints(min_length=1, max_length=120)]] = Field(
        min_length=1, max_length=24
    )
    align: list[Literal["left", "center", "right"]] | None = None
    rows: list[list[InlineMarkdown]] = Field(min_length=1, max_length=200)
    tabular_numbers: bool | None = None


class DataTable(_Block):
    type: Literal["DataTable"] = "DataTable"
    data: DataTableData


class DiagramData(_BlockData):
    format: Literal["mermaid", "svg"]
    source: Annotated[str, StringConstraints(min_length=1, max_length=16000)]
    alt: Annotated[str, StringConstraints(min_length=3, max_length=480)]


class Diagram(_Block):
    type: Literal["Diagram"] = "Diagram"
    data: DiagramData


# ── Media reference (1, T-6) ─────────────────────────────────────────────────


class MediaPlaceholderData(_BlockData):
    media_type: Literal["video", "audio"]
    url: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    caption: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    attribution: Annotated[str, StringConstraints(max_length=240)] | None = None


class MediaPlaceholder(_Block):
    type: Literal["MediaPlaceholder"] = "MediaPlaceholder"
    data: MediaPlaceholderData


# ── Discriminated union + document ───────────────────────────────────────────


ContentBlock = Annotated[
    Union[
        Heading,
        Paragraph,
        List_,
        Callout,
        Figure,
        Quote,
        Code,
        Definition,
        KeyConcept,
        WorkedExample,
        TryThis,
        Summary,
        CrossReference,
        Formula,
        DataTable,
        Diagram,
        MediaPlaceholder,
    ],
    Field(discriminator="type"),
]


class ContentDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+$")] = SCHEMA_VERSION
    blocks: list[ContentBlock] = Field(min_length=1)


_DOCUMENT_ADAPTER = TypeAdapter(ContentDocument)


# ── Schema loading ───────────────────────────────────────────────────────────


_SCHEMA_CACHE: dict | None = None


def load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with SCHEMA_PATH.open() as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


# ── Inline-markdown second-pass walker ───────────────────────────────────────


# Fields that hold InlineMarkdown (by block.type, field path inside data).
# A path segment of '[]' means "every element of this list".
_INLINE_FIELDS: dict[str, list[tuple[str, ...]]] = {
    "Paragraph": [("markdown",)],
    "List": [("items", "[]")],
    "Callout": [("body",)],
    "Figure": [("caption",)],
    "Quote": [("markdown",)],
    "Definition": [("body",)],
    "KeyConcept": [("body",)],
    "WorkedExample": [("prompt",), ("steps", "[]", "body"), ("answer",)],
    "TryThis": [("prompt",), ("hint",), ("answer",)],
    "Summary": [("points", "[]")],
    "CrossReference": [("label",)],
    "DataTable": [("rows", "[]", "[]")],
}


def _walk_inline(value: Any, path: tuple[str, ...], breadcrumb: str) -> None:
    if not path:
        if isinstance(value, str):
            _assert_inline_markdown(value, breadcrumb)
        return
    head, *rest = path
    rest_t = tuple(rest)
    if head == "[]":
        if not isinstance(value, list):
            return
        for i, item in enumerate(value):
            _walk_inline(item, rest_t, f"{breadcrumb}[{i}]")
        return
    if value is None:
        return
    if isinstance(value, dict):
        if head not in value:
            return
        _walk_inline(value[head], rest_t, f"{breadcrumb}.{head}")


def _check_inline_markdown(block: dict) -> None:
    btype = block.get("type")
    paths = _INLINE_FIELDS.get(btype or "", [])
    data = block.get("data") or {}
    for path in paths:
        _walk_inline(data, path, f"blocks[type={btype}].data")


# ── Public validator ─────────────────────────────────────────────────────────


def validate_document(payload: Any) -> ContentDocument:
    """Validate a ContentDocument against JSON Schema + Pydantic + inline-markdown rules.

    Raises ContentBlockValidationError on any failure. Returns the parsed
    ContentDocument on success.
    """
    schema = load_schema()
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ContentBlockValidationError(f"json-schema: {exc.message}") from exc

    try:
        document = _DOCUMENT_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise ContentBlockValidationError(f"pydantic: {exc}") from exc

    # Pydantic has validated; now walk raw payload for block-level markdown
    # inside InlineMarkdown fields. Using the raw dict avoids re-serialising.
    for block in payload["blocks"]:
        _check_inline_markdown(block)

    return document


# ── Stable-ID helpers (used later by T-2) ────────────────────────────────────


def make_positional_id(n: int) -> str:
    """Return 'b-NNNN' for prose-block positional IDs. n is 1-based."""
    if n < 1:
        raise ValueError("positional id must be 1-based")
    return f"b-{n:04d}"


_SLUG_NON_ALPHA = re.compile(r"[^a-z0-9]+")


def make_slug_id(prefix: str, text: str, max_total_len: int = 64) -> str:
    """Return '<prefix>-<slug>' for anchorable blocks (Heading/Definition/KeyConcept).

    Collapses non-alphanumerics to '-', lowercases, trims. Keeps the output
    within BlockId's 64-char pattern. Prefix is inserted verbatim (no
    re-slugging); caller should pass 'def' / 'heading' / 'concept' etc.
    """
    slug = _SLUG_NON_ALPHA.sub("-", text.lower()).strip("-")
    if not slug:
        raise ValueError("cannot derive slug from empty text")
    candidate = f"{prefix}-{slug}"
    if len(candidate) > max_total_len:
        candidate = candidate[:max_total_len].rstrip("-")
    return candidate
