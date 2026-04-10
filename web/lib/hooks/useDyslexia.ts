"use client";

import { useEffect, useState } from "react";

/**
 * Shared hook for the dyslexia-friendly font toggle.
 *
 * Persists via localStorage + a cookie (cookie lets the root Server Component
 * set data-dyslexic="true" on <html> during SSR, removing the anti-flash
 * inline-script workaround).
 *
 * Keyboard shortcut: Alt+D — registered globally when the hook mounts.
 * Callers can safely mount it in multiple components; the shortcut is only
 * registered once if a top-level component (e.g. PortalHeader) mounts first.
 */
export function useDyslexia() {
  const [enabled, setEnabled] = useState(false);

  // Read from localStorage on first client render.
  useEffect(() => {
    try {
      setEnabled(localStorage.getItem("sb_dyslexic") === "1");
    } catch {
      // localStorage unavailable (e.g. private browsing with strict settings).
    }
  }, []);

  function toggle(next?: boolean) {
    const value = next !== undefined ? next : !enabled;
    setEnabled(value);
    try {
      if (value) {
        localStorage.setItem("sb_dyslexic", "1");
        document.cookie = "sb_dyslexic=1; path=/; max-age=31536000; SameSite=Lax";
        document.documentElement.setAttribute("data-dyslexic", "true");
      } else {
        localStorage.removeItem("sb_dyslexic");
        document.cookie = "sb_dyslexic=; path=/; max-age=0; SameSite=Lax";
        document.documentElement.removeAttribute("data-dyslexic");
      }
    } catch {
      // Storage unavailable — in-memory state only.
    }
  }

  return { enabled, toggle };
}
