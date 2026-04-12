"""
backend/src/help/service.py

Deliver-1 + Deliver-3 — contextual help response generation.

Pipeline:
  1. Embed the question (Voyage AI voyage-3-lite, 512 dims)
     Fallback: full-text tsvector search when VOYAGE_API_KEY is absent.
  2. Retrieve top-3 most relevant help_chunks by cosine similarity (pgvector).
  3. Build a structured prompt with retrieved context.
  4. Call Claude Haiku for a deterministic, numbered-step answer.
  5. Parse and return the structured response.

Design notes:
  - Temperature=0 → same question always produces the same answer.
  - Max tokens=400 → help responses are concise by design.
  - The LLM is instructed to answer ONLY from retrieved context — hallucination
    risk is minimal because the retrieval step has already done the hard work.
  - If no relevant chunks are found, the endpoint returns a graceful fallback
    rather than fabricating an answer.
"""

from __future__ import annotations

import re

import asyncpg
from config import settings
from src.utils.logger import get_logger

log = get_logger("help")

_EMBED_DIM = 512
_TOP_K = 3
_HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Persona labels used in the prompt (human-readable)
_PERSONA_LABELS = {
    "school_admin": "School Admin",
    "teacher": "Teacher",
    "student": "Student",
}

# Human-readable labels and formatters for recognised account_state keys.
# Values passed from the frontend are sanitised through these formatters —
# the raw dict is never interpolated directly into the prompt.
_ACCOUNT_STATE_LABELS: dict[str, tuple[str, object]] = {
    "first_login": (
        "First login (temporary password not yet changed)",
        lambda v: "Yes — user must change password before using the portal" if v else "No",
    ),
    "teacher_count": (
        "Teachers provisioned",
        lambda v: str(int(v)),
    ),
    "student_count": (
        "Students enrolled",
        lambda v: str(int(v)),
    ),
    "classroom_count": (
        "Classrooms created",
        lambda v: str(int(v)),
    ),
    "curriculum_assigned": (
        "Curriculum package assigned to a classroom",
        lambda v: "Yes" if v else "No — no packages assigned yet",
    ),
}


def _render_account_context(account_state: dict | None) -> str:
    """
    Render account_state into a human-readable block for the prompt.

    Only recognised keys are included. Unknown keys are silently dropped so
    future signals can be added to the frontend incrementally.
    Returns an empty string when no recognised signals are present.
    """
    if not account_state:
        return ""
    lines: list[str] = []
    for key, (label, fmt) in _ACCOUNT_STATE_LABELS.items():
        if key in account_state:
            try:
                lines.append(f"- {label}: {fmt(account_state[key])}")
            except (TypeError, ValueError):
                pass  # malformed value — skip rather than fail
    if not lines:
        return ""
    return "Account context (use to personalise the answer):\n" + "\n".join(lines) + "\n"


# Structured output template the LLM must follow
_PROMPT_TEMPLATE = """\
You are a help assistant for StudyBuddy OnDemand, a K-12 STEM tutoring platform.

Persona: {persona_label}
Current page: {page}
{account_context}
Answer the question below using ONLY the reference content provided.
Format your answer EXACTLY as follows (no extra text outside these sections):

TITLE: <brief task title, ≤ 10 words>
STEPS:
1. <first action>
2. <second action>
(add more numbered steps as needed — maximum 7)
RESULT: <one sentence starting with ✓ that describes what success looks like>
RELATED: <comma-separated list of 2–3 related topic labels>

Rules:
- Reference actual UI labels, button names, and nav items verbatim.
- Each step is exactly one action. Never combine two actions in one step.
- If the question cannot be answered from the reference content, output:
  TITLE: I don't know
  STEPS:
  1. Please check the help documentation or contact support.
  RESULT: ✓ A support link is available in the Help menu.
  RELATED:

Question: {question}

Reference content:
{context}
"""


# ── Embedding ──────────────────────────────────────────────────────────────────


async def _embed(text: str) -> list[float] | None:
    """
    Embed text with Voyage AI voyage-3-lite (512 dims).

    Returns None if VOYAGE_API_KEY is not configured — the caller falls back
    to full-text search.
    """
    if not settings.VOYAGE_API_KEY:
        return None
    import voyageai  # imported lazily — not required for non-help routes
    client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
    result = await client.embed([text], model="voyage-3-lite", input_type="query")
    return result.embeddings[0]


# ── Retrieval ─────────────────────────────────────────────────────────────────


async def _retrieve_by_vector(
    conn: asyncpg.Connection,
    persona: str,
    embedding: list[float],
    k: int = _TOP_K,
) -> list[asyncpg.Record]:
    """Cosine-similarity search over help_chunks using pgvector."""
    vec_literal = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
    return await conn.fetch(
        """
        SELECT chunk_id::text, heading, body, source_file, section_id
        FROM help_chunks
        WHERE persona = $1
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $2::vector
        LIMIT $3
        """,
        persona,
        vec_literal,
        k,
    )


async def _retrieve_by_text(
    conn: asyncpg.Connection,
    persona: str,
    question: str,
    k: int = _TOP_K,
) -> list[asyncpg.Record]:
    """
    Fallback full-text search when no VOYAGE_API_KEY is configured.

    Uses PostgreSQL tsvector full-text matching on heading + body.
    Less precise than vector similarity but requires no external API.
    """
    return await conn.fetch(
        """
        SELECT chunk_id::text, heading, body, source_file, section_id,
               ts_rank(
                   to_tsvector('english', heading || ' ' || body),
                   plainto_tsquery('english', $2)
               ) AS rank
        FROM help_chunks
        WHERE persona = $1
        ORDER BY rank DESC, created_at DESC
        LIMIT $3
        """,
        persona,
        question,
        k,
    )


# ── Haiku call ────────────────────────────────────────────────────────────────


async def _call_haiku(prompt: str) -> str:
    """Call Claude Haiku with temperature=0 for deterministic structured output."""
    import anthropic  # already in requirements; imported here to isolate the import
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY or "")
    msg = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=400,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── Response parsing ──────────────────────────────────────────────────────────


def _parse_response(raw: str, chunks: list[asyncpg.Record]) -> dict:
    """
    Parse the structured LLM output into the HelpAskResponse fields.

    Expected format:
        TITLE: <text>
        STEPS:
        1. <step>
        2. <step>
        RESULT: <text>
        RELATED: <comma list>
    """
    title_m = re.search(r"TITLE:\s*(.+)", raw)
    result_m = re.search(r"RESULT:\s*(.+)", raw)
    related_m = re.search(r"RELATED:\s*(.+)", raw)

    # Extract numbered steps between STEPS: and RESULT:
    steps_block = re.search(r"STEPS:\s*\n(.*?)(?=RESULT:|$)", raw, re.DOTALL)
    steps: list[str] = []
    if steps_block:
        for line in steps_block.group(1).splitlines():
            step_m = re.match(r"\s*\d+\.\s+(.+)", line)
            if step_m:
                steps.append(step_m.group(1).strip())

    title = title_m.group(1).strip() if title_m else "Help"
    result = result_m.group(1).strip() if result_m else ""
    related_raw = related_m.group(1).strip() if related_m else ""
    related = [r.strip() for r in related_raw.split(",") if r.strip()] if related_raw else []

    # Surface which library sections were used (for transparency)
    sources = [c["heading"] for c in chunks]

    return {
        "title": title,
        "steps": steps or ["Please check the help documentation or contact support."],
        "result": result or "✓ Done.",
        "related": related[:3],
        "sources": sources,
    }


# ── Public interface ──────────────────────────────────────────────────────────


async def ask_help(
    conn: asyncpg.Connection,
    question: str,
    page: str | None,
    persona: str,
    account_state: dict | None = None,
) -> dict:
    """
    Full Deliver-1 + Deliver-3 pipeline: embed → retrieve → prompt → parse.

    account_state is an optional dict of context signals collected by the
    widget (first_login, teacher_count, etc.). Only recognised keys are
    threaded into the prompt — unknown keys are silently dropped.

    Returns a dict matching HelpAskResponse fields.
    """
    # 1. Embed
    embedding = await _embed(question)

    # 2. Retrieve
    if embedding is not None:
        chunks = await _retrieve_by_vector(conn, persona, embedding)
    else:
        log.info("help_text_fallback", reason="no_voyage_key", persona=persona)
        chunks = await _retrieve_by_text(conn, persona, question)

    if not chunks:
        log.info("help_no_chunks", persona=persona, question_len=len(question))
        return {
            "title": "I don't know",
            "steps": ["Please check the help documentation or contact support."],
            "result": "✓ A support link is available in the Help menu.",
            "related": [],
            "sources": [],
        }

    # 3. Build context + prompt
    context_parts = [f"## {c['heading']}\n{c['body']}" for c in chunks]
    context = "\n\n---\n\n".join(context_parts)

    page_label = page or "unknown"
    persona_label = _PERSONA_LABELS.get(persona, "User")
    account_context = _render_account_context(account_state)

    prompt = _PROMPT_TEMPLATE.format(
        persona_label=persona_label,
        page=page_label,
        account_context=account_context,
        question=question,
        context=context,
    )

    # 4. Call Haiku
    raw = await _call_haiku(prompt)
    log.info(
        "help_haiku_called",
        persona=persona,
        response_chars=len(raw),
        has_account_state=account_state is not None,
    )

    # 5. Parse
    return _parse_response(raw, list(chunks))
