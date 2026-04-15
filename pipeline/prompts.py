"""
pipeline/prompts.py

Prompt builders for StudyBuddy OnDemand content generation.

All functions are pure — they return prompt strings and make no API calls.
Each prompt instructs Claude to return ONLY valid JSON matching the target schema.
Prompts are grade-appropriate (Grade 5 simpler vocabulary; Grade 12 university-prep).
"""

from __future__ import annotations


def _grade_descriptor(grade: int) -> str:
    """Return a language-level descriptor suitable for the prompt."""
    if grade <= 6:
        return "a Grade 5–6 student (age 10–12). Use simple, clear language, short sentences, and relatable everyday examples."
    elif grade <= 8:
        return "a Grade 7–8 student (age 12–14). Use clear explanations with some technical vocabulary, and connect concepts to real-world applications."
    elif grade <= 10:
        return "a Grade 9–10 student (age 14–16). Use precise academic language with proper subject-specific terminology."
    else:
        return "a Grade 11–12 student (age 16–18) preparing for post-secondary studies. Use rigorous, university-prep language with full technical terminology."


# ── Universal formatting guidelines (Epic 11 C-1) ────────────────────────────
# Injected into every prompt so AI-generated content carries the right shape
# for tables and mathematical formulae. Per-subject refinements (Commerce
# Balance Sheets, Science reaction mechanisms, etc.) land in C-2.

_FORMATTING_GUIDELINES = """FORMATTING RULES (apply to all string-valued content fields):

Markdown syntax is ALLOWED inside content string values. The rule against
markdown fences applies ONLY to the outermost JSON response envelope.

TABLES — use GFM markdown tables whenever content is tabular by nature:
  - Comparisons with 2+ attributes
  - Chronologies and timelines
  - Side-by-side concept contrasts
  - Any numeric data set where rows share the same columns
Include column-alignment markers in the separator row:
  | Name | Amount | Description |
  |:-----|-------:|:------------|
  | Cash | 1,500  | Liquid asset |
Left-align text (`:---`), right-align numbers (`---:`), centre headings
(`:---:`). Right-align any monetary or numeric column.

MATHEMATICAL FORMULAE — use LaTeX delimiters:
  - Inline math inside prose: $E = mc^2$
  - Display math on its own line: $$\\int_a^b f(x)\\,dx$$
Use this for all equations, inequalities, fractions, subscripts,
superscripts, Greek letters, and any expression that benefits from typeset
rendering. Do NOT write raw "E = mc^2" as plain text — it will not render.

DOLLAR SIGN AS CURRENCY — escape or spell out to avoid math-mode collisions:
  - Write \\$150.00 (backslash-escaped) inside prose, OR
  - Spell out the currency code: "USD 150.00", "INR 1,200", "EUR 42.50".
Never use an unescaped $ outside a math expression.

SCIENTIFIC NOTATION:
  - In inline prose, Unicode superscripts are fine: "1.6 × 10⁻¹⁹ C".
  - In display equations, use KaTeX: $$1.6 \\times 10^{-19}\\,\\mathrm{C}$$.

FENCED CODE BLOCKS — use for pseudocode, algorithms, and program listings:
  ```python
  def area(r):
      return 3.14159 * r * r
  ```
"""


# ── Per-subject guidelines (Epic 11 C-2) ─────────────────────────────────────
# Injected in addition to the universal block. Subject names are matched
# case-insensitively against canonical groupings — unknown subjects fall
# through to the empty string (no-op).

_COMMERCE_GUIDELINES = """SUBJECT-SPECIFIC — COMMERCE (Accountancy / Business Studies / Economics):

Financial statements — ALWAYS render as markdown tables with right-aligned
numeric columns. Templates:

Balance Sheet example:
| Item | Amount (INR) |
|:-----|-------------:|
| Cash and Cash Equivalents | 50,000 |
| Accounts Receivable       | 30,000 |
| Inventory                 | 20,000 |
| **Total Current Assets**  | **100,000** |

Profit & Loss statement example:
| Line Item | Amount (INR) |
|:----------|-------------:|
| Revenue             | 500,000 |
| Cost of Goods Sold  | (300,000) |
| **Gross Profit**    | **200,000** |

Trial Balance example:
| Account | Debit | Credit |
|:--------|------:|-------:|
| Cash             | 50,000 |        |
| Accounts Payable |        | 30,000 |

Cash Flow statement: three sections — Operating, Investing, Financing —
each rendered as its own table. Use parentheses (300,000) for negative
values, bold rows for subtotals and totals. Always spell out currency
(INR / USD / EUR) — never unescaped $.

Accounting equations render as KaTeX:
  $$\\text{Assets} = \\text{Liabilities} + \\text{Equity}$$
  $$\\text{Gross Profit Margin} = \\frac{\\text{Gross Profit}}{\\text{Revenue}} \\times 100\\%$$
"""


_SCIENCE_GUIDELINES = """SUBJECT-SPECIFIC — NATURAL SCIENCES (Physics / Chemistry / Biology):

Formulae and equations — ALWAYS in KaTeX, never raw text.
  Physics: $$F = ma$$, $$E_k = \\tfrac{1}{2}mv^2$$, $$\\lambda = \\frac{h}{p}$$
  Chemistry: balanced equations via `\\ce{}` or arrow notation:
    $$2\\mathrm{H}_2 + \\mathrm{O}_2 \\rightarrow 2\\mathrm{H}_2\\mathrm{O}$$
  Biology: kinetic and equilibrium expressions as display math.

Reaction mechanisms / stoichiometry — tables:
| Reactant | Coefficient | Product | Coefficient |
|:---------|:-----------:|:--------|:-----------:|
| H₂       | 2           | H₂O     | 2           |
| O₂       | 1           |         |             |

Periodic-table excerpts, taxonomic ladders, comparative species tables,
genetic crosses (Punnett squares) — all as markdown tables. Keep Punnett
squares to 2×2 or 4×4 grids with bold allele labels.

Units: use KaTeX `\\mathrm{}` for unit typesetting in display equations
(e.g. $\\mathrm{m/s^2}$, $\\mathrm{kg \\cdot m^2}$). In inline prose,
Unicode is fine ("9.8 m/s²").

Observation tables and lab data should always be tabular.
"""


_MATHEMATICS_GUIDELINES = """SUBJECT-SPECIFIC — MATHEMATICS:

EVERY mathematical expression goes in KaTeX — inline `$...$` for expressions
that live mid-sentence, display `$$...$$` for expressions on their own line.
This applies to: variables ($x$, $y$), fractions ($\\frac{a}{b}$), powers
($x^2$), roots ($\\sqrt{2}$), integrals, sums, limits, matrices, set
notation, trigonometric functions, logarithms — everything.

Worked solutions: present each step in a numbered list; put the equation
on a display-math line beneath its explanation.

1. Move all $x$ terms to the left-hand side:
   $$3x + 2 = x + 10$$
   $$2x = 8$$
2. Divide both sides by 2:
   $$x = 4$$

Systems of equations, matrix operations, transformations — present the
matrix/system as display math. Proofs (geometric, algebraic, by induction)
use numbered steps where each justification cites a rule or earlier step.

Comparisons of functions, function-value tables, and piecewise definitions
render as markdown tables with right-aligned numeric columns.
"""


_CS_GUIDELINES = """SUBJECT-SPECIFIC — COMPUTER SCIENCE / TECHNOLOGY:

Pseudocode and program listings — fenced code blocks with the language tag
(```python, ```javascript, ```java, ```sql, etc.). Use 4-space indentation;
keep snippets under 20 lines; annotate with inline `# comments`.

Complexity analysis — KaTeX for asymptotic notation ($O(n \\log n)$,
$\\Theta(n^2)$, $\\Omega(n)$). Complexity comparisons as markdown tables:

| Operation | Array | Linked List | Hash Map |
|:----------|:-----:|:-----------:|:--------:|
| Lookup    | $O(1)$ | $O(n)$     | $O(1)$   |
| Insert    | $O(n)$ | $O(1)$     | $O(1)$   |

Truth tables — always as markdown tables with centred columns:
| p | q | p ∧ q | p ∨ q |
|:-:|:-:|:-----:|:-----:|
| T | T | T     | T     |
| T | F | F     | T     |

Data-structure diagrams (trees, graphs, linked lists) — use Mermaid.js
(```mermaid ... ```) for flowcharts and control flow, consistent with
CLAUDE.md content rule §4.

Shell commands in fenced `bash` blocks. Configuration files (JSON, YAML,
TOML) in fenced blocks tagged with the format.
"""


# Keyword → guideline block. Subjects are normalised (lowercase, stripped).
# Order matters: more-specific subjects first. "Computer Science" must match
# _CS_GUIDELINES before the bare "science" tests against the natural-sciences
# block (so _SCIENCE_GUIDELINES deliberately omits the over-broad "science"
# keyword — matching is anchored on specific discipline names only).
_SUBJECT_GUIDELINE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("computer science", "computing", "informatics", "programming", "coding",
      "information technology", "technology"),
     _CS_GUIDELINES),
    (("accountancy", "accounting", "business studies", "economics", "commerce"),
     _COMMERCE_GUIDELINES),
    (("physics", "chemistry", "biology"),
     _SCIENCE_GUIDELINES),
    (("mathematics", "math", "maths", "algebra", "geometry", "calculus", "statistics"),
     _MATHEMATICS_GUIDELINES),
]


def _subject_guidelines(subject: str) -> str:
    """Return the matching subject-specific guidelines, or '' if none match."""
    s = (subject or "").strip().lower()
    if not s:
        return ""
    for keywords, block in _SUBJECT_GUIDELINE_KEYWORDS:
        for kw in keywords:
            if kw in s:
                return block
    return ""


def build_lesson_prompt(
    unit_id: str,
    subject: str,
    topic: str,
    grade: int,
    lang: str,
) -> str:
    """Return the prompt for generating a lesson JSON document."""
    grade_desc = _grade_descriptor(grade)
    lang_instruction = f"Write all content in {lang.upper()} language." if lang != "en" else "Write all content in English."

    return f"""You are an expert STEM educator creating a lesson for {grade_desc}

{lang_instruction}

Generate a comprehensive lesson on the topic: "{topic}" (subject: {subject}, grade: {grade})
Unit ID: {unit_id}

You MUST respond with ONLY valid JSON — no markdown fences, no extra text, no explanation.

{_FORMATTING_GUIDELINES}
{_subject_guidelines(subject)}
The JSON must exactly match this schema:

{{
  "unit_id": "{unit_id}",
  "subject": "{subject}",
  "topic": "{topic}",
  "synopsis": "<2–3 sentence overview of the lesson>",
  "key_concepts": ["<concept 1>", "<concept 2>", "..."],
  "learning_objectives": ["<objective 1>", "<objective 2>", "..."],
  "reading_level": "<e.g., Grade {grade} reading level>",
  "estimated_duration_minutes": <integer between 20 and 45>,
  "language": "{lang}",
  "generated_at": "<ISO 8601 timestamp>",
  "model": "<model name used>",
  "content_version": 1
}}

Requirements:
- key_concepts: 4–8 items
- learning_objectives: 3–5 items, starting with action verbs (e.g., "Explain...", "Calculate...", "Identify...")
- synopsis: engaging and age-appropriate
- Do NOT include any text outside the JSON object
"""


def build_quiz_prompt(
    unit_id: str,
    subject: str,
    topic: str,
    grade: int,
    lang: str,
    set_number: int,
) -> str:
    """Return the prompt for generating a quiz set JSON document."""
    grade_desc = _grade_descriptor(grade)
    lang_instruction = f"Write all content in {lang.upper()} language." if lang != "en" else "Write all content in English."

    return f"""You are an expert STEM educator creating a quiz for {grade_desc}

{lang_instruction}

Generate quiz set {set_number} of 3 for the topic: "{topic}" (subject: {subject}, grade: {grade})
Unit ID: {unit_id}

You MUST respond with ONLY valid JSON — no markdown fences, no extra text, no explanation.

{_FORMATTING_GUIDELINES}
{_subject_guidelines(subject)}
The JSON must exactly match this schema:

{{
  "unit_id": "{unit_id}",
  "set_number": {set_number},
  "language": "{lang}",
  "questions": [
    {{
      "question_id": "q1",
      "question_text": "<question text>",
      "question_type": "multiple_choice",
      "options": [
        {{"option_id": "A", "text": "<option text>"}},
        {{"option_id": "B", "text": "<option text>"}},
        {{"option_id": "C", "text": "<option text>"}},
        {{"option_id": "D", "text": "<option text>"}}
      ],
      "correct_option": "A",
      "explanation": "<why this answer is correct>",
      "difficulty": "easy"
    }}
  ],
  "total_questions": 8,
  "estimated_duration_minutes": 10,
  "passing_score": 6,
  "generated_at": "<ISO 8601 timestamp>",
  "model": "<model name used>",
  "content_version": 1
}}

Requirements:
- EXACTLY 8 questions — no more, no fewer
- Each question has EXACTLY 4 options (A, B, C, D)
- correct_option must be one of: "A", "B", "C", "D"
- difficulty must be one of: "easy", "medium", "hard"
  - Include roughly 2–3 easy, 3–4 medium, 1–2 hard questions
- Set {set_number} should cover different aspects of the topic than sets 1–{set_number - 1 if set_number > 1 else 0}
- Do NOT include any text outside the JSON object
"""


def build_tutorial_prompt(
    unit_id: str,
    subject: str,
    topic: str,
    grade: int,
    lang: str,
) -> str:
    """Return the prompt for generating a tutorial (step-by-step walkthrough) JSON document."""
    grade_desc = _grade_descriptor(grade)
    lang_instruction = f"Write all content in {lang.upper()} language." if lang != "en" else "Write all content in English."

    return f"""You are an expert STEM educator creating a worked tutorial for {grade_desc}

{lang_instruction}

Generate a step-by-step tutorial for the topic: "{topic}" (subject: {subject}, grade: {grade})
Unit ID: {unit_id}

You MUST respond with ONLY valid JSON — no markdown fences, no extra text, no explanation.

{_FORMATTING_GUIDELINES}
{_subject_guidelines(subject)}
The JSON must exactly match this schema:

{{
  "unit_id": "{unit_id}",
  "language": "{lang}",
  "title": "<tutorial title>",
  "sections": [
    {{
      "section_id": "s1",
      "title": "<section title>",
      "content": "<detailed explanation for this section>",
      "examples": ["<worked example 1>", "<worked example 2>"],
      "practice_question": "<a practice question for the student to try>"
    }}
  ],
  "common_mistakes": ["<mistake 1>", "<mistake 2>", "<mistake 3>"],
  "generated_at": "<ISO 8601 timestamp>",
  "model": "<model name used>",
  "content_version": 1
}}

Requirements:
- 3–5 sections covering the topic progressively (from fundamentals to application)
- Each section has 1–3 worked examples
- common_mistakes: 3–5 items, describing errors students frequently make
- Do NOT include any text outside the JSON object
"""


def build_experiment_prompt(
    unit_id: str,
    subject: str,
    topic: str,
    grade: int,
    lang: str,
) -> str:
    """
    Return the prompt for generating a lab experiment JSON document.
    Only called for units where has_lab=True.
    """
    grade_desc = _grade_descriptor(grade)
    lang_instruction = f"Write all content in {lang.upper()} language." if lang != "en" else "Write all content in English."

    return f"""You are an expert STEM educator creating a hands-on lab experiment for {grade_desc}

{lang_instruction}

Generate a safe, classroom-appropriate lab experiment for the topic: "{topic}" (subject: {subject}, grade: {grade})
Unit ID: {unit_id}

You MUST respond with ONLY valid JSON — no markdown fences, no extra text, no explanation.

{_FORMATTING_GUIDELINES}
{_subject_guidelines(subject)}
The JSON must exactly match this schema:

{{
  "unit_id": "{unit_id}",
  "language": "{lang}",
  "experiment_title": "<title of the experiment>",
  "materials": ["<material 1>", "<material 2>", "..."],
  "safety_notes": ["<safety note 1>", "<safety note 2>"],
  "steps": [
    {{
      "step_number": 1,
      "instruction": "<what the student does>",
      "expected_observation": "<what the student should observe>"
    }}
  ],
  "questions": [
    {{
      "question": "<reflection question>",
      "answer": "<expected answer>"
    }}
  ],
  "conclusion_prompt": "<open-ended prompt asking the student to write their conclusion>",
  "generated_at": "<ISO 8601 timestamp>",
  "model": "<model name used>",
  "content_version": 1
}}

Requirements:
- materials: 4–10 common, safe, school-available items
- safety_notes: 2–5 items; must always be included even if the experiment is low-risk
- steps: 4–10 steps
- questions: 3–5 reflection questions
- All materials and procedures must be safe for the target age group
- Do NOT include any text outside the JSON object
"""
