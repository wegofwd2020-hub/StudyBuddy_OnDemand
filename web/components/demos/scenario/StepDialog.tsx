"use client";

import { Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import type { ScenarioDraft, DialogTurn } from "./types";

interface Props {
  draft: ScenarioDraft;
  onChange: (patch: Partial<ScenarioDraft>) => void;
}

const AVATAR_COLORS = [
  "bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
  "bg-rose-500", "bg-cyan-500",
];

function initials(name: string) {
  return name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "?";
}

export function StepDialog({ draft, onChange }: Props) {
  const { characters, dialog } = draft;

  function addTurn() {
    const defaultSpeaker = characters[dialog.length % Math.max(characters.length, 1)]?.id ?? "";
    onChange({
      dialog: [...dialog, { id: crypto.randomUUID(), speaker: defaultSpeaker, text: "" }],
    });
  }

  function updateTurn(idx: number, patch: Partial<DialogTurn>) {
    onChange({ dialog: dialog.map((t, i) => (i === idx ? { ...t, ...patch } : t)) });
  }

  function removeTurn(idx: number) {
    onChange({ dialog: dialog.filter((_, i) => i !== idx) });
  }

  function moveTurn(idx: number, dir: -1 | 1) {
    const next = [...dialog];
    const swap = idx + dir;
    if (swap < 0 || swap >= next.length) return;
    [next[idx], next[swap]] = [next[swap], next[idx]];
    onChange({ dialog: next });
  }

  const charColorIdx = Object.fromEntries(characters.map((c, i) => [c.id, i]));
  const charMap = Object.fromEntries(characters.map((c) => [c.id, c]));

  if (characters.length === 0) {
    return (
      <p className="text-sm text-gray-500 text-center py-6 rounded-xl border border-dashed bg-gray-50">
        Add characters in the previous step before defining the dialog.
      </p>
    );
  }

  // Estimated reading time: ~130 wpm
  const totalWords = dialog.reduce((n, t) => n + t.text.split(/\s+/).filter(Boolean).length, 0);
  const estSeconds = Math.round((totalWords / 130) * 60);

  return (
    <div className="space-y-4">
      {dialog.length > 0 && (
        <p className="text-xs text-gray-500 text-right">
          {dialog.length} turn{dialog.length !== 1 ? "s" : ""} ·{" "}
          ~{estSeconds < 60
            ? `${estSeconds}s`
            : `${Math.floor(estSeconds / 60)}m ${estSeconds % 60}s`} estimated
        </p>
      )}

      {dialog.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-6 rounded-xl border border-dashed bg-gray-50">
          No dialog turns yet. Add the first line.
        </p>
      )}

      {dialog.map((turn, idx) => {
        const colorIdx = charColorIdx[turn.speaker] ?? 0;
        const color = AVATAR_COLORS[colorIdx % AVATAR_COLORS.length];
        const char = charMap[turn.speaker];

        return (
          <div key={turn.id} className="flex gap-3 items-start">
            {/* Avatar dot */}
            <div className={`${color} flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white mt-1`}>
              {initials(char?.name ?? turn.speaker)}
            </div>

            <div className="flex-1 space-y-2">
              {/* Speaker selector */}
              <select
                value={turn.speaker}
                onChange={(e) => updateTurn(idx, { speaker: e.target.value })}
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold outline-none focus:border-indigo-500 bg-white"
              >
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.id} — {c.role_label || "No role"}
                  </option>
                ))}
              </select>

              {/* Dialog text */}
              <textarea
                value={turn.text}
                onChange={(e) => updateTurn(idx, { text: e.target.value })}
                placeholder="What does this character say?"
                rows={3}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 resize-none"
              />
            </div>

            {/* Controls */}
            <div className="flex flex-col gap-1 mt-1">
              <button type="button" onClick={() => moveTurn(idx, -1)} disabled={idx === 0}
                className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-20">
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
              <button type="button" onClick={() => moveTurn(idx, 1)} disabled={idx === dialog.length - 1}
                className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-20">
                <ArrowDown className="h-3.5 w-3.5" />
              </button>
              <button type="button" onClick={() => removeTurn(idx)}
                className="rounded p-1 text-gray-400 hover:text-red-500">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        );
      })}

      <button
        type="button"
        onClick={addTurn}
        className="flex items-center gap-2 rounded-lg border-2 border-dashed border-indigo-300 px-5 py-3 text-sm font-semibold text-indigo-600 hover:border-indigo-500 hover:bg-indigo-50 transition-colors"
      >
        <Plus className="h-4 w-4" />
        Add Dialog Turn
      </button>
    </div>
  );
}
