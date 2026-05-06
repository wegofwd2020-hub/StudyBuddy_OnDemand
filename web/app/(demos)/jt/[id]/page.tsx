import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { ScenarioVideoPlayer } from "@/components/content/ScenarioVideoPlayer";
import { getScenarioById, SCENARIO_LIST } from "@/data/scenarios";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  return SCENARIO_LIST.map((s) => ({ id: s.id }));
}

export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  const scenario = getScenarioById(id);
  return {
    title: scenario ? `${scenario.title} — JT Use Case` : "JT Use Case",
    description: "Scenario-based compliance training",
  };
}

export default async function JTScenarioPage({ params }: PageProps) {
  const { id } = await params;
  const scenario = getScenarioById(id);
  if (!scenario) notFound();

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="mx-auto max-w-2xl">
        <Link
          href="/jt"
          className="mb-6 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          <ChevronLeft className="h-4 w-4" /> All use cases
        </Link>

        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900">{scenario.title}</h1>
          <p className="mt-3 text-gray-500">
            Scenario-based compliance training — watch the conversation, then answer the compliance question.
          </p>
        </div>

        <ScenarioVideoPlayer scenario={scenario} />

        <p className="mt-10 text-center text-xs text-gray-400">
          Scenario authored by John Thomas · StudyBuddy OnDemand
        </p>
      </div>
    </div>
  );
}
