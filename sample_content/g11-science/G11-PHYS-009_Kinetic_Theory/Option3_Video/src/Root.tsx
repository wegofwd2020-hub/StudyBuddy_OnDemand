import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { MaxwellBoltzmannScene } from './scenes/MaxwellBoltzmannScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="kinetic-theory-maxwell-boltzmann"
        component={MaxwellBoltzmannScene}
        durationInFrames={30 * 28}     // 28 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
