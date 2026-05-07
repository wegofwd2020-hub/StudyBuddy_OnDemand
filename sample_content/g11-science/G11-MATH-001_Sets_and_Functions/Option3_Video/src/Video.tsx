import React from 'react';
import { AbsoluteFill, Series } from 'remotion';
import { PAI_THEME } from './theme';
import { SCENE } from './Root';
import { TitleScene } from './scenes/TitleScene';
import { VennScene } from './scenes/VennScene';
import { VerticalLineTestScene } from './scenes/VerticalLineTestScene';
import { ArrowDiagramScene } from './scenes/ArrowDiagramScene';
import { CompositionScene } from './scenes/CompositionScene';
import { InverseScene } from './scenes/InverseScene';
import { TransformationsScene } from './scenes/TransformationsScene';
import { ProjectileScene } from './scenes/ProjectileScene';
import { ClosingScene } from './scenes/ClosingScene';

export const Video: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: PAI_THEME.colors.background, fontFamily: PAI_THEME.typography.fontFamily }}>
      <Series>
        <Series.Sequence durationInFrames={SCENE.title}>
          <TitleScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.venn}>
          <VennScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.vlt}>
          <VerticalLineTestScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.arrow}>
          <ArrowDiagramScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.composition}>
          <CompositionScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.inverse}>
          <InverseScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.transformations}>
          <TransformationsScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.projectile}>
          <ProjectileScene />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE.closing}>
          <ClosingScene />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
