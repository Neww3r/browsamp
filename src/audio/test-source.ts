/**
 * A guitar-like DI loop for working without an instrument plugged in: Karplus-Strong
 * strings played as a short riff, at a typical pickup level (~-10 dBFS peaks).
 */

interface Note {
  t: number; // seconds
  midi: number[]; // several notes = strummed chord
  dur: number;
  mute?: boolean; // palm mute
}

const E2 = 40;
const RIFF: Note[] = [
  { t: 0.0, midi: [E2, E2 + 7, E2 + 12], dur: 1.2 },
  ...[1.25, 1.5, 1.75, 2.0, 2.25, 2.5].map((t) => ({ t, midi: [E2], dur: 0.22, mute: true })),
  { t: 2.75, midi: [E2 + 3, E2 + 10, E2 + 15], dur: 0.45 },
  { t: 3.25, midi: [E2 + 5, E2 + 12, E2 + 17], dur: 0.7 },
  ...[4.0, 4.25, 4.5].map((t) => ({ t, midi: [E2], dur: 0.22, mute: true })),
  { t: 4.75, midi: [E2 + 7, E2 + 14, E2 + 19], dur: 1.0 },
  // single-note lead line
  { t: 6.0, midi: [64], dur: 0.3 },
  { t: 6.3, midi: [67], dur: 0.3 },
  { t: 6.6, midi: [69], dur: 0.3 },
  { t: 6.9, midi: [71], dur: 0.9 },
  { t: 7.9, midi: [69], dur: 0.3 },
  { t: 8.2, midi: [67], dur: 1.2 },
];
const LENGTH_S = 9.6;

function pluck(out: Float32Array, sr: number, start: number, freq: number, dur: number, mute: boolean, seed: number) {
  // The two-point average reads the next (newer) ring slot, so the loop delay is
  // N - 0.5 + allpass fraction. The fraction stays in [0.5, 1.5), where a first-order
  // allpass is well behaved.
  const period = sr / freq;
  const n = Math.floor(period);
  const frac = period + 0.5 - n;
  const c = (1 - frac) / (1 + frac);
  const ring = new Float32Array(n);
  let s = seed;
  const rand = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296) * 2 - 1;
  // Pick excitation, low-passed for a softer attack; pick position comb at 1/7 of the string.
  let lp = 0;
  for (let i = 0; i < n; i++) {
    lp += (rand() - lp) * (mute ? 0.25 : 0.6);
    ring[i] = lp;
  }
  const pickOff = Math.max(1, Math.round(n / 7));
  for (let i = n - 1; i >= pickOff; i--) ring[i] -= ring[i - pickOff];

  const decay = mute ? 0.93 : 0.997;
  const end = Math.min(out.length, start + Math.round(dur * sr));
  const releaseLen = Math.round(0.02 * sr);
  let idx = 0;
  let x1 = 0;
  let y1 = 0;
  for (let t = start; t < end; t++) {
    const cur = ring[idx];
    const avg = decay * 0.5 * (cur + ring[(idx + 1) % n]);
    const ap = c * avg + x1 - c * y1;
    x1 = avg;
    y1 = ap;
    ring[idx] = ap;
    idx = (idx + 1) % n;
    const env = end - t < releaseLen ? (end - t) / releaseLen : 1;
    out[t] += cur * env;
  }
}

export function makeTestRiff(ctx: BaseAudioContext): AudioBuffer {
  const sr = ctx.sampleRate;
  const data = new Float32Array(Math.round(LENGTH_S * sr));
  let seed = 12345;
  for (const note of RIFF) {
    note.midi.forEach((m, k) => {
      const f = 440 * Math.pow(2, (m - 69) / 12);
      const start = Math.round((note.t + k * 0.012) * sr); // strum spread
      pluck(data, sr, start, f, note.dur, !!note.mute, seed++);
    });
  }
  let peak = 0;
  for (const v of data) peak = Math.max(peak, Math.abs(v));
  const g = 0.32 / peak;
  for (let i = 0; i < data.length; i++) data[i] *= g;
  const buf = ctx.createBuffer(1, data.length, sr);
  buf.copyToChannel(data, 0);
  return buf;
}
