"""No prompt may instruct the model to emit a JSON-invalid escape in PROSE.

Every content type comes back as JSON and is parsed with a bare `json.loads`
(`pipeline/build_unit.py::_parse_json_response` strips code fences and nothing
else). So prose that tells the model to put a literal backslash before a
character JSON cannot escape produces output that will not parse, three retries
burn on the same instruction, and the unit is marked failed.

That is not hypothetical. The C-5 regen (#745) lost exactly two units to it:

    G11-ACC-001  quiz_set_2  Invalid \\escape: line 36 column 97
    G12-ACC-002  quiz_set_1  Invalid \\escape: line 22 column 112

Both Accountancy -- the only currency-dense subject -- because the rule that
caused it was about currency:

    - Write \\$150.00 (backslash-escaped) inside prose, OR

`_FORMATTING_GUIDELINES` is a NORMAL triple-quoted string, so that `\\\\$`
collapsed to a single backslash and the model was told, literally, to write
`\\$150.00`. JSON permits only `\\" \\\\ \\/ \\b \\f \\n \\r \\t \\uXXXX`.

## Why this guard excludes math and code spans

The prompts are FULL of single backslashes: `$$\\int_a^b f(x)\\,dx$$`,
`\\frac{a}{b}`, `\\times 100\\%`, `` `\\mathrm{}` ``. A guard that flagged those
too would be flagging the 103 units that regenerated CLEANLY -- every one of
them maths- or science-heavy. Those backslashes are KaTeX *notation being
demonstrated*, and the model escapes them correctly on the way out (it emits
`\\\\frac` in the JSON, which decodes to `\\frac`).

The currency line was different in kind: it did not show notation, it gave an
*escaping instruction* -- "backslash-escaped" -- for prose. The model obeyed it
literally and emitted a raw `\\$`, because it had been told the backslash WAS
the escape. So the guard is scoped to prose: math spans (`$...$`, `$$...$$`),
fenced blocks and inline code spans are stripped before scanning.

Two things make this worth a standing test rather than a one-line fix:

  - It is silent in review. The prompt reads as correct English; only the
    interaction between "literal backslash" and "delivered as JSON" breaks it.
  - The failure mode is subject-specific, so a full regen of most grades passes
    and the bug only surfaces on the curricula that happen to use currency.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# The complete set JSON allows after a backslash. `u` additionally requires four
# hex digits, but a prompt telling the model to write `\uXXXX` is not the shape
# this guards against.
_VALID_JSON_ESCAPES = set('"\\/bfnrtu')

# A single backslash followed by one non-whitespace character. Two backslashes
# are fine -- that IS the escaped form.
_SINGLE_BACKSLASH = re.compile(r"(?<!\\)\\([^\s\\])")

# Notation-demonstrating spans. Backslashes inside these are KaTeX being shown,
# not an instruction about escaping; see the module docstring.
_NOTATION_SPANS = re.compile(
    r"```.*?```"  # fenced code block
    r"|\$\$.*?\$\$"  # display math
    r"|\$[^$\n]*\$"  # inline math (same line only)
    r"|`[^`\n]*`",  # inline code span
    re.DOTALL,
)


def _prompt_module():
    import pipeline.prompts as prompts

    return prompts


def _prose(text: str) -> str:
    """`text` with notation spans removed, so only instructions remain."""
    return _NOTATION_SPANS.sub(" ", text)


def _offending_escapes(text: str) -> list[str]:
    """Backslash sequences in the PROSE of `text` that JSON could not represent."""
    return [
        m.group(0)
        for m in _SINGLE_BACKSLASH.finditer(_prose(text))
        if m.group(1) not in _VALID_JSON_ESCAPES
    ]


def test_the_reported_failure_is_reproducible():
    """Pin the exact mechanism, so a future reader need not take it on trust."""
    # What the model produces when it follows a `write \$150.00` instruction.
    with pytest.raises(json.JSONDecodeError) as exc:
        json.loads(r'{"q": "The asset cost \$150.00 in cash."}')
    assert "Invalid \\escape" in str(exc.value)

    # The correctly escaped form parses, and yields the single backslash back.
    # This is what the model already does for KaTeX, which is why maths units
    # regenerate cleanly.
    assert json.loads(r'{"q": "cost \\$150.00"}')["q"] == r"cost \$150.00"

    # Spelling out the currency -- the fix -- needs no escaping at all.
    assert json.loads('{"q": "cost USD 150.00"}')["q"] == "cost USD 150.00"


def test_universal_formatting_block_instructs_no_invalid_escape():
    """The block that reaches EVERY content type, and caused the two failures."""
    guidelines = _prompt_module()._FORMATTING_GUIDELINES
    bad = _offending_escapes(guidelines)
    assert not bad, (
        f"_FORMATTING_GUIDELINES tells the model to emit {bad} in prose, which "
        "JSON cannot represent. Spell the value out instead (e.g. 'USD 150.00')."
    )


# The two units the regen actually lost, so the arguments are not invented.
# Accountancy selects the Commerce subject block -- where the currency guidance
# lives -- and set 2 is the quiz set that failed on G11-ACC-001.
_REAL_CASE = dict(
    unit_id="G11-ACC-001",
    subject="Accountancy",
    topic="Depreciation and Asset Valuation",
    grade=11,
    lang="en",
)


@pytest.mark.parametrize(
    "builder,extra",
    [
        ("build_lesson_prompt", {}),
        ("build_quiz_prompt", {"set_number": 2}),
        ("build_tutorial_prompt", {}),
        ("build_experiment_prompt", {}),
    ],
)
def test_built_prompts_instruct_no_invalid_escape(builder, extra):
    """The assembled prompt, not just the shared block.

    A per-subject block can reintroduce the instruction on its own -- the
    Commerce block sits right next to the rule that caused this.
    """
    fn = getattr(_prompt_module(), builder)
    bad = _offending_escapes(fn(**_REAL_CASE, **extra))
    assert not bad, f"{builder} instructs the model to emit {bad} in prose; JSON cannot represent it"


def test_every_required_argument_is_supplied():
    """Guard the guard: a builder gaining a required arg must not silently skip.

    The first draft of this file synthesised arguments by reflection and passed
    a string where `set_number: int` was expected -- the prompt was never built
    and the escape check never ran.
    """
    for builder, extra in (
        ("build_lesson_prompt", {}),
        ("build_quiz_prompt", {"set_number": 2}),
        ("build_tutorial_prompt", {}),
        ("build_experiment_prompt", {}),
    ):
        fn = getattr(_prompt_module(), builder)
        # Raises TypeError if the call is not fully satisfied.
        inspect.signature(fn).bind(**_REAL_CASE, **extra)


def test_the_guard_would_have_caught_the_regression():
    """Mutation check in test form: the pre-fix text must still be rejected.

    Stripping notation spans is exactly the kind of narrowing that can quietly
    turn a guard into a no-op, so the offending line is asserted against the
    real helper -- including the `$` in it, which must not make the line look
    like a math span.
    """
    pre_fix = (
        "DOLLAR SIGN AS CURRENCY — escape or spell out:\n"
        "  - Write \\$150.00 (backslash-escaped) inside prose, OR\n"
        '  - Spell out the currency code: "USD 150.00".\n'
        "Never use an unescaped $ outside a math expression.\n"
    )
    assert _offending_escapes(pre_fix) == ["\\$"]


def test_notation_is_deliberately_allowed_and_prose_is_not():
    """The scope decision itself, so a later reader can see it was a choice.

    103 of 105 units in the #745 regen carried KaTeX like this and parsed
    fine. Flagging it would fail the prompts that DEMONSTRABLY work.
    """
    assert _offending_escapes(r"Display math: $$\int_a^b f(x)\,dx$$") == []
    assert _offending_escapes(r"Use $\frac{a}{b}$ for fractions") == []
    assert _offending_escapes(r"Unit typesetting uses `\mathrm{}` here") == []
    assert _offending_escapes("Percent in math: $100\\%$") == []

    # ...but the same command in prose, outside any span, is still an
    # instruction to emit a literal backslash, and is still caught.
    # (`\f` would be a poor example -- formfeed IS a legal JSON escape.)
    assert _offending_escapes(r"Write \int in your prose") == ["\\i"]

    # And the legitimately escaped forms are never flagged.
    assert _offending_escapes(r"Escape it as \\$ if you must") == []
    assert _offending_escapes('Spell it out: "USD 150.00"') == []
    assert _offending_escapes(r"A newline is \n and a tab is \t") == []
