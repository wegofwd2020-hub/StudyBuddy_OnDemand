import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { ScenarioVideoPlayer } from "@/components/content/ScenarioVideoPlayer";
import { getStoryById, STORY_LIST } from "@/data/social-stories";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  return STORY_LIST.map((s) => ({ id: s.id }));
}

export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  const story = getStoryById(id);
  return {
    title: story ? `${story.title} — Social Story` : "Social Story",
    description: "Carol Gray-style social story",
  };
}

export default async function SocialStoryPage({ params }: PageProps) {
  const { id } = await params;
  const story = getStoryById(id);
  if (!story) notFound();

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="mx-auto max-w-2xl">
        <Link
          href="/stories"
          className="mb-6 inline-flex items-center gap-1 text-sm font-medium text-emerald-600 hover:text-emerald-700"
        >
          <ChevronLeft className="h-4 w-4" /> All social stories
        </Link>

        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900">{story.title}</h1>
          <p className="mt-3 text-gray-500">
            Watch the story end-to-end. No quiz — just the narrative.
          </p>
        </div>

        <ScenarioVideoPlayer scenario={story} />

        <p className="mt-10 text-center text-xs text-gray-400">
          Social-story prototype · StudyBuddy OnDemand
        </p>
      </div>
    </div>
  );
}
