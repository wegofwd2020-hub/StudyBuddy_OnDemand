"use client";

import { useState, useEffect } from "react";
import { ScenarioVideoPlayer } from "@/components/content/ScenarioVideoPlayer";
import contractLaw001 from "@/data/scenarios/contract_law_001_en.json";
import type { ScenarioWithClips } from "@/components/content/ScenarioVideoPlayer";

const PASSPHRASE = "jt2026";
const SESSION_KEY = "jt_access";

export function JTUseCaseGated() {
  const [unlocked, setUnlocked] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    setUnlocked(sessionStorage.getItem(SESSION_KEY) === "1");
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim().toLowerCase() === PASSPHRASE) {
      sessionStorage.setItem(SESSION_KEY, "1");
      setUnlocked(true);
      setError(false);
    } else {
      setError(true);
      setInput("");
    }
  }

  if (!unlocked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border bg-white p-8 shadow-lg">
          <h1 className="mb-1 text-xl font-bold text-gray-900">JT Use Case</h1>
          <p className="mb-6 text-sm text-gray-500">Enter the access code to continue.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="password"
              value={input}
              onChange={(e) => { setInput(e.target.value); setError(false); }}
              placeholder="Access code"
              autoFocus
              className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            />
            {error && (
              <p className="text-xs text-red-500">Incorrect code — try again.</p>
            )}
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              Continue
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="mx-auto max-w-2xl">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900">JT Use Case</h1>
          <p className="mt-3 text-gray-500">
            Scenario-based compliance training — watch the conversation, then answer the compliance question.
          </p>
        </div>

        <ScenarioVideoPlayer scenario={contractLaw001 as ScenarioWithClips} />

        <p className="mt-10 text-center text-xs text-gray-400">
          Scenario authored by John Thomas · StudyBuddy OnDemand
        </p>
      </div>
    </div>
  );
}
