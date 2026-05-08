import React from "react";
import { AbsoluteFill } from "remotion";
import { PAI_THEME } from "../theme";
import { SlideInPanel } from "../components/SlideInPanel";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 4 — Layer 2: IMAGES
 *
 * Visual: layer indicator advances. Three image panels slide in from
 * the right with motion-blur — force-body diagram, a position-time
 * graph, and a hurricane-evacuation map (the "this week's news" hook).
 */
const LAYERS = ["TEXT", "IMAGES", "ANIMATION", "QUIZ", "TUTORIAL"];

const LayerStackIndicator: React.FC<{ active: number }> = ({ active }) => (
  <div
    style={{
      width: 360,
      display: "flex",
      flexDirection: "column",
      gap: 10,
      fontFamily: PAI_THEME.typography.fontFamilyMono,
    }}
  >
    {LAYERS.map((label, i) => {
      const isActive = i === active;
      const isPast = i < active;
      return (
        <div
          key={i}
          style={{
            padding: "16px 22px",
            backgroundColor: isActive
              ? PAI_THEME.colors.accent
              : isPast
              ? PAI_THEME.colors.backgroundAlt
              : "transparent",
            border: `2px solid ${
              isActive ? PAI_THEME.colors.accentLight : PAI_THEME.colors.textDark
            }`,
            borderRadius: 8,
            color: isActive
              ? PAI_THEME.colors.text
              : isPast
              ? PAI_THEME.colors.textMuted
              : PAI_THEME.colors.textDark,
            fontSize: 22,
            fontWeight: isActive ? 700 : 500,
            display: "flex",
            justifyContent: "space-between",
            opacity: isActive ? 1 : isPast ? 0.7 : 0.4,
          }}
        >
          <span>0{i + 1}</span>
          <span>{label}</span>
        </div>
      );
    })}
  </div>
);

const ImagePanel: React.FC<{ title: string; subtitle: string; bg: string }> = ({
  title,
  subtitle,
  bg,
}) => (
  <div
    style={{
      width: 360,
      height: 260,
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
        fontSize: 22,
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

export const Slide04_LayerImages: React.FC = () => {
  return (
    <SceneFrame
      slideNumber={4}
      totalSlides={12}
      audioFile="slide-04.mp3"
      caption="Layer two — IMAGES. Force diagrams. A motion graph. The hurricane map from this week's news, drawn for her grade."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 60,
          flexDirection: "row",
          padding: "0 80px",
        }}
      >
        <LayerStackIndicator active={1} />

        <div style={{ position: "relative", flex: 1, height: 600 }}>
          <div style={{ position: "absolute", top: 40, left: 0 }}>
            <SlideInPanel from="right" appearAt={0} distance={800}>
              <ImagePanel
                title="Force-body diagram"
                subtitle="Tension, friction, gravity"
                bg="#fde68a"
              />
            </SlideInPanel>
          </div>
          <div style={{ position: "absolute", top: 180, left: 80 }}>
            <SlideInPanel from="right" appearAt={45} distance={800}>
              <ImagePanel
                title="v-t graph"
                subtitle="Constant deceleration"
                bg="#bfdbfe"
              />
            </SlideInPanel>
          </div>
          <div style={{ position: "absolute", top: 320, left: 160 }}>
            <SlideInPanel from="right" appearAt={90} distance={800}>
              <ImagePanel
                title="Hurricane evac map"
                subtitle="Real news — this week"
                bg="#fecaca"
              />
            </SlideInPanel>
          </div>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
