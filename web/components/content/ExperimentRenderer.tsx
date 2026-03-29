import type { ExperimentContent } from "@/lib/types/api";
import { useTranslations } from "next-intl";
import { FlaskConical, AlertTriangle, CheckCircle2, Package } from "lucide-react";

interface ExperimentRendererProps {
  experiment: ExperimentContent;
}

export function ExperimentRenderer({ experiment }: ExperimentRendererProps) {
  const t = useTranslations("experiment_screen");

  return (
    <article className="space-y-8">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50">
          <FlaskConical className="h-5 w-5 text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{experiment.title}</h1>
      </div>

      {/* Materials */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-800">
          <Package className="h-4 w-4" />
          {t("materials_heading")}
        </h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {experiment.materials.map((m, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />
              {m}
            </li>
          ))}
        </ul>
      </section>

      {/* Safety notes */}
      {experiment.safety_notes.length > 0 && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {t("safety_heading")}
          </h2>
          <ul className="space-y-1">
            {experiment.safety_notes.map((note, i) => (
              <li key={i} className="text-sm text-amber-700">
                {note}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Steps */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">{t("steps_heading")}</h2>
        <ol className="space-y-4">
          {experiment.steps.map((step) => (
            <li key={step.step} className="flex gap-4">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-purple-600 text-xs font-bold text-white">
                {step.step}
              </div>
              <p className="pt-0.5 text-sm leading-relaxed text-gray-600">
                {step.instruction}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* Expected outcome */}
      {experiment.expected_outcome && (
        <section className="rounded-lg border border-green-100 bg-green-50 p-4">
          <h2 className="mb-1 flex items-center gap-2 font-semibold text-green-800">
            <CheckCircle2 className="h-4 w-4" />
            {t("expected_outcome_heading")}
          </h2>
          <p className="text-sm text-green-700">{experiment.expected_outcome}</p>
        </section>
      )}
    </article>
  );
}
