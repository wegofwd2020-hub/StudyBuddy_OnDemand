import Link from "next/link";
import { STORY_LIST, totalCost } from "@/data/social-stories";

export const metadata = {
  title: "Social Stories — StudyBuddy",
  description: "Carol Gray-style social stories for self-regulation and anxiety coping",
};

export default function StoriesLandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="mx-auto max-w-2xl">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Social Stories</h1>
          <p className="mt-3 text-gray-500">
            Carol Gray-style stories for self-regulation and anxiety coping — pick a story
            to play.
          </p>
        </div>

        <ul className="space-y-4">
          {STORY_LIST.map((s, idx) => {
            const m = s.metrics;
            const total = totalCost(m);
            const isPreview = m.ship_status === "preview";
            return (
              <li key={s.id}>
                <Link
                  href={`/stories/${s.id}`}
                  className="block rounded-2xl border bg-white p-6 shadow-sm transition hover:border-emerald-300 hover:shadow-md"
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-semibold text-emerald-600">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-semibold text-gray-900">{s.title}</h2>
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          {s.domain}
                        </span>
                        {isPreview && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                            Preview · text only
                          </span>
                        )}
                      </div>
                      <p className="mb-1 text-xs font-medium tracking-wide text-emerald-700 uppercase">
                        Audience: {s.audience}
                      </p>
                      <p className="text-sm text-gray-500">{s.description}</p>

                      {/* Metrics row */}
                      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                        <span title="broker authoring time, wall-clock">
                          ⏱ ~{m.authoring_time_min} min build
                        </span>
                        <span aria-hidden className="text-gray-300">
                          ·
                        </span>
                        <span title="estimated total cost: LLM authoring + image generation + D-ID video">
                          💵 ~${total.toFixed(2)} total
                        </span>
                        <span aria-hidden className="text-gray-300">
                          ·
                        </span>
                        <span className="text-gray-400">
                          LLM ${m.llm_cost_usd.toFixed(2)} · img $
                          {m.image_cost_usd.toFixed(2)} · D-ID $
                          {m.video_cost_usd.toFixed(2)}
                        </span>
                      </div>

                      <p className="mt-3 text-sm font-medium text-emerald-600">
                        Play story →
                      </p>
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Aggregate row */}
        <div className="mt-6 rounded-xl border border-dashed border-gray-200 bg-white px-5 py-3 text-xs text-gray-500">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-semibold text-gray-700">Catalog so far:</span>
            <span>{STORY_LIST.length} stories</span>
            <span aria-hidden className="text-gray-300">
              ·
            </span>
            <span>
              ~{STORY_LIST.reduce((acc, s) => acc + s.metrics.authoring_time_min, 0)} min
              total build
            </span>
            <span aria-hidden className="text-gray-300">
              ·
            </span>
            <span>
              ~${STORY_LIST.reduce((acc, s) => acc + totalCost(s.metrics), 0).toFixed(2)}{" "}
              total cost
            </span>
          </div>
          <p className="mt-1 text-[11px] text-gray-400">
            Same engine as the JT use cases, no quiz. Each story preserves the Carol Gray
            <em> name → tool → affirm</em> arc. Audio includes a corner &quot;AI&quot; or
            &quot;D-iD&quot; watermark from the rendering tier.
          </p>
        </div>

        <p className="mt-10 text-center text-xs text-gray-400">
          StudyBuddy OnDemand · social-story prototypes
        </p>
      </div>
    </div>
  );
}
