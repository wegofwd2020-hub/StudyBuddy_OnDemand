import type { TutorialContent } from "@/lib/types/api";

interface TutorialRendererProps {
  tutorial: TutorialContent;
}

export function TutorialRenderer({ tutorial }: TutorialRendererProps) {
  return (
    <article className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{tutorial.title}</h1>
        <p className="mt-2 text-gray-500">{tutorial.objective}</p>
      </div>

      <ol className="space-y-6">
        {tutorial.steps.map((step) => (
          <li key={step.step} className="flex gap-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
              {step.step}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{step.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-gray-600">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>

      {tutorial.summary && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
          <h3 className="mb-1 font-semibold text-blue-800">Summary</h3>
          <p className="text-sm text-blue-700">{tutorial.summary}</p>
        </div>
      )}
    </article>
  );
}
