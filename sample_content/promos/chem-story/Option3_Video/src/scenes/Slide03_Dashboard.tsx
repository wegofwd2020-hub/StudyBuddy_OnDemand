import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { CursorTrace } from "../components/CursorTrace";
import { AppFrame } from "../components/app/AppFrame";
import { DashboardPage } from "../components/app/DashboardPage";
import { DASHBOARD_TILES, PERSONA } from "../data/lesson";

/**
 * Slide 3 — the actual student dashboard, as it appears in the app.
 *
 * Renders <AppFrame> + <DashboardPage> with the active "Reactions of
 * alkenes" tile highlighted. Cursor moves to the active tile + clicks
 * to "open" the lesson. This is the first pixel-faithful app screen
 * the viewer sees.
 */
export const Slide03_Dashboard: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  // Active-tile glow ring is brightest after the cursor lands
  const ringPulse = frame >= 240;

  return (
    <SceneFrame
      slideNumber={3}
      totalSlides={12}
      audioFile="slide-03.wav"
      caption="Aditi opens her dashboard. Continue where you left off — Reactions of Alkenes is queued and ready."
    >
      <div style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        <AppFrame userName="Aditi K." clockTime="9:14 PM">
          <DashboardPage
            greeting={PERSONA.greeting}
            subjectName={PERSONA.subjectName}
            unitTiles={DASHBOARD_TILES}
            highlightActiveRing={ringPulse}
          />
        </AppFrame>
      </div>

      {/* Cursor: starts off-canvas, moves to active tile, clicks, hovers */}
      <CursorTrace
        path={[
          { x: 1700, y: 200, atFrame: 90 },
          { x: 960, y: 480, atFrame: 220 },  // hero "Continue" CTA position
          { x: 960, y: 480, atFrame: 280 },
        ]}
        clickAt={250}
      />
    </SceneFrame>
  );
};
