import type { LessonContent } from "@/lib/types/api";
import { CheckCircle2 } from "lucide-react";

interface LessonRendererProps {
  lesson: LessonContent;
}

export function LessonRenderer({ lesson }: LessonRendererProps) {
  return (
    <article className="rounded-lg border border-gray-300 bg-stone-50 p-6 font-heading shadow-md">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">{lesson.title}</h1>

      {lesson.sections.map((section, i) => (
        <section key={i} className="mb-8">
          <h2 className="mb-3 text-lg font-semibold text-gray-800">
            {section.heading}
          </h2>
          <p className="leading-relaxed whitespace-pre-wrap text-gray-700">
            {section.body}
          </p>
        </section>
      ))}

      {lesson.key_points.length > 0 && (
        <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-4 shadow-sm">
          <h3 className="mb-3 font-semibold text-blue-800">Key Points</h3>
          <ul className="space-y-2">
            {lesson.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-blue-900">
                <CheckCircle2
                  className="mt-0.5 h-4 w-4 shrink-0 text-blue-500"
                  aria-hidden="true"
                />
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
