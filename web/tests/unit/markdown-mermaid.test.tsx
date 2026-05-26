/**
 * Unit test — SBMarkdown renders ```mermaid fenced blocks as a diagram
 * container (Authoring Studio diagram_emphasis output), not as raw code.
 *
 * Run with:
 *   npm test -- markdown-mermaid
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SBMarkdown } from "@/components/content/Markdown";

// Mermaid is dynamically imported by MermaidDiagram; stub it so the test is
// deterministic in jsdom (real mermaid needs a full browser layout engine).
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({ svg: "<svg aria-hidden='true'></svg>" }),
  },
}));

describe("SBMarkdown mermaid rendering", () => {
  it("routes a mermaid fenced block to the diagram container, not <pre><code>", async () => {
    const md = "```mermaid\ngraph TD; A-->B;\n```";
    render(<SBMarkdown>{md}</SBMarkdown>);

    expect(await screen.findByTestId("mermaid-diagram")).toBeInTheDocument();
    // The raw diagram source must not be shown as code text.
    expect(screen.queryByText("graph TD; A-->B;")).not.toBeInTheDocument();
  });

  it("still renders a non-mermaid fenced block as code", () => {
    const md = "```python\nprint('hi')\n```";
    render(<SBMarkdown>{md}</SBMarkdown>);
    expect(screen.queryByTestId("mermaid-diagram")).not.toBeInTheDocument();
    expect(screen.getByText("print('hi')")).toBeInTheDocument();
  });
});
