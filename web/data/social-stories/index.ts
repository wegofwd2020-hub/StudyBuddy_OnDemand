import anxiety001 from "./anxiety_001_en.json";
import acceptingNo from "./accepting_no_en.json";
import type { ScenarioWithClips } from "@/components/content/ScenarioVideoPlayer";

export interface SocialStoryMetrics {
  authoring_time_min: number;
  llm_cost_usd: number;
  image_cost_usd: number;
  video_cost_usd: number;
  ship_status: "live" | "preview";
}

export interface SocialStoryListItem {
  id: string;
  title: string;
  domain: string;
  language: string;
  description: string;
  audience: string;
  metrics: SocialStoryMetrics;
}

export function totalCost(m: SocialStoryMetrics): number {
  return m.llm_cost_usd + m.image_cost_usd + m.video_cost_usd;
}

export const STORY_REGISTRY: Record<string, ScenarioWithClips> = {
  "anxiety-001": anxiety001 as ScenarioWithClips,
  "accepting-no": acceptingNo as ScenarioWithClips,
};

export const STORY_LIST: SocialStoryListItem[] = [
  {
    id: "anxiety-001",
    title: "Handling unexpected change",
    domain: "Anxiety / Coping",
    language: "en",
    audience: "Adult, autism context",
    description:
      "An adult first-person social story about anxiety when a plan changes unexpectedly — names the feeling, teaches a concrete grounding-and-breathing protocol, ends with a past-success affirmation.",
    metrics: {
      authoring_time_min: 5,
      llm_cost_usd: 2.0,
      image_cost_usd: 0,
      video_cost_usd: 3.75,
      ship_status: "live",
    },
  },
  {
    id: "accepting-no",
    title: "Accepting No",
    domain: "Social Skills / Self-regulation",
    language: "en",
    audience: "Child / family — adapted from Autism Behavior Services Inc.",
    description:
      'Daniel struggles to hear the word "no" — at the supermarket, at the diner, with Dad. The ABSI narrator teaches that "no isn\'t forever," deep breathing, and counting down. In the resolution, Daniel applies the tool and proposes earning his own money for the toy.',
    metrics: {
      authoring_time_min: 10,
      llm_cost_usd: 4.0,
      image_cost_usd: 0,
      video_cost_usd: 15.0,
      ship_status: "live",
    },
  },
];

export function getStoryById(id: string): ScenarioWithClips | undefined {
  return STORY_REGISTRY[id];
}
