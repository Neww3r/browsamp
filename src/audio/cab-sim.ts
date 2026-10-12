/**
 * Microphone simulation for the cabinet page. Each mic's response is the cabinet response
 * shaped by where the mic sits on the cone, how far it is from the grille and what kind of
 * mic it is; two mics are summed with their true arrival delays (so blending them can comb,
 * like the real thing). The result is a minimum-phase-ish IR conditioned like any other.
 */

import { BUILTIN_CABS, bands, cabinetChain, conditionIr, reflection, toBuffer, type Band } from './ir';

export interface MicSpec {
  /** 0 = dynamic (SM57-style), 1 = ribbon (R121-style). */
  type: 0 | 1;
  /** Position on the cone: 0 = dust cap, 1 = edge of the cone. */
  r: number;
  /** Distance from the grille, in centimetres. */
  distCm: number;
  levelDb: number;
}

const MIC_VOICE: Record<0 | 1, Band[]> = {
  0: [
    { type: 'highpass', f: 70, q: 0.7 },
    { type: 'peaking', f: 220, q: 1.0, gain: -1.5 },
    { type: 'peaking', f: 5800, q: 1.4, gain: 4 },
    { type: 'lowpass', f: 14500, q: 0.7 },
  ],
  1: [
    { type: 'lowshelf', f: 160, gain: 2 },
    { type: 'highshelf', f: 3000, gain: -4.5 },
    { type: 'lowpass', f: 8500, q: 0.6 },
  ],
};

const SPEED_CM_PER_S = 34300;
const LENGTH_S = 0.12;

function micBands(m: MicSpec): Band[] {
  const r = Math.min(1, Math.max(0, m.r));
  const near = 1 - Math.min(1, m.distCm / 30);
  return [
    ...MIC_VOICE[m.type],
    // Off the dust cap the cone radiates less treble and the presence peak moves down.
    { type: 'highshelf', f: 3200, gain: -8 * Math.pow(r, 1.3) },
    { type: 'peaking', f: 4800 - 2200 * r, q: 1.2, gain: 3 - 3.5 * r },
    { type: 'lowpass', f: 12000 - 5000 * r, q: 0.6 },
    // Proximity effect: directional mics gain bass up close (ribbons, figure-8, even more).
    { type: 'lowshelf', f: 190, gain: (m.type === 1 ? 9 : 6.5) * near * near },
    // A little air absorption and room further out.
    { type: 'highshelf', f: 8000, gain: -2.5 * (1 - near) },
  ];
}

/** Renders the summed IR of the active mics. Mics at or below -30 dB are off. */
export async function renderMicIr(ctx: BaseAudioContext, cabinet: number, mics: MicSpec[]): Promise<AudioBuffer> {
  const sr = ctx.sampleRate;
  const off = new OfflineAudioContext(1, Math.round(sr * LENGTH_S), sr);
  const imp = off.createBuffer(1, off.length, sr);
  imp.getChannelData(0)[0] = 1;
  const src = off.createBufferSource();
  src.buffer = imp;

  const cab = cabinetChain(off, src, BUILTIN_CABS[cabinet] ?? BUILTIN_CABS[0]);
  let active = 0;
  for (const m of mics) {
    if (m.levelDb <= -29.9) continue;
    active++;
    const delay = off.createDelay(0.05);
    delay.delayTime.value = m.distCm / SPEED_CM_PER_S;
    cab.connect(delay);
    let node: AudioNode = bands(off, delay, micBands(m));
    // Floor/baffle reflection: later and stronger as the mic backs off.
    node = reflection(off, node, 0.35 + m.distCm * 0.09, 0.08 + (m.distCm / 30) * 0.3);
    const g = off.createGain();
    g.gain.value = Math.pow(10, m.levelDb / 20);
    node.connect(g).connect(off.destination);
  }
  if (!active) cab.connect(off.destination);
  src.start();
  const out = await off.startRendering();
  return toBuffer(ctx, conditionIr(out.getChannelData(0), sr));
}
