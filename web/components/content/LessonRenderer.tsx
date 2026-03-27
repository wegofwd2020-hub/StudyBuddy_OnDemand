import type { LessonContent } from "@/lib/types/api";
import { CheckCircle2 } from "lucide-react";

interface LessonRendererProps {
  lesson: LessonContent;
}

export function LessonRenderer({ lesson }: LessonRendererProps) {
  return (
    <article className="prose prose-gray max-w-none">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{lesson.title}</h1>

      {lesson.sections.map((section, i) => (
        <section key={i} className="mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">{section.heading}</h2>
          <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">{section.body}</p>
        </section>
      ))}

      {lesson.key_points.length > 0 && (
        <div className="mt-8 rounded-lg border border-blue-100 bg-blue-50 p-4">
          <h3 className="font-semibold text-blue-800 mb-3">Key Points</h3>
          <ul className="space-y-2">
            {lesson.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-blue-700">
                <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-blue-500" />
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
