"use client";

import { useState, useEffect } from "react";
import { ScenarioBuilder } from "@/components/demos/scenario/ScenarioBuilder";

const PASSPHRASE = "jt2026";
const SESSION_KEY = "jt_access";

export function ScenarioBuilderGated() {
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
    } else {
      setError(true);
      setInput("");
    }
  }

  if (!unlocked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border bg-white p-8 shadow-lg">
          <h1 className="mb-1 text-xl font-bold text-gray-900">Scenario Builder</h1>
          <p className="mb-6 text-sm text-gray-500">Enter the access code to continue.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="password"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setError(false);
              }}
              placeholder="Access code"
              autoFocus
              className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            />
            {error && <p className="text-xs text-red-500">Incorrect code — try again.</p>}
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
    <div className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">New Scenario</h1>
          <p className="mt-1 text-sm text-gray-500">
            Define characters, dialog, and quiz questions. Export as JSON to trigger
            avatar generation.
          </p>
        </div>
        <ScenarioBuilder />
      </div>
    </div>
  );
}
