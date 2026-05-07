#!/usr/bin/env bun
/**
 * Convert a StudyBuddy unit's content_store_data files into a single Markdown
 * document suitable for reading, archiving, or rendering to PDF via pandoc.
 *
 * Usage:
 *   bun scripts/extract_unit_to_markdown.ts \
 *     --unit-dir content_store_data/curricula/default-2026-g11-science/G11-MATH-001 \
 *     --out ~/Downloads/Sets_and_Functions.md \
 *     [--lang en] [--include-quizzes]
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, basename } from "node:path";

type Section = {
  section_id: string;
  title: string;
  content: string;
  examples?: string[];
  practice_question?: string;
};

type Lesson = {
  unit_id: string;
  topic: string;
  synopsis: string;
  key_concepts?: string[];
  learning_objectives?: string[];
  reading_level?: string;
  estimated_duration_minutes?: number;
};

type Tutorial = {
  unit_id: string;
  title: string;
  sections: Section[];
  common_mistakes?: string[];
};

type QuizOption = { option_id: string; text: string };
type QuizQuestion = {
  question_id: string;
  question_text: string;
  options?: QuizOption[];
  correct_option?: string;
  explanation?: string;
  difficulty?: string;
};
type QuizSet = {
  unit_id: string;
  set_number: number;
  questions: QuizQuestion[];
};

function parseArgs(): {
  unitDir: string;
  out: string;
  lang: string;
  includeQuizzes: boolean;
} {
  const args = Bun.argv.slice(2);
  const get = (k: string) => {
    const i = args.indexOf(k);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const unitDir = get("--unit-dir");
  const out = get("--out");
  if (!unitDir || !out) {
    console.error(
      "Usage: bun extract_unit_to_markdown.ts --unit-dir <path> --out <md> [--lang en] [--include-quizzes]",
    );
    process.exit(2);
  }
  return {
    unitDir,
    out,
    lang: get("--lang") ?? "en",
    includeQuizzes: args.includes("--include-quizzes"),
  };
}

function readJson<T>(path: string): T | null {
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf-8")) as T;
}

function renderLesson(lesson: Lesson): string {
  const lines: string[] = [];
  lines.push(`# ${lesson.topic}\n`);
  lines.push(`> Unit \`${lesson.unit_id}\``);
  if (lesson.reading_level) lines.push(`> Reading level: ${lesson.reading_level}`);
  if (lesson.estimated_duration_minutes)
    lines.push(`> Estimated duration: ${lesson.estimated_duration_minutes} min`);
  lines.push("");
  lines.push("## Synopsis\n");
  lines.push(lesson.synopsis);
  lines.push("");
  if (lesson.key_concepts?.length) {
    lines.push("## Key Concepts\n");
    for (const c of lesson.key_concepts) lines.push(`- ${c}`);
    lines.push("");
  }
  if (lesson.learning_objectives?.length) {
    lines.push("## Learning Objectives\n");
    for (const o of lesson.learning_objectives) lines.push(`- ${o}`);
    lines.push("");
  }
  return lines.join("\n");
}

function renderTutorial(tutorial: Tutorial): string {
  const lines: string[] = [];
  lines.push(`---\n`);
  lines.push(`# ${tutorial.title}\n`);
  for (const section of tutorial.sections) {
    lines.push(`## ${section.title}\n`);
    lines.push(section.content);
    lines.push("");
    if (section.examples?.length) {
      for (const ex of section.examples) {
        lines.push(ex);
        lines.push("");
      }
    }
    if (section.practice_question) {
      lines.push(`### Practice Question\n`);
      lines.push(section.practice_question);
      lines.push("");
    }
    lines.push("");
  }
  if (tutorial.common_mistakes?.length) {
    lines.push(`## Common Mistakes\n`);
    for (const m of tutorial.common_mistakes) lines.push(`- ${m}`);
    lines.push("");
  }
  return lines.join("\n");
}

function renderQuizSet(quiz: QuizSet): string {
  const lines: string[] = [];
  lines.push(`---\n`);
  lines.push(`# Quiz Set ${quiz.set_number}\n`);
  for (const q of quiz.questions) {
    lines.push(`### ${q.question_id}. ${q.question_text}`);
    if (q.difficulty) lines.push(`*Difficulty: ${q.difficulty}*`);
    lines.push("");
    if (q.options?.length) {
      for (const opt of q.options) {
        const marker = opt.option_id === q.correct_option ? "**(correct)**" : "";
        lines.push(`- **${opt.option_id})** ${opt.text} ${marker}`.trim());
      }
      lines.push("");
    }
    if (q.explanation) {
      lines.push(`**Explanation:** ${q.explanation}`);
      lines.push("");
    }
  }
  return lines.join("\n");
}

function main() {
  const { unitDir, out, lang, includeQuizzes } = parseArgs();

  const lesson = readJson<Lesson>(join(unitDir, `lesson_${lang}.json`));
  const tutorial = readJson<Tutorial>(join(unitDir, `tutorial_${lang}.json`));
  if (!lesson || !tutorial) {
    console.error(`Missing lesson or tutorial JSON in ${unitDir}`);
    process.exit(1);
  }

  const parts: string[] = [];
  parts.push(renderLesson(lesson));
  parts.push(renderTutorial(tutorial));

  if (includeQuizzes) {
    for (let n = 1; n <= 3; n++) {
      const quiz = readJson<QuizSet>(join(unitDir, `quiz_set_${n}_${lang}.json`));
      if (quiz) parts.push(renderQuizSet(quiz));
    }
  }

  const md = parts.join("\n");
  const expandedOut = out.replace(/^~(?=\/)/, process.env.HOME ?? "~");
  writeFileSync(expandedOut, md);
  console.log(
    `Wrote ${md.length.toLocaleString()} chars to ${expandedOut} (source: ${basename(unitDir)})`,
  );
}

main();
