"use client";

import { Plus, Trash2 } from "lucide-react";
import type { ScenarioDraft, ScenarioCharacter } from "./types";
import { emptyCharacter, VOICES_BY_LANG, BACKGROUNDS } from "./types";

interface Props {
  draft: ScenarioDraft;
  onChange: (patch: Partial<ScenarioDraft>) => void;
}

export function StepCharacters({ draft, onChange }: Props) {
  const voices = VOICES_BY_LANG[draft.language];

  function addCharacter() {
    const next = [...draft.characters, emptyCharacter(draft.characters.length)];
    // Assign default voice by position
    next[next.length - 1].voice_id =
      voices[Math.min(next.length - 1, voices.length - 1)].id;
    onChange({ characters: next });
  }

  function updateCharacter(idx: number, patch: Partial<ScenarioCharacter>) {
    const next = draft.characters.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    onChange({ characters: next });
  }

  function removeCharacter(idx: number) {
    onChange({ characters: draft.characters.filter((_, i) => i !== idx) });
  }

  return (
    <div className="space-y-5">
      {draft.characters.length === 0 && (
        <p className="rounded-xl border border-dashed bg-gray-50 py-6 text-center text-sm text-gray-500">
          No characters yet. Add at least two to define a dialog.
        </p>
      )}

      {draft.characters.map((char, idx) => (
        <div key={char.id} className="space-y-4 rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold tracking-wide text-indigo-600 uppercase">
              Character {idx + 1} — {char.id}
            </span>
            <button
              type="button"
              onClick={() => removeCharacter(idx)}
              className="text-gray-400 hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Full Name *
              </label>
              <input
                value={char.name}
                onChange={(e) => updateCharacter(idx, { name: e.target.value })}
                placeholder="e.g. Alex Rivera"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Role / Title *
              </label>
              <input
                value={char.role_label}
                onChange={(e) => updateCharacter(idx, { role_label: e.target.value })}
                placeholder="e.g. Sales Director — Vendor"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Organisation
              </label>
              <input
                value={char.org ?? ""}
                onChange={(e) => updateCharacter(idx, { org: e.target.value })}
                placeholder="e.g. Vendor Co."
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Approx. Age
              </label>
              <input
                type="number"
                min={18}
                max={75}
                value={char.approx_age ?? ""}
                onChange={(e) =>
                  updateCharacter(idx, {
                    approx_age: Number(e.target.value) || undefined,
                  })
                }
                placeholder="e.g. 38"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Gender
              </label>
              <select
                value={char.gender}
                onChange={(e) =>
                  updateCharacter(idx, {
                    gender: e.target.value as ScenarioCharacter["gender"],
                  })
                }
                className="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="non-binary">Non-binary</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Ethnicity (optional)
              </label>
              <input
                value={char.ethnicity ?? ""}
                onChange={(e) => updateCharacter(idx, { ethnicity: e.target.value })}
                placeholder="e.g. South Asian, Hispanic, East Asian…"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Animation Style
              </label>
              <select
                value={char.animation_style}
                onChange={(e) =>
                  updateCharacter(idx, {
                    animation_style: e.target.value as "realistic" | "animated",
                  })
                }
                className="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              >
                <option value="realistic">Realistic / Photo-like</option>
                <option value="animated">Illustrated / Animated</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Voice
              </label>
              <select
                value={char.voice_id ?? ""}
                onChange={(e) => updateCharacter(idx, { voice_id: e.target.value })}
                className="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              >
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Background / Setting
              </label>
              <select
                value={char.background ?? "office"}
                onChange={(e) => updateCharacter(idx, { background: e.target.value })}
                className="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              >
                {BACKGROUNDS.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addCharacter}
        className="flex items-center gap-2 rounded-lg border-2 border-dashed border-indigo-300 px-5 py-3 text-sm font-semibold text-indigo-600 transition-colors hover:border-indigo-500 hover:bg-indigo-50"
      >
        <Plus className="h-4 w-4" />
        Add Character
      </button>
    </div>
  );
}
