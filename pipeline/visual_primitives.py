"""
pipeline/visual_primitives.py — visual-primitive identification (issue #323 / 319c).

For each tutorial section, identify what visual primitives would aid
comprehension.  Output is a list[VisualNeed]: each entry is a
library-shaped query (kind + topic_phrase + keywords + confidence) that
the resolver (backend/src/visuals/resolver.py) can match against
visual_library_entries via cosine similarity.

The LLM's job here is *extraction* — turn a long section into a short
canonical phrase that mirrors how library sidecars are written.  This is
why we don't embed the section directly: an embedding of the full
section would be diluted by exposition, examples, asides.  We want the
embedding-shaped equivalent of the sidecar's `topic_phrase + keywords`.

Public surface:
  - VisualNeed              Pydantic model
  - identify_visual_needs() async — returns list[VisualNeed]
  - PROMPT_TEMPLATE         the prompt sent to the LLM (exposed for tests)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger("pipeline.visual_primitives")

# Same closed enum as backend/src/visuals/library.py and the sidecar
# validator — keep in sync if either side widens.
VisualKind = Literal["image", "image-grid", "animated-svg", "video"]


class VisualNeed(BaseModel):
    """One visual primitive a section would benefit from."""

    kind: VisualKind
    topic_phrase: str = Field(min_length=1, max_length=200)
    keywords: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


PROMPT_TEMPLATE = """\
You are a STEM-content reviewer deciding what visual aids a tutorial
section would benefit from.

Section subject: {subject}
Section title:   {section_title}
Section body:
\"\"\"
{section_content}
\"\"\"

Return a JSON ARRAY (possibly empty) of visual needs the section calls
for.  A visual need is appropriate when the concept is fundamentally
spatial, geometric, dynamic, or comparative — not when prose alone
suffices.  Do NOT invent needs that aren't in the section.  If the
section is text-heavy with no clear visual trigger, return [].

Each item MUST be an object with these keys (strict — no extras):
  - kind: one of "image" (single static figure), "image-grid"
          (a comparison set of related figures), "animated-svg"
          (motion or step-through reveals essential), "video" (long-form
          motion with audio).
  - topic_phrase: 3–10 words naming the concept the visual depicts.
                  Phrase it the way a library curator would caption it
                  (e.g. "projectile motion trajectory at 60 degrees",
                  "Venn diagram set intersection").  Lower-case.
  - keywords: 3–8 lower-case alphanumeric-or-hyphen tokens that
              supplement topic_phrase (e.g. "trajectory", "parabola",
              "max-height").  No spaces inside a token.  No trailing
              punctuation.
  - confidence: float in [0.0, 1.0].  Use ≥ 0.85 only when the visual is
                clearly necessary; 0.6–0.8 for "would help"; below 0.5
                for borderline cases the resolver should probably skip.

Output ONLY the JSON array.  No prose, no markdown fences, no commentary.
If unsure, prefer fewer high-confidence needs over many low-confidence
ones.
"""


def _strip_code_fences(text: str) -> str:
    """LLMs sometimes wrap JSON in ```json blocks despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        # Drop opening fence (with or without language tag) and closing fence
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _parse_response(raw: str) -> list[VisualNeed]:
    """Parse the LLM response into VisualNeed[]; never raise on bad input."""
    cleaned = _strip_code_fences(raw)
    if not cleaned:
        log.warning("visual_primitives: empty LLM response")
        return []

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.warning("visual_primitives: bad JSON from LLM: %s", e)
        return []

    if not isinstance(parsed, list):
        log.warning(
            "visual_primitives: expected JSON array, got %s",
            type(parsed).__name__,
        )
        return []

    needs: list[VisualNeed] = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            log.warning("visual_primitives: item %d is not an object", i)
            continue
        try:
            needs.append(VisualNeed(**item))
        except ValidationError as e:
            log.warning("visual_primitives: item %d failed validation: %s", i, e)
    return needs


async def identify_visual_needs(
    section_content: str,
    section_title: str,
    subject: str,
    *,
    provider_id: str = "anthropic",
    settings=None,
) -> list[VisualNeed]:
    """LLM pass over a section's content + title returning visual needs.

    Args:
        section_content: The full prose body of the section.
        section_title:   Short heading, included in the prompt for context.
        subject:         Closed-enum subject from the library
                         (physics / chemistry / math / biology / …).
        provider_id:     Which pipeline LLM provider to use (default
                         "anthropic"; set to "openai" or "google" via
                         caller config).
        settings:        Pipeline settings instance (api keys, model id).
                         Defaults to `pipeline.config.settings` when None.

    Returns:
        list[VisualNeed]. May be empty: a text-heavy section legitimately
        has no visual needs, and a malformed LLM response also returns
        []. The two are distinguishable in logs (warning on parse fail,
        nothing on legitimate empty array).

    Never raises on bad LLM output — the resolver downstream is
    responsible for handling [] gracefully.  This is by design: a
    pipeline run must not fail because one provider gave us garbage.
    """
    if settings is None:
        from pipeline.config import settings as default_settings  # local import

        settings = default_settings

    from pipeline.providers import get_provider  # local import — formatter strips top-level

    prompt = PROMPT_TEMPLATE.format(
        subject=subject,
        section_title=section_title,
        section_content=section_content,
    )

    provider = get_provider(provider_id, settings)
    try:
        # provider.generate is sync; offload so the pipeline event loop
        # (or the resolver caller) doesn't block.
        text, _in_tok, _out_tok = await asyncio.to_thread(provider.generate, prompt)
    except Exception as e:  # noqa: BLE001 — provider can raise SDK-specific errors
        log.warning("visual_primitives: provider %s failed: %s", provider_id, e)
        return []

    return _parse_response(text)
