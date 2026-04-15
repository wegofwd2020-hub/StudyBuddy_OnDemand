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
