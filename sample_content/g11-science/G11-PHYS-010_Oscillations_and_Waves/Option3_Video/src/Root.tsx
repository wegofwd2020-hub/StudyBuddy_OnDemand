import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { ShmScene } from './scenes/ShmScene';
import { WaveSuperpositionScene } from './scenes/WaveSuperpositionScene';
import { DopplerScene } from './scenes/DopplerScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="oscillations-shm"
        component={ShmScene}
        durationInFrames={30 * 24}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="oscillations-superposition"
        component={WaveSuperpositionScene}
        durationInFrames={30 * 26}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="oscillations-doppler"
        component={DopplerScene}
        durationInFrames={30 * 22}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
