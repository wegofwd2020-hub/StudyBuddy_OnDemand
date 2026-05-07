import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { PAI_THEME } from '../theme';

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subtitleOpacity = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });
  const subtitleY = interpolate(frame, [30, 60], [20, 0], { extrapolateRight: 'clamp' });

  // Math symbols floating in background
  const symbols = ['∪', '∩', '∈', '⊆', '𝒫', '∀', '∃', '∘', 'ƒ', '⁻¹'];

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background} 0%, ${PAI_THEME.colors.backgroundAlt} 100%)`,
      justifyContent: 'center', alignItems: 'center', flexDirection: 'column',
    }}>
      {/* Floating math glyphs */}
      {symbols.map((s, i) => {
        const phase = (i / symbols.length) * Math.PI * 2;
        const x = 200 + (i % 5) * 350 + Math.sin(frame / 30 + phase) * 30;
        const y = 150 + Math.floor(i / 5) * 700 + Math.cos(frame / 30 + phase) * 25;
        const op = interpolate(frame, [10 + i * 3, 40 + i * 3], [0, 0.18], { extrapolateRight: 'clamp' });
        return (
          <div key={i} style={{
            position: 'absolute', left: x, top: y, fontSize: 140, color: PAI_THEME.colors.accent,
            opacity: op, fontWeight: 700,
          }}>{s}</div>
        );
      })}
      <h1 style={{
        ...PAI_THEME.typography.title,
        fontSize: 110,
        color: PAI_THEME.colors.text,
        opacity: titleOpacity, transform: `scale(${titleScale})`,
        textShadow: PAI_THEME.effects.textShadow,
        margin: 0, textAlign: 'center', zIndex: 1,
      }}>
        Sets and Functions
      </h1>
      <p style={{
        ...PAI_THEME.typography.subtitle,
        color: PAI_THEME.colors.accentLight,
        opacity: subtitleOpacity,
        transform: `translateY(${subtitleY}px)`,
        margin: '24px 0 0', textAlign: 'center', zIndex: 1,
      }}>
        From foundational theory to functional reasoning
      </p>
    </AbsoluteFill>
  );
};
