/**
 * Cabinet impulse responses. Built-in IRs are synthesized (minimum-phase filter chains, so
 * they add no latency); user IRs are loaded from .wav files and conditioned the same way.
 */

const MAX_IR_SECONDS = 0.2;
const FADE_SECONDS = 0.02;

export interface Band {
  type: BiquadFilterType;
  f: number;
  q?: number;
  gain?: number;
}

export interface CabDesign {
  name: string;
  bands: Band[];
  /** Early reflection (delay in ms, linear gain), e.g. back panel of an open cab. */
  reflection?: [number, number];
}

export const BUILTIN_CABS: CabDesign[] = [
  {
    name: '4x12 Moderne',
    bands: [
      { type: 'highpass', f: 75, q: 1.4 },
      { type: 'peaking', f: 120, q: 1.0, gain: 3 },
      { type: 'peaking', f: 450, q: 1.2, gain: -3 },
      { type: 'peaking', f: 2500, q: 1.4, gain: 4.5 },
      { type: 'peaking', f: 4300, q: 3, gain: -4 },
      { type: 'lowpass', f: 5200, q: 0.8 },
      { type: 'lowpass', f: 6500, q: 0.7 },
    ],
  },
  {
    name: '2x12 Vintage',
    bands: [
      { type: 'highpass', f: 70, q: 1.0 },
      { type: 'peaking', f: 180, q: 0.8, gain: 1.5 },
      { type: 'peaking', f: 1500, q: 1.0, gain: 3 },
      { type: 'peaking', f: 3000, q: 1.5, gain: 2 },
      { type: 'lowpass', f: 4500, q: 0.9 },
      { type: 'lowpass', f: 6000, q: 0.7 },
    ],
    reflection: [0.45, 0.25],
  },
  {
    name: '1x12 Ouvert',
    bands: [
      { type: 'highpass', f: 90, q: 0.8 },
      { type: 'peaking', f: 220, q: 1.0, gain: -2 },
      { type: 'peaking', f: 2000, q: 1.0, gain: 2.5 },
      { type: 'lowpass', f: 6500, q: 0.7 },
      { type: 'lowpass', f: 9000, q: 0.7 },
    ],
    reflection: [1.3, 0.3],
  },
];

/** Chains biquads after `input` and returns the last node. */
export function bands(ctx: BaseAudioContext, input: AudioNode, list: Band[]): AudioNode {
  let node = input;
  for (const b of list) {
    const f = ctx.createBiquadFilter();
    f.type = b.type;
    f.frequency.value = b.f;
    if (b.q !== undefined) f.Q.value = b.q;
    if (b.gain !== undefined) f.gain.value = b.gain;
    node.connect(f);
    node = f;
  }
  return node;
}

/** Adds a single delayed copy of `input` (an early reflection) and returns the sum. */
export function reflection(ctx: BaseAudioContext, input: AudioNode, ms: number, gain: number): AudioNode {
  const sum = ctx.createGain();
  const delay = ctx.createDelay(0.1);
  delay.delayTime.value = ms / 1000;
  const g = ctx.createGain();
  g.gain.value = gain;
  input.connect(sum);
  input.connect(delay).connect(g).connect(sum);
  return sum;
}

export function cabinetChain(ctx: BaseAudioContext, input: AudioNode, d: CabDesign): AudioNode {
  const node = bands(ctx, input, d.bands);
  return d.reflection ? reflection(ctx, node, ...d.reflection) : node;
}

async function renderDesign(d: CabDesign, sr: number): Promise<Float32Array> {
  const len = Math.round(sr * 0.1);
  const off = new OfflineAudioContext(1, len, sr);
  const imp = off.createBuffer(1, len, sr);
  imp.getChannelData(0)[0] = 1;
  const src = off.createBufferSource();
  src.buffer = imp;

  cabinetChain(off, src, d).connect(off.destination);
  src.start();
  const out = await off.startRendering();
  return out.getChannelData(0).slice();
}

/** Trim leading silence (it would only add latency), cap length, fade out, unit-energy normalize. */
export function conditionIr(data: Float32Array, sr: number): Float32Array {
  let peak = 0;
  for (const v of data) peak = Math.max(peak, Math.abs(v));
  if (peak === 0) throw new Error('IR silencieuse');
  let start = 0;
  while (start < data.length && Math.abs(data[start]) < peak * 0.05) start++;
  start = Math.max(0, start - 2);
  const len = Math.min(data.length - start, Math.round(sr * MAX_IR_SECONDS));
  const out = data.slice(start, start + len);
  const fade = Math.min(len, Math.round(sr * FADE_SECONDS));
  for (let i = 0; i < fade; i++) out[len - 1 - i] *= 0.5 - 0.5 * Math.cos((Math.PI * i) / fade);
  let energy = 0;
  for (const v of out) energy += v * v;
  const g = 1 / Math.sqrt(energy);
  for (let i = 0; i < len; i++) out[i] *= g;
  return out;
}

export function toBuffer(ctx: BaseAudioContext, data: Float32Array): AudioBuffer {
  const buf = ctx.createBuffer(1, data.length, ctx.sampleRate);
  buf.copyToChannel(data as Float32Array<ArrayBuffer>, 0);
  return buf;
}

export async function builtinIr(ctx: BaseAudioContext, index: number): Promise<AudioBuffer> {
  const d = BUILTIN_CABS[index] ?? BUILTIN_CABS[0];
  return toBuffer(ctx, conditionIr(await renderDesign(d, ctx.sampleRate), ctx.sampleRate));
}

/** decodeAudioData resamples to the context rate; multi-channel IRs keep their first channel. */
export async function irFromFile(ctx: BaseAudioContext, bytes: ArrayBuffer): Promise<AudioBuffer> {
  const decoded = await ctx.decodeAudioData(bytes);
  return toBuffer(ctx, conditionIr(decoded.getChannelData(0), ctx.sampleRate));
}
