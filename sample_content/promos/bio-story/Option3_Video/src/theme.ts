/**
 * Theme tokens — palette, typography, animation timings.
 *
 * Lifted from `pipeline/visual_templates/shared.ts` so the user-story
 * videos visually align with the rest of the StudyBuddy visual library.
 * Constants are inlined here rather than imported because Remotion
 * projects manage their own bundle and don't see outside-project
 * imports cleanly.
 */

export const PAI_THEME = {
  colors: {
    // Background range (deepest to lightest)
    background: "#0f172a",
    backgroundAlt: "#1e293b",
    backgroundDark: "#020617",

    // Brand accents — purple family
    accent: "#8b5cf6",
    accentLight: "#a78bfa",
    accentDark: "#7c3aed",
    accentMuted: "#6366f1",

    // Foreground text
    text: "#f1f5f9",
    textMuted: "#94a3b8",
    textDark: "#64748b",

    // Surface tones
    paperGround: "#F5F5F0",
    coolWash: "rgba(139, 92, 246, 0.1)",
    warmWash: "rgba(251, 191, 36, 0.1)",

    // Status colours (inherited from shared.ts)
    success: "#10b981",
    warning: "#f59e0b",
    error: "#ef4444",
    info: "#3b82f6",

    // Per-dimension hexagon colours (used by ScopingHexagon)
    dim1: "#8b5cf6", // topic
    dim2: "#3b82f6", // grade
    dim3: "#10b981", // language
    dim4: "#f59e0b", // curriculum context
    dim5: "#ef4444", // format
    dim6: "#a78bfa", // real-world framing
  },

  typography: {
    fontFamily:
      'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    title: { fontSize: 84, fontWeight: "bold" as const, lineHeight: 1.05 },
    subtitle: { fontSize: 42, fontWeight: "600" as const, lineHeight: 1.2 },
    heading: { fontSize: 36, fontWeight: "600" as const, lineHeight: 1.3 },
    body: { fontSize: 28, fontWeight: "normal" as const, lineHeight: 1.5 },
    caption: { fontSize: 22, fontWeight: "normal" as const, lineHeight: 1.4 },
    small: { fontSize: 16, fontWeight: "normal" as const, lineHeight: 1.4 },
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },
    springBouncy: { damping: 8, stiffness: 120 },

    fadeFrames: 30,
    quickFade: 15,
    slowFade: 45,

    // Per-slide layout: 16 seconds = 480 frames at 30fps
    settleInFrames: 30,
    captionHoldFrames: 30,
  },
} as const;

export type PAITheme = typeof PAI_THEME;

// Slide-rhythm constants used by Root.tsx + scenes
export const FPS = 30;
export const SLIDE_DURATION_SEC = 16;
export const SLIDE_DURATION_FRAMES = SLIDE_DURATION_SEC * FPS;
