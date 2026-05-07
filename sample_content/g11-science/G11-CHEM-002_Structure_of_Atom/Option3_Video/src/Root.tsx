import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { BohrTransitionScene } from './scenes/BohrTransitionScene';
import { ElectronFillScene } from './scenes/ElectronFillScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="structure-of-atom-bohr-transition"
        component={BohrTransitionScene}
        durationInFrames={30 * 24}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="structure-of-atom-electron-fill"
        component={ElectronFillScene}
        durationInFrames={30 * 24}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
