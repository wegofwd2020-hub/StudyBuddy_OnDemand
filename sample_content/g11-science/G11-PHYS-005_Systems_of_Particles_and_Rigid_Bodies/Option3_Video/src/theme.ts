/**
 * PAI Theme for Remotion — mirrors kinematics + laws-of-motion video theme verbatim.
 *
 * Source: sample_content/g11-science/G11-PHYS-002_Kinematics/Option3_Video/src/theme.ts
 * Derived from Art skill preferences at:
 * ~/.claude/PAI/USER/SKILLCUSTOMIZATIONS/Art/PREFERENCES.md
 *
 * Core aesthetic: Charcoal architectural sketch with purple accents
 * Visual feel: Monumental emotional spaces, gestural linework, cool washes
 */

export const PAI_THEME = {
  // Colors (from Art color palette)
  colors: {
    // Backgrounds (vast architectural space feel)
    background: '#0f172a',        // Deep slate
    backgroundAlt: '#1e293b',     // Slightly lighter slate
    backgroundDark: '#020617',    // Near black

    // Accents (purple/violet from Art prefs)
    accent: '#8b5cf6',            // Primary purple
    accentLight: '#a78bfa',       // Lighter purple
    accentDark: '#7c3aed',        // Darker purple
    accentMuted: '#6366f1',       // Indigo variant

    // Text (paper ground inspired)
    text: '#f1f5f9',              // Light text
    textMuted: '#94a3b8',         // Muted/secondary text
    textDark: '#64748b',          // De-emphasized text

    // Special
    paperGround: '#F5F5F0',       // Cream/off-white from Art prefs
    coolWash: 'rgba(139, 92, 246, 0.1)', // Purple atmospheric wash
    warmWash: 'rgba(251, 191, 36, 0.1)', // Amber contrast wash

    // Utility
    success: '#10b981',           // Green
    warning: '#f59e0b',           // Amber
    error: '#ef4444',             // Red
    info: '#3b82f6',              // Blue
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontFamilyMono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    title: { fontSize: 72, fontWeight: 'bold' as const, lineHeight: 1.1 },
    subtitle: { fontSize: 48, fontWeight: '600' as const, lineHeight: 1.2 },
    heading: { fontSize: 36, fontWeight: '600' as const, lineHeight: 1.3 },
    body: { fontSize: 24, fontWeight: 'normal' as const, lineHeight: 1.5 },
    caption: { fontSize: 18, fontWeight: 'normal' as const, lineHeight: 1.4 },
    small: { fontSize: 14, fontWeight: 'normal' as const, lineHeight: 1.4 },
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },
    springBouncy: { damping: 8, stiffness: 120 },

    fadeFrames: 30,
    quickFade: 15,
    slowFade: 45,

    staggerDelay: 10,
    staggerFast: 5,
    staggerSlow: 15,
  },

  spacing: {
    page: 100,
    section: 60,
    element: 30,
    tight: 15,

    paragraphGap: 24,
    listItemGap: 16,
  },

  effects: {
    textShadow: '0 2px 4px rgba(0,0,0,0.5)',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
    boxShadowLarge: '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)',
    glow: '0 0 20px rgba(139, 92, 246, 0.5)',
  },

  borderRadius: {
    small: 8,
    medium: 16,
    large: 24,
    full: 9999,
  },
} as const

export type PAITheme = typeof PAI_THEME
export type PAIColors = typeof PAI_THEME.colors
export type PAITypography = typeof PAI_THEME.typography
export type PAIAnimation = typeof PAI_THEME.animation

export const fadeInterpolation = (startFrame = 0) => ({
  inputRange: [startFrame, startFrame + PAI_THEME.animation.fadeFrames],
  outputRange: [0, 1] as [number, number],
})

export const titleScreenStyle = {
  backgroundColor: PAI_THEME.colors.background,
  display: 'flex' as const,
  justifyContent: 'center' as const,
  alignItems: 'center' as const,
  fontFamily: PAI_THEME.typography.fontFamily,
}

export const contentScreenStyle = {
  backgroundColor: PAI_THEME.colors.background,
  padding: PAI_THEME.spacing.page,
  fontFamily: PAI_THEME.typography.fontFamily,
}
