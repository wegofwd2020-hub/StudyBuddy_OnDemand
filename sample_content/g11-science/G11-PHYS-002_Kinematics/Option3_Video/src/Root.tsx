import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { UamScene } from './scenes/UamScene';
import { FreeFallScene } from './scenes/FreeFallScene';
import { ProjectileScene } from './scenes/ProjectileScene';
import { GraphAnalysisScene } from './scenes/GraphAnalysisScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="kinematics-uam"
        component={UamScene}
        durationInFrames={30 * 24}     // 24 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="kinematics-freefall"
        component={FreeFallScene}
        durationInFrames={30 * 28}     // 28 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="kinematics-projectile"
        component={ProjectileScene}
        durationInFrames={30 * 22}     // 22 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="kinematics-graphs"
        component={GraphAnalysisScene}
        durationInFrames={30 * 26}     // 26 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
