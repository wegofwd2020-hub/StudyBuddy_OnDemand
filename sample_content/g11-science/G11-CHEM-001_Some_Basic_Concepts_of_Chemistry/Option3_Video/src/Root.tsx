import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { MoleVisualizationScene } from './scenes/MoleVisualizationScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="basic-chem-mole-visualization"
        component={MoleVisualizationScene}
        durationInFrames={30 * 28}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
