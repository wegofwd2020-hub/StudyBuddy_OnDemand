/**
 * PAI Theme for Remotion — mirrors kinematics + oscillations + g9 + structure-of-atom themes.
 * Adds chemistry-specific particle palette + periodic-block colours.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#8b5cf6',
    accentLight: '#a78bfa',
    accentDark: '#7c3aed',
    accentMuted: '#6366f1',

    text: '#f1f5f9',
    textMuted: '#94a3b8',
    textDark: '#64748b',

    paperGround: '#F5F5F0',
    coolWash: 'rgba(139, 92, 246, 0.1)',
    warmWash: 'rgba(251, 191, 36, 0.1)',

    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',

    // Chemistry particle palette — matches Phase-1 SVG catalogue
    proton: '#dc2626',     // red
    neutron: '#64748b',    // slate
    electron: '#3b82f6',   // blue
    photon: '#facc15',     // yellow

    // Periodic-block tile colours — mirrors the SVG catalogue
    blockS: '#3b82f6',     // s — blue
    blockP: '#f97316',     // p — orange
    blockD: '#22c55e',     // d — green
    blockF: '#a855f7',     // f — purple

    // Trend gradients
    trendCool: '#3b82f6',  // start of "small/low" gradient
    trendWarm: '#dc2626',  // end of "big/high" gradient
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',

    title: { fontSize: 72, fontWeight: 'bold' as const, lineHeight: 1.1 },
    subtitle: { fontSize: 48, fontWeight: '600' as const, lineHeight: 1.2 },
    heading: { fontSize: 36, fontWeight: '600' as const, lineHeight: 1.3 },
    body: { fontSize: 24, fontWeight: 'normal' as const, lineHeight: 1.5 },
    caption: { fontSize: 18, fontWeight: 'normal' as const, lineHeight: 1.4 },
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },

    fadeFrames: 30,
    quickFade: 15,
    slowFade: 45,
  },
} as const;

export type PAITheme = typeof PAI_THEME;
