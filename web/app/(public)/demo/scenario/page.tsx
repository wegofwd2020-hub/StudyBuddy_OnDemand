import { ScenarioVideoPlayer } from "@/components/content/ScenarioVideoPlayer";
import contractLaw001 from "@/data/scenarios/contract_law_001_en.json";
import type { ScenarioWithClips } from "@/components/content/ScenarioVideoPlayer";

export const metadata = {
  title: "Scenario Training Demo — StudyBuddy",
  description: "Interactive scenario-based compliance training powered by AI",
};

export default function ScenarioDemoPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Page header */}
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900">StudyBuddy — Scenario Training</h1>
          <p className="mt-3 text-gray-500">
            Corporate compliance training delivered as interactive animated scenarios.
            Watch the conversation unfold, then test your knowledge.
          </p>
        </div>

        {/* Player */}
        <ScenarioVideoPlayer scenario={contractLaw001 as ScenarioWithClips} />

        {/* Footer note */}
        <p className="mt-10 text-center text-xs text-gray-400">
          Scenario authored by John Thomas · Demo build · StudyBuddy OnDemand
        </p>
      </div>
    </div>
  );
}
