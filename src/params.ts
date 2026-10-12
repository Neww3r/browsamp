/** Every user-facing control, and how it maps onto the DSP parameter IDs (see dsp/src/amp.rs, fx.rs). */

/** `cab` parameters never reach a worklet: they drive the cabinet IR synthesis. */
export type Target = 'amp' | 'fx' | 'cab';

export interface ParamDef {
  key: string;
  label: string;
  target: Target;
  id: number;
  min: number;
  max: number;
  def: number;
  log?: boolean;
  /** UI value → value sent to the DSP. */
  toDsp?: (v: number) => number;
  fmt: (v: number) => string;
}

const knob10 = (v: number) => v.toFixed(1);
const pct = (v: number) => `${Math.round(v)} %`;
const db = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)} dB`;
const div10 = (v: number) => v / 10;
const div100 = (v: number) => v / 100;

export const GATE_OFF = -90;

export const PARAMS: ParamDef[] = [
  { key: 'input', label: 'Input', target: 'amp', id: 0, min: -24, max: 24, def: 0, fmt: db },
  { key: 'gate', label: 'Gate', target: 'amp', id: 1, min: GATE_OFF, max: -20, def: GATE_OFF, fmt: (v) => (v <= GATE_OFF + 0.5 ? 'Off' : `${Math.round(v)} dB`) },

  // Amp knobs: one set per amp model (see AMP_KNOBS).
  { key: 'gain', label: 'Gain', target: 'amp', id: 2, min: 0, max: 10, def: 5, fmt: knob10 },
  { key: 'bass', label: 'Bass', target: 'amp', id: 3, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },
  { key: 'mid', label: 'Middle', target: 'amp', id: 4, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },
  { key: 'treble', label: 'Treble', target: 'amp', id: 5, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },
  { key: 'presence', label: 'Presence', target: 'amp', id: 6, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },
  { key: 'resonance', label: 'Resonance', target: 'amp', id: 7, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },
  { key: 'master', label: 'Master', target: 'amp', id: 8, min: 0, max: 10, def: 5, toDsp: div10, fmt: knob10 },

  // Pre-FX pedals (amp worklet, before the preamp).
  { key: 'compSustain', label: 'Sustain', target: 'amp', id: 12, min: 0, max: 10, def: 5, fmt: knob10 },
  { key: 'compAttack', label: 'Attack', target: 'amp', id: 13, min: 0, max: 10, def: 5, fmt: knob10 },
  { key: 'compLevel', label: 'Level', target: 'amp', id: 14, min: -12, max: 12, def: 0, fmt: db },
  { key: 'compBlend', label: 'Blend', target: 'amp', id: 15, min: 0, max: 100, def: 100, toDsp: div100, fmt: pct },
  { key: 'odDrive', label: 'Drive', target: 'amp', id: 17, min: 0, max: 10, def: 4, fmt: knob10 },
  { key: 'odTone', label: 'Tone', target: 'amp', id: 18, min: 0, max: 10, def: 5, fmt: knob10 },
  { key: 'odLevel', label: 'Level', target: 'amp', id: 19, min: 0, max: 10, def: 5, fmt: knob10 },

  // Post-FX (fx worklet).
  { key: 'delayMix', label: 'Mix', target: 'fx', id: 0, min: 0, max: 100, def: 25, toDsp: div100, fmt: pct },
  { key: 'delayTime', label: 'Time', target: 'fx', id: 1, min: 40, max: 1500, def: 380, log: true, fmt: (v) => `${Math.round(v)} ms` },
  { key: 'delayFb', label: 'Repeats', target: 'fx', id: 2, min: 0, max: 90, def: 35, toDsp: div100, fmt: pct },
  { key: 'delayTone', label: 'Tone', target: 'fx', id: 3, min: 800, max: 10000, def: 3500, log: true, fmt: (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)} kHz` : `${Math.round(v)} Hz`) },
  { key: 'reverbMix', label: 'Mix', target: 'fx', id: 4, min: 0, max: 100, def: 20, toDsp: div100, fmt: pct },
  { key: 'reverbDecay', label: 'Decay', target: 'fx', id: 5, min: 0.3, max: 10, def: 2, log: true, fmt: (v) => `${v.toFixed(1)} s` },
  { key: 'reverbDamp', label: 'Damping', target: 'fx', id: 6, min: 0, max: 90, def: 35, toDsp: div100, fmt: pct },
  { key: 'reverbPredelay', label: 'Pre-delay', target: 'fx', id: 7, min: 0, max: 150, def: 15, fmt: (v) => `${Math.round(v)} ms` },
  { key: 'output', label: 'Output', target: 'fx', id: 8, min: -40, max: 12, def: -9, fmt: db },

  // Cabinet microphones.
  { key: 'mic1Dist', label: 'Distance', target: 'cab', id: 0, min: 0, max: 30, def: 2, fmt: (v) => `${v.toFixed(1)} cm` },
  { key: 'mic1Level', label: 'Level', target: 'cab', id: 1, min: -30, max: 6, def: 0, fmt: db },
  { key: 'mic2Dist', label: 'Distance', target: 'cab', id: 2, min: 0, max: 30, def: 12, fmt: (v) => `${v.toFixed(1)} cm` },
  { key: 'mic2Level', label: 'Level', target: 'cab', id: 3, min: -30, max: 6, def: -30, fmt: (v) => (v <= -29.9 ? 'Off' : db(v)) },
];

export const PARAM = Object.fromEntries(PARAMS.map((p) => [p.key, p])) as Record<string, ParamDef>;

export const AMP_KNOBS = ['gain', 'bass', 'mid', 'treble', 'presence', 'resonance', 'master'] as const;
export type AmpKnob = (typeof AMP_KNOBS)[number];
export const isAmpKnob = (key: string): key is AmpKnob => (AMP_KNOBS as readonly string[]).includes(key);

/** DSP parameter IDs that are switches rather than knobs. */
export const AMP_TUNER = 9;
export const AMP_TUNER_MUTE = 10;
export const AMP_COMP_ON = 11;
export const AMP_OD_ON = 16;

export function toNorm(p: ParamDef, v: number): number {
  return p.log ? Math.log(v / p.min) / Math.log(p.max / p.min) : (v - p.min) / (p.max - p.min);
}

export function fromNorm(p: ParamDef, t: number): number {
  t = Math.min(1, Math.max(0, t));
  return p.log ? p.min * Math.pow(p.max / p.min, t) : p.min + t * (p.max - p.min);
}
