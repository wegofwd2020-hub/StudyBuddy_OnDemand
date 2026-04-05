"use client";

/**
 * web/components/help/MindMap.tsx
 *
 * Client-side Mermaid mindmap renderer.
 * Mermaid must be imported dynamically — it references `window` internally
 * and cannot be imported in SSR context.
 */

import { useEffect, useId, useRef, useState } from "react";

interface MindMapProps {
  diagram: string;
  /** Tailwind class applied to the wrapper for sizing */
  className?: string;
}

export function MindMap({ diagram, className = "" }: MindMapProps) {
  const id = useId().replace(/:/g, "");
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;

        mermaid.initialize({
          startOnLoad: false,
          theme: "default",
          mindmap: {
            padding: 16,
          },
          themeVariables: {
            // Keep colors accessible — ensure contrast ≥4.5:1
            primaryColor: "#e0e7ff",
            primaryTextColor: "#1e1b4b",
            primaryBorderColor: "#6366f1",
            lineColor: "#6366f1",
            secondaryColor: "#f0fdf4",
            tertiaryColor: "#fefce8",
          },
        });

        const { svg } = await mermaid.render(`mm-${id}`, diagram);

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          // Make SVG responsive
          const svgEl = containerRef.current.querySelector("svg");
          if (svgEl) {
            svgEl.setAttribute("width", "100%");
            svgEl.removeAttribute("height");
            svgEl.style.maxWidth = "100%";
          }
          setRendered(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Diagram render failed");
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [diagram, id]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        <p className="font-medium">Diagram could not be rendered</p>
        <pre className="mt-1 overflow-auto text-xs">{error}</pre>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {!rendered && (
        <div className="flex h-48 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      )}
      <div
        ref={containerRef}
        className={rendered ? "block" : "hidden"}
        aria-label="Mind map diagram"
      />
    </div>
  );
}
