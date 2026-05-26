"use client";

import { useState } from "react";
import { Plus, Trash2, Save } from "lucide-react";
import type { StructuredTOC } from "@/lib/api/authoring";

/**
 * Editable subjects → units table for the Authoring Studio (requirement c).
 * Each unit row has an editable title, subtopics (comma-separated), and
 * prerequisites (comma-separated). Subjects/units can be added or removed.
 */
export function StructuredTocEditor({
  value,
  saving,
  onSave,
}: {
  value: StructuredTOC;
  saving: boolean;
  onSave: (toc: StructuredTOC) => void;
}) {
  const [toc, setToc] = useState<StructuredTOC>(() => structuredClone(value));
  const [dirty, setDirty] = useState(false);

  function update(next: StructuredTOC) {
    setToc(next);
    setDirty(true);
  }

  function setUnit(
    si: number,
    ui: number,
    patch: Partial<{ title: string; subtopics: string[]; prerequisites: string[] }>,
  ) {
    const next = structuredClone(toc);
    next.subjects[si].units[ui] = { ...next.subjects[si].units[ui], ...patch };
    update(next);
  }

  function addUnit(si: number) {
    const next = structuredClone(toc);
    next.subjects[si].units.push({
      title: "New topic",
      subtopics: [],
      prerequisites: [],
    });
    update(next);
  }
  function removeUnit(si: number, ui: number) {
    const next = structuredClone(toc);
    next.subjects[si].units.splice(ui, 1);
    update(next);
  }
  function addSubject() {
    const next = structuredClone(toc);
    next.subjects.push({
      subject_label: "New subject",
      units: [{ title: "New topic", subtopics: [], prerequisites: [] }],
    });
    update(next);
  }
  function removeSubject(si: number) {
    const next = structuredClone(toc);
    next.subjects.splice(si, 1);
    update(next);
  }

  return (
    <div className="space-y-5">
      {toc.subjects.map((subject, si) => (
        <div key={si} className="rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-2">
            <input
              value={subject.subject_label}
              onChange={(e) => {
                const next = structuredClone(toc);
                next.subjects[si].subject_label = e.target.value;
                update(next);
              }}
              className="flex-1 rounded-md border border-transparent px-2 py-1 text-sm font-semibold text-gray-900 hover:border-gray-200 focus:border-indigo-500 focus:outline-none"
            />
            <button
              onClick={() => removeSubject(si)}
              title="Remove subject"
              className="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Topic</th>
                <th className="px-3 py-2 text-left font-medium">
                  Subtopics (comma-separated)
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  Prerequisites (comma-separated)
                </th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {subject.units.map((unit, ui) => (
                <tr key={ui}>
                  <td className="px-3 py-2 align-top">
                    <input
                      value={unit.title}
                      onChange={(e) => setUnit(si, ui, { title: e.target.value })}
                      className="w-full rounded-md border border-gray-200 px-2 py-1 focus:border-indigo-500 focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2 align-top">
                    <input
                      value={unit.subtopics.join(", ")}
                      onChange={(e) =>
                        setUnit(si, ui, {
                          subtopics: e.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                        })
                      }
                      className="w-full rounded-md border border-gray-200 px-2 py-1 focus:border-indigo-500 focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2 align-top">
                    <input
                      value={unit.prerequisites.join(", ")}
                      onChange={(e) =>
                        setUnit(si, ui, {
                          prerequisites: e.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                        })
                      }
                      className="w-full rounded-md border border-gray-200 px-2 py-1 focus:border-indigo-500 focus:outline-none"
                    />
                  </td>
                  <td className="px-2 py-2 align-top">
                    <button
                      onClick={() => removeUnit(si, ui)}
                      title="Remove topic"
                      className="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-3 py-2">
            <button
              onClick={() => addUnit(si)}
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:underline"
            >
              <Plus className="h-3.5 w-3.5" /> Add topic
            </button>
          </div>
        </div>
      ))}

      <div className="flex items-center justify-between">
        <button
          onClick={addSubject}
          className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:underline"
        >
          <Plus className="h-4 w-4" /> Add subject
        </button>
        <button
          disabled={!dirty || saving}
          onClick={() => onSave(toc)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save structure"}
        </button>
      </div>
    </div>
  );
}
