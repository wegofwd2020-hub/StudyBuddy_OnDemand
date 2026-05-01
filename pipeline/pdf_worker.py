"""
pipeline/pdf_worker.py

Renders a full unit study pack PDF from generated content.

Produces a single PDF per unit containing:
  - Lesson (synopsis, sections, key points, learning objectives)
  - All quiz sets (questions, options, correct answers, explanations)
  - Tutorial (sections, examples, practice questions, common mistakes)
  - Experiment (materials, safety, steps, reflection questions) — has_lab only

Uses WeasyPrint to render an HTML+CSS Jinja2 template to PDF.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML

log = logging.getLogger("pipeline.pdf_worker")

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)

_MD_EXTENSIONS = ["tables", "fenced_code", "nl2br"]


def _md(text: str) -> Markup:
    """Convert markdown text to safe HTML markup for Jinja2."""
    if not text:
        return Markup("")
    return Markup(md_lib.markdown(str(text), extensions=_MD_EXTENSIONS))


def generate_pdf(
    unit_id: str,
    unit_title: str,
    subject: str,
    curriculum_id: str,
    generated_content: dict[str, Any],
    output_path: str,
    lang: str = "en",
) -> None:
    """
    Render a study pack PDF for a single unit.

    Args:
        unit_id:           e.g. "CCA-D1-001"
        unit_title:        display title from the curriculum JSON
        subject:           subject name e.g. "Agentic Architecture & Orchestration"
        curriculum_id:     e.g. "cert-architect-foundations-2026"
        generated_content: dict with keys "lesson", "quiz_1".."quiz_N",
                           "tutorial", "experiment"
        output_path:       absolute path to write the PDF
        lang:              ISO 639-1 code e.g. "en"
    """
    quiz_sets = []
    n = 1
    while f"quiz_{n}" in generated_content:
        quiz_sets.append((n, generated_content[f"quiz_{n}"]))
        n += 1

    template = _jinja_env.get_template("unit_study_pack.html")
    html_str = template.render(
        unit_id=unit_id,
        unit_title=unit_title,
        subject=subject,
        curriculum_id=curriculum_id,
        lang=lang,
        generated_at=datetime.now(tz=timezone.utc).strftime("%B %d, %Y"),
        lesson=generated_content.get("lesson"),
        quiz_sets=quiz_sets,
        tutorial=generated_content.get("tutorial"),
        experiment=generated_content.get("experiment"),
        md=_md,
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    HTML(string=html_str, base_url=_TEMPLATE_DIR).write_pdf(output_path)
    log.info("pdf_written path=%s", output_path)
