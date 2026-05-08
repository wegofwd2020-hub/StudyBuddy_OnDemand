/**
 * pipeline/visual_templates/oscillations.ts
 *
 * Class-specific primitives for oscillation/wave catalogues.
 *
 * Lifted from `scripts/generate_oscillations_visuals.ts` per #343 (Wave 5
 * phase C-7). Per the G11-PHYS-010 MEMO, `superpositionPlot` is the
 * already-extracted helper representing the "stacked-three-plots" pattern
 * (wave 1 + wave 2 + sum); future work in #344 (Wave 6) will lift the
 * remaining inline patterns (sine plot, side-by-side concept comparison,
 * pendulum diagram, standing-wave modes, doppler wavefronts).
 */

import {
  ACCENT,
  ACCENT_2,
  INK,
  NEGATIVE,
  makePlot,
  polyline,
  svgWrap,
} from "./shared.ts";

/**
 * Three vertically-stacked plots showing two component waves and their
 * superposition sum at a given phase difference. Used in
 * `superposition-constructive` and `superposition-destructive` figures
 * (phase=0 vs phase=π).
 */
export function superpositionPlot(
  title: string,
  phase: number,
  name: string,
): string {
  const W = 600;
  const H = 360;
  const samples = 200;
  const w1: Array<[number, number]> = [];
  const w2: Array<[number, number]> = [];
  const sum: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const x = (i / samples) * 4;
    const a = Math.sin(x * Math.PI);
    const b = Math.sin(x * Math.PI + phase);
    w1.push([x, a]);
    w2.push([x, b]);
    sum.push([x, a + b]);
  }

  const body: string[] = [];
  body.push(
    `<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">${title}</text>`,
  );

  const plotH = 90;
  const gap = 12;
  const stacks = [
    {
      data: w1,
      color: ACCENT,
      label: "wave 1",
      yRange: [-2.4, 2.4] as [number, number],
    },
    {
      data: w2,
      color: ACCENT_2,
      label: "wave 2",
      yRange: [-2.4, 2.4] as [number, number],
    },
    {
      data: sum,
      color: NEGATIVE,
      label: "sum (superposition)",
      yRange: [-2.4, 2.4] as [number, number],
    },
  ];

  let yOffset = 40;
  for (const s of stacks) {
    body.push(`<g transform="translate(0, ${yOffset})">`);
    const p = makePlot({
      width: W,
      height: plotH,
      pad: { l: 60, r: 30, t: 12, b: 22 },
      xRange: [0, 4],
      yRange: s.yRange,
      xTicks: [0, 1, 2, 3, 4],
      yTicks: [-2, 0, 2],
      xLabel: "x",
      yLabel: "y",
    });
    body.push(...p.pieces);
    body.push(polyline(s.data, p.xToPx, p.yToPx, s.color, 2));
    body.push(
      `<text x="${W - 50}" y="${p.y0 + 12}" font="11px system-ui" font-size="11" font-weight="600" fill="${s.color}" text-anchor="end">${s.label}</text>`,
    );
    body.push(`</g>`);
    yOffset += plotH + gap;
  }

  return svgWrap(
    W,
    H,
    name,
    "Three vertically-stacked plots showing two component waves and their superposition sum.",
    body.join("\n"),
  );
}
