import contractLaw001 from "./contract_law_001_en.json";
import inOfficeBehavior from "./in_office_behavior_en.json";
import intermediaryBribery from "./intermediary_bribery_en.json";
import type { ScenarioWithClips } from "@/components/content/ScenarioVideoPlayer";

export interface ScenarioMetrics {
  authoring_time_min: number; // broker wall-clock minutes from spec → shipped
  llm_cost_usd: number; // estimated Claude-token cost for broker authoring
  image_cost_usd: number; // image-gen API cost for stylized portraits (0 if default photo used)
  video_cost_usd: number; // D-ID /talks credits cost (0 if no videos yet)
  ship_status: "live" | "preview"; // 'live' = videos rendered; 'preview' = text-only fallback
}

export interface ScenarioListItem {
  id: string;
  title: string;
  domain: string;
  language: string;
  description: string;
  metrics: ScenarioMetrics;
}

export function totalCost(m: ScenarioMetrics): number {
  return m.llm_cost_usd + m.image_cost_usd + m.video_cost_usd;
}

export const SCENARIO_REGISTRY: Record<string, ScenarioWithClips> = {
  "contract-law-001": contractLaw001 as ScenarioWithClips,
  "in-office-behavior": inOfficeBehavior as ScenarioWithClips,
  "intermediary-bribery": intermediaryBribery as ScenarioWithClips,
};

export const SCENARIO_LIST: ScenarioListItem[] = [
  {
    id: "contract-law-001",
    title: "Subsidiary Contract Routing — Legal or Not?",
    domain: "Contract Law / FCPA",
    language: "en",
    description:
      "A vendor sales director hears an unusual contract-routing request from a client. Watch the conversation, then decide whether the proposal is legal under US FCPA / AML rules.",
    metrics: {
      authoring_time_min: 5,
      llm_cost_usd: 3.0,
      image_cost_usd: 0,
      video_cost_usd: 3.0,
      ship_status: "live",
    },
  },
  {
    id: "in-office-behavior",
    title: "Inappropriate Workplace Talk — Code of Conduct",
    domain: "Code of Conduct",
    language: "en",
    description:
      "Two IT colleagues at SmallThings.com talk about a female coworker's dress and looks. Watch the conversation and decide whether this is acceptable office behaviour — even though no slurs or derogatory language are used.",
    metrics: {
      authoring_time_min: 5,
      llm_cost_usd: 2.0,
      image_cost_usd: 0,
      video_cost_usd: 4.0,
      ship_status: "live",
    },
  },
  {
    id: "intermediary-bribery",
    title: "Hiring a Local Fixer — Where's the Line?",
    domain: "FCPA / Anti-Bribery",
    language: "en",
    description:
      "A VP of International Sales meets with a regional consultant who promises to 'smooth things along' with a foreign government tender. Watch the conversation and decide whether the arrangement passes US FCPA scrutiny.",
    metrics: {
      authoring_time_min: 3,
      llm_cost_usd: 4.0,
      image_cost_usd: 0,
      // estimate; reconcile vs D-ID dashboard once usage settles
      video_cost_usd: 5.0,
      ship_status: "live",
    },
  },
];

export function getScenarioById(id: string): ScenarioWithClips | undefined {
  return SCENARIO_REGISTRY[id];
}
