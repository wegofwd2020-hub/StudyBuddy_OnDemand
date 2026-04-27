import { ScenarioBuilder } from "@/components/scenario/ScenarioBuilder";

export const metadata = {
  title: "New Scenario — StudyBuddy Admin",
};

export default function NewScenarioPage() {
  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">New Scenario</h1>
        <p className="mt-1 text-sm text-gray-500">
          Define characters, dialog, and quiz questions. Export as JSON to trigger avatar generation.
        </p>
      </div>
      <ScenarioBuilder />
    </div>
  );
}
