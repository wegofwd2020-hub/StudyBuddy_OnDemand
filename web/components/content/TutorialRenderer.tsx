"use client";

import { useMemo, useState } from "react";
import { ChevronDown, AlertTriangle, Lightbulb, HelpCircle } from "lucide-react";
import { SBMarkdown } from "@/components/content/Markdown";
import { VisualSlot } from "@/components/content/VisualSlot";
import { cn } from "@/lib/utils";
import type { TutorialContent, TutorialSection } from "@/lib/types/api";

interface TutorialRendererProps {
  tutorial: TutorialContent;
}

export function TutorialRenderer({ tutorial }: TutorialRendererProps) {
  const allIds = useMemo(
    () => tutorial.sections.map((s) => s.section_id),
    [tutorial.sections],
  );
  const [openIds, setOpenIds] = useState<Set<string>>(
    () => new Set(allIds.length > 0 ? [allIds[0]] : []),
  );

  function toggle(id: string) {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const allOpen = openIds.size === allIds.length;
  const noneOpen = openIds.size === 0;

  return (
    <article className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">{tutorial.title}</h1>
        {allIds.length > 1 && (
          <button
            type="button"
            onClick={() =>
              setOpenIds(allOpen ? new Set() : new Set(allIds))
            }
            className="shrink-0 rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
          >
            {allOpen ? "Collapse all" : noneOpen ? "Expand all" : "Expand all"}
          </button>
        )}
      </div>

      <ol role="list" className="space-y-3">
        {tutorial.sections.map((section) => (
          <SectionDisclosure
            key={section.section_id}
            section={section}
            isOpen={openIds.has(section.section_id)}
            onToggle={() => toggle(section.section_id)}
          />
        ))}
      </ol>

      {tutorial.common_mistakes.length > 0 && (
        <aside className="rounded-lg border border-amber-300 bg-amber-50 p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-amber-800">Common mistakes</h2>
          </div>
          <ul className="list-disc space-y-1 pl-5 font-heading text-sm text-amber-900">
            {tutorial.common_mistakes.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </aside>
      )}
    </article>
  );
}

function SectionDisclosure({
  section,
  isOpen,
  onToggle,
}: {
  section: TutorialSection;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const panelId = `tut-panel-${section.section_id}`;
  const buttonId = `tut-trigger-${section.section_id}`;
  return (
    <li className="overflow-hidden rounded-lg border border-gray-300 bg-stone-50 shadow-md">
      <button
        type="button"
        id={buttonId}
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
      >
        <h3 className="text-sm font-semibold text-gray-900 sm:text-base">
          {section.title}
        </h3>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-gray-500 transition-transform duration-150 motion-reduce:transition-none",
            isOpen && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-labelledby={buttonId}
          className="border-t border-gray-200 bg-stone-50 px-4 py-4 font-heading"
        >
          <div className="prose prose-sm max-w-none font-heading text-gray-800">
            <SBMarkdown className="font-heading text-gray-800">
              {section.content}
            </SBMarkdown>
          </div>

          <VisualSlot visuals={section.visuals} />

          {section.examples.length > 0 && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 font-heading">
              <div className="mb-2 flex items-center gap-2">
                <Lightbulb
                  className="h-3.5 w-3.5 text-blue-600"
                  aria-hidden="true"
                />
                <h4 className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                  Examples
                </h4>
              </div>
              <ul className="list-disc space-y-2 pl-5 text-sm text-blue-900">
                {section.examples.map((ex, i) => (
                  <li key={i}>
                    <SBMarkdown className="font-heading text-blue-900">
                      {ex}
                    </SBMarkdown>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {section.practice_question && (
            <div className="mt-4 rounded-md border border-purple-200 bg-purple-50 p-3 font-heading">
              <div className="mb-2 flex items-center gap-2">
                <HelpCircle
                  className="h-3.5 w-3.5 text-purple-600"
                  aria-hidden="true"
                />
                <h4 className="text-xs font-semibold uppercase tracking-wide text-purple-700">
                  Practice question
                </h4>
              </div>
              <div className="prose prose-sm max-w-none font-heading text-purple-900">
                <SBMarkdown className="font-heading text-purple-900">
                  {section.practice_question}
                </SBMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
