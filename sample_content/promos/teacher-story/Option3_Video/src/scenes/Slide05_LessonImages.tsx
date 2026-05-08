import React from "react";
import { AbsoluteFill } from "remotion";
import { PAI_THEME } from "../theme";
import { SlideInPanel } from "../components/SlideInPanel";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 5 — "Then images"
 *
 * Visual: three image panels slide in from the right with motion-blur
 * trails — a force-body diagram, a velocity-time graph, and a hurricane
 * deceleration map. They tile across the lesson canvas.
 */
const ImagePanel: React.FC<{ title: string; subtitle: string; bg: string }> = ({
  title,
  subtitle,
  bg,
}) => (
  <div
    style={{
      width: 380,
      height: 280,
      backgroundColor: bg,
      borderRadius: 12,
      padding: 24,
      display: "flex",
      flexDirection: "column",
      justifyContent: "flex-end",
      border: `2px solid ${PAI_THEME.colors.accentLight}`,
      boxShadow: "0 12px 24px rgba(0,0,0,0.3)",
    }}
  >
    <p
      style={{
        margin: 0,
        color: "#0f172a",
        fontSize: 24,
        fontWeight: 700,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {title}
    </p>
    <p
      style={{
        margin: "4px 0 0 0",
        color: "#334155",
        fontSize: 16,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {subtitle}
    </p>
  </div>
);

export const Slide05_LessonImages: React.FC = () => {
  return (
    <SceneFrame
      slideNumber={5}
      totalSlides={12}
      audioFile="slide-05.wav"
      caption="Then images. Force-body diagrams. Motion graphs. A hurricane evacuation map drawn from this week's news."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ position: "relative", width: 1400, height: 320 }}>
          <div style={{ position: "absolute", top: 0, left: 80 }}>
            <SlideInPanel from="right" appearAt={0} distance={800}>
              <ImagePanel
                title="Force-body diagram"
                subtitle="Tension, friction, gravity"
                bg="#fde68a"
              />
            </SlideInPanel>
          </div>
          <div style={{ position: "absolute", top: 0, left: 510 }}>
            <SlideInPanel from="right" appearAt={45} distance={800}>
              <ImagePanel
                title="v-t graph"
                subtitle="Constant deceleration"
                bg="#bfdbfe"
              />
            </SlideInPanel>
          </div>
          <div style={{ position: "absolute", top: 0, left: 940 }}>
            <SlideInPanel from="right" appearAt={90} distance={800}>
              <ImagePanel
                title="Hurricane evac map"
                subtitle="Real news, this week"
                bg="#fecaca"
              />
            </SlideInPanel>
          </div>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
