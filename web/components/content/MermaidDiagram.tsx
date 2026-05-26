"use client";

/**
 * web/components/content/MermaidDiagram.tsx
 *
 * Renders a fenced ```mermaid code block (flowchart / sequence / class /
 * state diagram) as an inline SVG. Used by SBMarkdown so Authoring Studio
 * content (and any content the pipeline emits with diagram_emphasis) renders
 * diagrams instead of raw code.
 *
 * Mermaid is imported dynamically — it touches `window` and cannot be
 * imported during SSR. The wrapper div carries data-testid="mermaid-diagram"
 * and renders immediately; the SVG fills in asynchronously. On a render
 * error we show a short note (never the raw source) so a malformed diagram
 * doesn't dump code at the reader.
 */

import { useEffect, useId, useRef, useState } from "react";

export function MermaidDiagram({ chart }: { chart: string }) {
  const id = useId().replace(/:/g, "");
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "default",
          securityLevel: "strict",
          themeVariables: {
            // Keep colours accessible — contrast ≥ 4.5:1 (WCAG AA).
            primaryColor: "#e0e7ff",
            primaryTextColor: "#1e1b4b",
            primaryBorderColor: "#6366f1",
            lineColor: "#6366f1",
          },
        });
        const { svg } = await mermaid.render(`mmd-${id}`, chart);
        if (cancelled || !containerRef.current) return;
        containerRef.current.innerHTML = svg;
        const svgEl = containerRef.current.querySelector("svg");
        if (svgEl) {
          svgEl.setAttribute("width", "100%");
          svgEl.removeAttribute("height");
          svgEl.style.maxWidth = "100%";
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Diagram could not be rendered");
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  return (
    <div
      data-testid="mermaid-diagram"
      className="my-3 flex justify-center overflow-x-auto rounded-md bg-gray-50 p-3"
    >
      {error ? (
        <span className="text-sm text-gray-400 italic">Diagram unavailable</span>
      ) : (
        <div ref={containerRef} className="w-full" />
      )}
    </div>
  );
}
