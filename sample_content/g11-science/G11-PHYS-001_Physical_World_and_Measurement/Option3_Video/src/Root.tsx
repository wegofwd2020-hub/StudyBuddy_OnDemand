import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { ScaleOfUniverseScene } from './scenes/ScaleOfUniverseScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="physical-world-scale"
        component={ScaleOfUniverseScene}
        durationInFrames={30 * 32}     // 32 s — 9 stops × ~3.3 s each + intro/outro
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
