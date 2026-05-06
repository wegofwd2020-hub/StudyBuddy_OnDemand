"use client";

import { useState, useEffect } from "react";

const PASSPHRASE = "jt2026";
const SESSION_KEY = "jt_access";

export default function JTLayout({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    setUnlocked(sessionStorage.getItem(SESSION_KEY) === "1");
    setHydrated(true);
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

  if (!hydrated) return null;

  if (!unlocked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border bg-white p-8 shadow-lg">
          <h1 className="mb-1 text-xl font-bold text-gray-900">JT Use Cases</h1>
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

  return <>{children}</>;
}
