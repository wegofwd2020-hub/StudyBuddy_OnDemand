"""
tests/test_content_blocks.py

Epic 12 T-1a — content block schema + Pydantic mirror.

Covers:
  - Happy path for every one of the 17 block types
  - Rejection cases: unknown type, bad id, additionalProperties, block-level
    markdown inside InlineMarkdown fields
  - Drift test: same samples run through JSON Schema and Pydantic — verdicts
    must agree (per Q7(a) of the epic)
  - Stable-id helpers
"""

from __future__ import annotations

import copy
import os
import sys
from typing import Any

import jsonschema
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _candidate in (
    os.path.dirname(os.path.dirname(_HERE)),  # host: .../backend/tests -> repo root
    os.path.dirname(_HERE),                    # container mount: /app/tests -> /app
):
    if os.path.isdir(os.path.join(_candidate, "pipeline")):
        if _candidate not in sys.path:
            sys.path.insert(0, _candidate)
        break

from pipeline.content_blocks import (  # noqa: E402
    ContentBlockValidationError,
    SCHEMA_VERSION,
    _DOCUMENT_ADAPTER,
    load_schema,
    make_positional_id,
    make_slug_id,
    validate_document,
)


# ── Sample blocks (one per type) ─────────────────────────────────────────────


def _doc(block: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "blocks": [block]}


SAMPLE_BLOCKS: dict[str, dict[str, Any]] = {
    "Heading": {
        "type": "Heading",
        "id": "heading-the-accounting-equation",
        "data": {"level": 2, "text": "The Accounting Equation"},
    },
    "Paragraph": {
        "type": "Paragraph",
        "id": "b-0001",
        "data": {"markdown": "A **balance sheet** summarises what a business owns and owes."},
    },
    "List": {
        "type": "List",
        "id": "b-0002",
        "data": {"style": "bullet", "items": ["Assets", "Liabilities", "Equity"]},
    },
    "Callout": {
        "type": "Callout",
        "id": "b-0003",
        "data": {
            "variant": "info",
            "title": "Remember",
            "body": "Assets = Liabilities + Equity.",
        },
    },
    "Figure": {
        "type": "Figure",
        "id": "b-0004",
        "data": {
            "src": "curricula/default-2026-g11/G11-ACC-001/media/balance-sheet.png",
            "alt": "Annotated balance sheet showing the three main sections",
            "caption": "Sample balance sheet for *Acme Ltd.*",
            "attribution": "OpenStax Introductory Business",
            "license": "CC BY 4.0",
        },
    },
    "Quote": {
        "type": "Quote",
        "id": "b-0005",
        "data": {
            "markdown": "Accounting is the language of business.",
            "attribution": "Warren Buffett",
        },
    },
    "Code": {
        "type": "Code",
        "id": "b-0006",
        "data": {"language": "python", "source": "total = assets - liabilities\nprint(total)"},
    },
    "Definition": {
        "type": "Definition",
        "id": "def-balance-sheet",
        "data": {
            "term": "Balance Sheet",
            "body": "A statement of a company's **assets**, *liabilities*, and equity at a point in time.",
        },
    },
    "KeyConcept": {
        "type": "KeyConcept",
        "id": "concept-double-entry",
        "data": {
            "title": "Double-Entry Bookkeeping",
            "body": "Every transaction affects at least two accounts.",
        },
    },
    "WorkedExample": {
        "type": "WorkedExample",
        "id": "b-0007",
        "data": {
            "title": "Preparing a trial balance",
            "prompt": "Given the ledger balances, prepare the trial balance.",
            "steps": [
                {"label": "Step 1", "body": "List every ledger account."},
                {"label": "Step 2", "body": "Place debit balances in the debit column."},
            ],
            "answer": "Total debits equal total credits: $10,000.",
        },
    },
    "TryThis": {
        "type": "TryThis",
        "id": "b-0008",
        "data": {
            "prompt": "Compute equity given assets of $500 and liabilities of $200.",
            "hint": "Use the accounting equation.",
            "answer": "$300",
        },
    },
    "Summary": {
        "type": "Summary",
        "id": "b-0009",
        "data": {"points": ["Assets fund the business.", "Liabilities are claims on assets."]},
    },
    "CrossReference": {
        "type": "CrossReference",
        "id": "b-0010",
        "data": {"target_id": "def-balance-sheet", "label": "See the *balance sheet* definition."},
    },
    "Formula": {
        "type": "Formula",
        "id": "b-0011",
        "data": {"latex": "A = L + E", "label": "Accounting equation", "block": True},
    },
    "DataTable": {
        "type": "DataTable",
        "id": "b-0012",
        "data": {
            "caption": "Balance sheet excerpt",
            "headers": ["Account", "Debit", "Credit"],
            "align": ["left", "right", "right"],
            "rows": [
                ["Cash", "500", "0"],
                ["Loan payable", "0", "200"],
            ],
            "tabular_numbers": True,
        },
    },
    "Diagram": {
        "type": "Diagram",
        "id": "b-0013",
        "data": {
            "format": "mermaid",
            "source": "graph LR\n  A-->B",
            "alt": "Simple two-node flowchart",
        },
    },
    "MediaPlaceholder": {
        "type": "MediaPlaceholder",
        "id": "b-0014",
        "data": {
            "media_type": "video",
            "url": "https://www.youtube.com/watch?v=example",
            "caption": "Walkthrough of the accounting equation",
        },
    },
}


ALL_TYPES = list(SAMPLE_BLOCKS.keys())


# ── Happy path ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("block_type", ALL_TYPES)
def test_happy_path_each_block_type(block_type: str):
    doc = _doc(SAMPLE_BLOCKS[block_type])
    result = validate_document(doc)
    assert result.blocks[0].type == block_type


def test_happy_path_full_document():
    doc = {"schema_version": SCHEMA_VERSION, "blocks": list(SAMPLE_BLOCKS.values())}
    result = validate_document(doc)
    assert len(result.blocks) == len(ALL_TYPES)


def test_seventeen_block_types_supported():
    """Guard against silent type additions/removals."""
    assert len(ALL_TYPES) == 17


# ── Rejection cases ──────────────────────────────────────────────────────────


def test_rejects_unknown_block_type():
    bad = _doc({"type": "Widget", "id": "b-0001", "data": {}})
    with pytest.raises(ContentBlockValidationError):
        validate_document(bad)


def test_rejects_missing_schema_version():
    with pytest.raises(ContentBlockValidationError):
        validate_document({"blocks": [SAMPLE_BLOCKS["Paragraph"]]})


def test_rejects_bad_schema_version_format():
    with pytest.raises(ContentBlockValidationError):
        validate_document({"schema_version": "one-point-zero", "blocks": [SAMPLE_BLOCKS["Paragraph"]]})


def test_rejects_empty_blocks():
    with pytest.raises(ContentBlockValidationError):
        validate_document({"schema_version": SCHEMA_VERSION, "blocks": []})


def test_rejects_bad_block_id_uppercase():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    block["id"] = "BadID"
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_bad_block_id_with_spaces():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    block["id"] = "bad id"
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_missing_id():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    del block["id"]
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_additional_top_level_properties():
    doc = {"schema_version": SCHEMA_VERSION, "blocks": [SAMPLE_BLOCKS["Paragraph"]], "extra": 1}
    with pytest.raises(ContentBlockValidationError):
        validate_document(doc)


def test_rejects_additional_data_properties():
    block = copy.deepcopy(SAMPLE_BLOCKS["Heading"])
    block["data"]["extra"] = "nope"
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_heading_level_out_of_range():
    block = copy.deepcopy(SAMPLE_BLOCKS["Heading"])
    block["data"]["level"] = 5
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_figure_without_alt():
    block = copy.deepcopy(SAMPLE_BLOCKS["Figure"])
    del block["data"]["alt"]
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_figure_with_short_alt():
    block = copy.deepcopy(SAMPLE_BLOCKS["Figure"])
    block["data"]["alt"] = "ab"
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_inline_markdown_table():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    block["data"]["markdown"] = "| a | b |\n| - | - |\n| 1 | 2 |"
    with pytest.raises(ContentBlockValidationError, match="GFM table"):
        validate_document(_doc(block))


def test_rejects_inline_markdown_atx_heading():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    block["data"]["markdown"] = "# Section title"
    with pytest.raises(ContentBlockValidationError, match="ATX heading"):
        validate_document(_doc(block))


def test_rejects_inline_markdown_fenced_code():
    block = copy.deepcopy(SAMPLE_BLOCKS["Paragraph"])
    block["data"]["markdown"] = "before ```x``` after"
    with pytest.raises(ContentBlockValidationError, match="fenced code"):
        validate_document(_doc(block))


def test_rejects_inline_markdown_in_list_item():
    block = copy.deepcopy(SAMPLE_BLOCKS["List"])
    block["data"]["items"] = ["ok", "# not ok"]
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_inline_markdown_in_table_cell():
    block = copy.deepcopy(SAMPLE_BLOCKS["DataTable"])
    block["data"]["rows"] = [["ok", "```bad```", "ok"]]
    block["data"]["headers"] = ["a", "b", "c"]
    block["data"]["align"] = ["left", "left", "left"]
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


def test_rejects_mediaplaceholder_bad_media_type():
    block = copy.deepcopy(SAMPLE_BLOCKS["MediaPlaceholder"])
    block["data"]["media_type"] = "animation"
    with pytest.raises(ContentBlockValidationError):
        validate_document(_doc(block))


# ── Drift test: JSON Schema vs Pydantic verdicts must agree ──────────────────


VALID_SAMPLES: list[dict[str, Any]] = [_doc(b) for b in SAMPLE_BLOCKS.values()]

INVALID_SAMPLES: list[dict[str, Any]] = [
    _doc({"type": "Widget", "id": "b-0001", "data": {}}),
    _doc({**SAMPLE_BLOCKS["Paragraph"], "id": "BadID"}),
    _doc({**SAMPLE_BLOCKS["Paragraph"], "extra_field": 1}),
    {"schema_version": SCHEMA_VERSION, "blocks": []},
    {"schema_version": "invalid", "blocks": [SAMPLE_BLOCKS["Paragraph"]]},
    _doc(
        {
            "type": "Heading",
            "id": "h1",
            "data": {"level": 5, "text": "too deep"},
        }
    ),
    _doc(
        {
            "type": "Figure",
            "id": "f1",
            "data": {
                "src": "x.png",
                "alt": "ab",  # too short
            },
        }
    ),
    _doc(
        {
            "type": "MediaPlaceholder",
            "id": "m1",
            "data": {
                "media_type": "animation",  # not in enum
                "url": "https://example.com",
                "caption": "bad",
            },
        }
    ),
]


@pytest.mark.parametrize("sample", VALID_SAMPLES)
def test_drift_valid_samples_pass_both(sample):
    schema = load_schema()
    # JSON Schema: must not raise
    jsonschema.validate(instance=sample, schema=schema)
    # Pydantic: must not raise
    _DOCUMENT_ADAPTER.validate_python(sample)


@pytest.mark.parametrize("sample", INVALID_SAMPLES)
def test_drift_invalid_samples_fail_both(sample):
    schema = load_schema()

    schema_failed = False
    pydantic_failed = False
    try:
        jsonschema.validate(instance=sample, schema=schema)
    except jsonschema.ValidationError:
        schema_failed = True
    try:
        _DOCUMENT_ADAPTER.validate_python(sample)
    except Exception:
        pydantic_failed = True

    assert schema_failed == pydantic_failed, (
        f"drift: schema_failed={schema_failed} pydantic_failed={pydantic_failed} "
        f"for sample {sample!r}"
    )
    assert schema_failed, "invalid sample should have failed at least one validator"


# ── Stable-id helpers ────────────────────────────────────────────────────────


def test_make_positional_id():
    assert make_positional_id(1) == "b-0001"
    assert make_positional_id(42) == "b-0042"
    assert make_positional_id(9999) == "b-9999"


def test_make_positional_id_rejects_zero_or_negative():
    with pytest.raises(ValueError):
        make_positional_id(0)
    with pytest.raises(ValueError):
        make_positional_id(-3)


def test_make_slug_id_basic():
    assert make_slug_id("def", "Balance Sheet") == "def-balance-sheet"
    assert make_slug_id("heading", "The Accounting Equation") == "heading-the-accounting-equation"
    assert make_slug_id("concept", "Double-Entry Bookkeeping") == "concept-double-entry-bookkeeping"


def test_make_slug_id_strips_punctuation():
    assert make_slug_id("def", "Profit & Loss!!!") == "def-profit-loss"


def test_make_slug_id_rejects_empty():
    with pytest.raises(ValueError):
        make_slug_id("def", "!!!")


def test_make_slug_id_truncates_long():
    long_text = "x" * 200
    result = make_slug_id("def", long_text)
    assert len(result) <= 64


def test_slug_id_passes_blockid_pattern():
    """Slugged IDs must satisfy the BlockId regex."""
    import re

    pattern = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
    for raw in ["Balance Sheet", "Profit & Loss", "The Accounting Equation"]:
        assert pattern.match(make_slug_id("def", raw)), f"failed: {raw}"
