"use client";

import type { ScenarioDraft, Language, Difficulty } from "./types";
import { COMPLIANCE_DOMAINS } from "./types";

interface Props {
  draft: ScenarioDraft;
  onChange: (patch: Partial<ScenarioDraft>) => void;
}

export function StepMetadata({ draft, onChange }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1">Scenario Title *</label>
        <input
          value={draft.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="e.g. Subsidiary Contract Routing"
          className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1">Short Description</label>
        <textarea
          value={draft.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="One or two sentences describing the scenario and its learning objective."
          rows={3}
          className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 resize-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Compliance Domain *</label>
          <select
            value={draft.domain}
            onChange={(e) => onChange({ domain: e.target.value })}
            className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white"
          >
            <option value="">— select domain —</option>
            {COMPLIANCE_DOMAINS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Language</label>
          <select
            value={draft.language}
            onChange={(e) => onChange({ language: e.target.value as Language })}
            className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white"
          >
            <option value="en">English</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Difficulty</label>
          <select
            value={draft.difficulty}
            onChange={(e) => onChange({ difficulty: e.target.value as Difficulty })}
            className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white"
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Target Seniority</label>
          <input
            value={draft.target_seniority}
            onChange={(e) => onChange({ target_seniority: e.target.value })}
            placeholder="e.g. Sales team, All staff, Management"
            className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
          />
        </div>
      </div>
    </div>
  );
}
