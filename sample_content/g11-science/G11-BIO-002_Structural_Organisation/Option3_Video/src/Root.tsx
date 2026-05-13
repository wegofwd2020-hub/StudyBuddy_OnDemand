import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { CellToOrganismZoomScene } from './scenes/CellToOrganismZoomScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="bio-org-zoom-cell-to-organism"
        component={CellToOrganismZoomScene}
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
