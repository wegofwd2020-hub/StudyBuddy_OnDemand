import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 7 — chlorophyll absorption-spectrum reveal.
 *
 * Mid-scene "zoom in": the lesson page steps aside and a stylised
 * absorption-spectrum chart appears. X-axis = wavelength (400-700 nm),
 * Y-axis = absorbance. A coloured visible-light bar runs along the
 * X-axis; the chlorophyll absorbance curve reveals progressively
 * (left → right). Two annotations land at the red and blue peaks; a
 * green callout in the trough explains "this is what we see".
 */
const SPECTRUM_PALETTE = {
  bg: "#ffffff",
  ink: "#111827",
  axis: "#94a3b8",
  curve: PAI_THEME.colors.accent,
  red: "#dc2626",
  blue: "#2563eb",
  green: "#16a34a",
} as const;

// Chart geometry
const CHART_X = 240;
const CHART_Y = 250;
const CHART_W = 1440;
const CHART_H = 480;
const X_MIN_NM = 400;
const X_MAX_NM = 700;

function nmToX(nm: number): number {
  return CHART_X + ((nm - X_MIN_NM) / (X_MAX_NM - X_MIN_NM)) * CHART_W;
}

// Wavelength → CSS colour for the visible-light bar
function wavelengthColor(nm: number): string {
  if (nm < 440) return "#7e22ce"; // violet
  if (nm < 490) return "#1d4ed8"; // blue
  if (nm < 510) return "#0d9488"; // teal
  if (nm < 565) return "#16a34a"; // green
  if (nm < 590) return "#eab308"; // yellow
  if (nm < 625) return "#ea580c"; // orange
  return "#dc2626"; // red
}

// Stylised chlorophyll a + b combined absorption (Y in [0..1]):
// peaks at ~440 nm and ~660 nm, deep trough at ~550 nm.
function chlorophyllAbsorbance(nm: number): number {
  const peakBlue = Math.exp(-Math.pow((nm - 440) / 22, 2));
  const peakRed = Math.exp(-Math.pow((nm - 660) / 22, 2));
  const baseline = 0.10;
  const trough = 0.04 * Math.exp(-Math.pow((nm - 550) / 25, 2));
  const total = baseline + 0.95 * peakBlue + 0.90 * peakRed - trough;
  return Math.max(0, Math.min(1, total));
}

function curvePoint(nm: number): { x: number; y: number } {
  const a = chlorophyllAbsorbance(nm);
  return { x: nmToX(nm), y: CHART_Y + CHART_H - a * (CHART_H - 40) };
}

export const Slide07_PigmentSpectrum: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgFade = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  // Curve reveals from left to right between frames 60 and 240
  const revealNm = interpolate(frame, [60, 240], [X_MIN_NM, X_MAX_NM], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const blueLabelOpacity = interpolate(frame, [180, 220], [0, 1], { extrapolateRight: "clamp" });
  const redLabelOpacity = interpolate(frame, [240, 280], [0, 1], { extrapolateRight: "clamp" });
  const greenCalloutOpacity = interpolate(frame, [320, 360], [0, 1], { extrapolateRight: "clamp" });

  // Sample the curve up to the revealed wavelength
  const sampleStep = 4; // every 4 nm
  const points: Array<{ x: number; y: number }> = [];
  for (let nm = X_MIN_NM; nm <= revealNm; nm += sampleStep) {
    points.push(curvePoint(nm));
  }
  const pathD =
    points.length > 0
      ? "M " + points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ")
      : "";

  return (
    <SceneFrame
      slideNumber={7}
      totalSlides={12}
      audioFile="slide-07.wav"
      caption="Why are plants green? Chlorophyll absorbs red and blue strongly — but reflects green. Green is what reaches our eyes."
    >
      <AbsoluteFill style={{ backgroundColor: SPECTRUM_PALETTE.bg, opacity: bgFade }}>
        <h2
          style={{
            position: "absolute",
            top: 100,
            left: 0,
            right: 0,
            textAlign: "center",
            margin: 0,
            fontSize: 36,
            fontWeight: 700,
            color: SPECTRUM_PALETTE.ink,
            fontFamily: PAI_THEME.typography.fontFamily,
            transform: `scale(${interpolate(titleSpring, [0, 1], [0.95, 1])})`,
          }}
        >
          Chlorophyll absorption spectrum
        </h2>

        <svg
          width={1920}
          height={1080}
          style={{ position: "absolute", inset: 0, fontFamily: PAI_THEME.typography.fontFamily }}
        >
          {/* Y-axis */}
          <line
            x1={CHART_X}
            y1={CHART_Y}
            x2={CHART_X}
            y2={CHART_Y + CHART_H}
            stroke={SPECTRUM_PALETTE.axis}
            strokeWidth={2}
          />
          <text
            x={CHART_X - 20}
            y={CHART_Y + CHART_H / 2}
            fill={SPECTRUM_PALETTE.ink}
            fontSize={22}
            transform={`rotate(-90 ${CHART_X - 20} ${CHART_Y + CHART_H / 2})`}
            textAnchor="middle"
          >
            absorbance
          </text>

          {/* X-axis */}
          <line
            x1={CHART_X}
            y1={CHART_Y + CHART_H}
            x2={CHART_X + CHART_W}
            y2={CHART_Y + CHART_H}
            stroke={SPECTRUM_PALETTE.axis}
            strokeWidth={2}
          />

          {/* Visible-spectrum colour bar under the X-axis */}
          {Array.from({ length: 60 }).map((_, i) => {
            const nm = X_MIN_NM + ((X_MAX_NM - X_MIN_NM) * i) / 60;
            const x = nmToX(nm);
            return (
              <rect
                key={i}
                x={x}
                y={CHART_Y + CHART_H + 10}
                width={CHART_W / 60 + 1}
                height={28}
                fill={wavelengthColor(nm)}
                opacity={0.85}
              />
            );
          })}
          {/* X-axis labels (selected wavelengths) */}
          {[400, 500, 600, 700].map((nm) => (
            <g key={nm}>
              <line
                x1={nmToX(nm)}
                y1={CHART_Y + CHART_H}
                x2={nmToX(nm)}
                y2={CHART_Y + CHART_H + 6}
                stroke={SPECTRUM_PALETTE.axis}
                strokeWidth={2}
              />
              <text
                x={nmToX(nm)}
                y={CHART_Y + CHART_H + 70}
                fontSize={20}
                fill={SPECTRUM_PALETTE.ink}
                textAnchor="middle"
              >
                {nm} nm
              </text>
            </g>
          ))}

          {/* Chlorophyll absorbance curve — reveals left to right */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke={SPECTRUM_PALETTE.curve}
              strokeWidth={5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Annotations */}
          {/* Blue peak */}
          {blueLabelOpacity > 0 && (
            <g opacity={blueLabelOpacity}>
              <line
                x1={nmToX(440)}
                y1={curvePoint(440).y - 30}
                x2={nmToX(440)}
                y2={curvePoint(440).y - 5}
                stroke={SPECTRUM_PALETTE.blue}
                strokeWidth={2}
              />
              <rect
                x={nmToX(440) - 90}
                y={curvePoint(440).y - 80}
                width={180}
                height={50}
                fill={SPECTRUM_PALETTE.blue}
                rx={8}
              />
              <text
                x={nmToX(440)}
                y={curvePoint(440).y - 47}
                fill="#fff"
                fontSize={20}
                fontWeight={700}
                textAnchor="middle"
              >
                absorbs blue
              </text>
            </g>
          )}
          {/* Red peak */}
          {redLabelOpacity > 0 && (
            <g opacity={redLabelOpacity}>
              <line
                x1={nmToX(660)}
                y1={curvePoint(660).y - 30}
                x2={nmToX(660)}
                y2={curvePoint(660).y - 5}
                stroke={SPECTRUM_PALETTE.red}
                strokeWidth={2}
              />
              <rect
                x={nmToX(660) - 90}
                y={curvePoint(660).y - 80}
                width={180}
                height={50}
                fill={SPECTRUM_PALETTE.red}
                rx={8}
              />
              <text
                x={nmToX(660)}
                y={curvePoint(660).y - 47}
                fill="#fff"
                fontSize={20}
                fontWeight={700}
                textAnchor="middle"
              >
                absorbs red
              </text>
            </g>
          )}
          {/* Green callout in the trough */}
          {greenCalloutOpacity > 0 && (
            <g opacity={greenCalloutOpacity}>
              <line
                x1={nmToX(550)}
                y1={CHART_Y + 20}
                x2={nmToX(550)}
                y2={curvePoint(550).y - 4}
                stroke={SPECTRUM_PALETTE.green}
                strokeWidth={2}
                strokeDasharray="6 4"
              />
              <rect
                x={nmToX(550) - 220}
                y={CHART_Y - 30}
                width={440}
                height={60}
                fill={SPECTRUM_PALETTE.green}
                rx={10}
              />
              <text
                x={nmToX(550)}
                y={CHART_Y + 8}
                fill="#fff"
                fontSize={22}
                fontWeight={700}
                textAnchor="middle"
              >
                reflects green — this is what we see
              </text>
            </g>
          )}
        </svg>
      </AbsoluteFill>
    </SceneFrame>
  );
};
