/**
 * PAI Theme for Remotion — mirrors kinematics + oscillations + g9 + structure-of-atom + basic-chem + thermo themes.
 * Adds redox-specific palette: anode (Zn), cathode (Cu), electron flow, ion migration.
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
    proton: '#dc2626',
    neutron: '#64748b',
    electron: '#3b82f6',
    photon: '#facc15',
    carbon: '#1f2937',
    hydrogen: '#fef3c7',
    oxygen: '#dc2626',

    // Thermo-specific (kept for parity with sibling project)
    reactant: '#f87171',
    product: '#34d399',
    transitionState: '#fbbf24',
    energyCurve: '#fb7185',

    // Redox-specific
    zinc: '#a3a3a3',          // silvery-grey Zn electrode
    zincDark: '#525252',
    copper: '#d97706',        // reddish-orange Cu electrode
    copperDark: '#92400e',
    zincSolution: 'rgba(165, 180, 252, 0.35)',  // pale blue ZnSO₄
    copperSolution: 'rgba(96, 165, 250, 0.55)', // deeper blue CuSO₄ (more saturated)
    saltBridge: '#fde68a',    // pale amber agar gel
    saltBridgeDark: '#f59e0b',
    sodiumIon: '#fbbf24',     // Na⁺ — gold
    sulfateIon: '#a78bfa',    // SO₄²⁻ — violet
    wireColor: '#cbd5e1',     // metallic wire
    electronGlow: '#60a5fa',  // bright blue glow for moving electrons
    voltmeter: '#facc15',     // yellow LCD-style display
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
