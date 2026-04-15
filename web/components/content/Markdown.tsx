"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { cn } from "@/lib/utils";

/**
 * SBMarkdown — the canonical prose renderer for AI-generated content.
 *
 * Epic 11 C-3: consolidates the four inline <ReactMarkdown> copies across
 * lesson / tutorial / quiz / experiment viewers into a single component,
 * adds remark-math + rehype-katex for typeset formulae, and normalises
 * table / code / blockquote styling.
 *
 * Styling conventions applied:
 *   - Tables: zebra-striped rows, bold header, horizontal-scroll wrapper
 *     (so wide Balance Sheets don't break on narrow viewports).
 *   - Numeric table cells: font-mono + tabular-nums for decimal alignment.
 *     The pipeline emits GFM alignment markers (|---:|) per Q4; those are
 *     honoured natively by remark-gfm.
 *   - Inline code: indigo accent on a light gray pill.
 *   - Fenced code: gray block with horizontal scroll.
 *   - Blockquote: left-border indent, italic — the attribution line
 *     (when present as em-dashed suffix, per C-9) inherits the same style.
 *   - Math: KaTeX CSS is imported globally from globals.css.
 */
export function SBMarkdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <div className={cn("text-sm text-gray-700", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gray-100 font-semibold text-gray-600">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-gray-100">{children}</tbody>
          ),
          tr: ({ children }) => <tr className="even:bg-gray-50">{children}</tr>,
          th: ({ children, style }) => (
            <th
              className={cn(
                "px-3 py-2",
                style?.textAlign === "right" && "text-right",
                style?.textAlign === "center" && "text-center",
                (!style?.textAlign || style.textAlign === "left") && "text-left",
              )}
              style={style}
            >
              {children}
            </th>
          ),
          td: ({ children, style }) => (
            <td
              className={cn(
                "px-3 py-2",
                style?.textAlign === "right" && "text-right font-mono tabular-nums",
                style?.textAlign === "center" && "text-center",
                (!style?.textAlign || style.textAlign === "left") && "text-left",
              )}
              style={style}
            >
              {children}
            </td>
          ),
          code: ({ children, className: cname }) => {
            const isBlock = cname?.includes("language-");
            if (isBlock) {
              return (
                <pre className="my-2 overflow-x-auto rounded-md bg-gray-50 p-3 font-mono text-xs text-gray-800">
                  <code>{children}</code>
                </pre>
              );
            }
            return (
              <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs text-indigo-700">
                {children}
              </code>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="my-3 border-l-4 border-indigo-200 bg-indigo-50/50 px-4 py-2 text-sm italic text-gray-700">
              {children}
            </blockquote>
          ),
          p: ({ children }) => (
            <p className="mb-2 leading-relaxed last:mb-0">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="mb-2 list-disc space-y-1 pl-4">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 list-decimal space-y-1 pl-4">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">{children}</strong>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
