/** Typed access to art/layout.json, the stage geometry shared with the Blender scripts. */
import raw from '../../art/layout.json';

export interface AmpLayout {
  id: string;
  voice: string;
  head: Rect;
  panel: Rect;
  grille: Rect;
  knobSize: number;
  knobStyle: string;
  knobY: number;
  knobs: { key: string; x: number }[];
  labelDy: number;
  power: Point;
  jewel: Point;
  /** Numbers printed around the knobs, e.g. [1, 12] on a tweed panel: values are shown on it. */
  scale: [number, number];
}

export interface PedalLayout {
  id: 'comp' | 'od' | 'delay' | 'reverb';
  scene: 'pre' | 'post';
  name: string;
  color: [number, number, number];
  cx: number;
  cy: number;
  knobs: { key: string; dx: number; dy: number }[];
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Point {
  x: number;
  y: number;
}

export const LAYOUT = raw as unknown as {
  /** The safe area: everything interactive lives in these coordinates. */
  stage: { w: number; h: number };
  /** Backgrounds are rendered larger than the stage so any window shape is filled. */
  canvas: Rect;
  frames: number;
  knobStrip: { cols: number; pad: number };
  amps: AmpLayout[];
  pedal: {
    w: number;
    h: number;
    knobSize: number;
    footswitch: { dx: number; dy: number; r: number };
    led: { dx: number; dy: number };
    name: { dx: number; dy: number };
  };
  pedals: PedalLayout[];
  cab: { speaker: { cx: number; cy: number; r: number }; panel: Rect };
};
