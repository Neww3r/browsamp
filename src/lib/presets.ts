import { AMP_KNOBS, PARAMS, isAmpKnob, type AmpKnob } from '../params';

export type MicType = 0 | 1; // 0 = dynamic, 1 = ribbon
export type FxId = 'comp' | 'od' | 'delay' | 'reverb';

export interface MicState {
  type: MicType;
  /** Position on the speaker, normalized to the cone radius (0,0 = dust cap). */
  x: number;
  y: number;
}

export interface RigState {
  v: 2;
  model: number;
  /** One set of knob values per amp model. */
  amps: Record<AmpKnob, number>[];
  /** Every other parameter, keyed like PARAMS. */
  values: Record<string, number>;
  on: Record<FxId, boolean>;
  cab: {
    mode: 'mics' | 'ir' | 'off';
    /** -1 = the cabinet that goes with the current amp. */
    cabinet: number;
    mics: [MicState, MicState];
  };
}

export interface Preset {
  name: string;
  state: RigState;
  factory?: boolean;
}

const defaults = (keys: readonly string[]) =>
  Object.fromEntries(PARAMS.filter((p) => keys.includes(p.key)).map((p) => [p.key, p.def]));

export function defaultRig(): RigState {
  const ampDefaults = defaults(AMP_KNOBS) as Record<AmpKnob, number>;
  return {
    v: 2,
    model: 1,
    amps: [0, 1, 2].map(() => ({ ...ampDefaults })),
    values: defaults(PARAMS.filter((p) => !isAmpKnob(p.key)).map((p) => p.key)),
    on: { comp: false, od: false, delay: false, reverb: true },
    cab: {
      mode: 'mics',
      cabinet: -1,
      mics: [
        { type: 0, x: 0.22, y: -0.12 },
        { type: 1, x: -0.45, y: 0.3 },
      ],
    },
  };
}

/** Fills in anything added since a state was saved, and upgrades v1 states. */
export function normalize(input: unknown): RigState {
  const d = defaultRig();
  if (!input || typeof input !== 'object') return d;
  const s = input as Partial<RigState> & { values?: Record<string, number> };
  if (s.v !== 2) return fromV1(s as unknown as V1State);
  return {
    ...d,
    ...s,
    amps: d.amps.map((a, i) => ({ ...a, ...(s.amps?.[i] ?? {}) })),
    values: { ...d.values, ...(s.values ?? {}) },
    on: { ...d.on, ...(s.on ?? {}) },
    cab: { ...d.cab, ...(s.cab ?? {}), mics: (s.cab?.mics ?? d.cab.mics).map((m, i) => ({ ...d.cab.mics[i], ...m })) as [MicState, MicState] },
  };
}

interface V1State {
  model?: number;
  cab?: string;
  delayOn?: boolean;
  reverbOn?: boolean;
  values?: Record<string, number>;
}

function fromV1(s: V1State): RigState {
  const r = defaultRig();
  r.model = s.model ?? r.model;
  for (const [k, v] of Object.entries(s.values ?? {})) {
    if (isAmpKnob(k)) r.amps[r.model][k] = v;
    else if (k in r.values) r.values[k] = v;
  }
  r.on.delay = !!s.delayOn;
  r.on.reverb = s.reverbOn ?? true;
  if (s.cab === 'off') r.cab.mode = 'off';
  else if (s.cab === 'user') r.cab.mode = 'ir';
  return r;
}

function preset(name: string, model: number, amp: Partial<Record<AmpKnob, number>>, extra: (r: RigState) => void = () => {}): Preset {
  const r = defaultRig();
  r.model = model;
  Object.assign(r.amps[model], amp);
  extra(r);
  return { name, state: r, factory: true };
}

export const FACTORY: Preset[] = [
  preset('Glass Clean', 0, { gain: 4, bass: 5.5, mid: 4.5, treble: 6.5, presence: 6, master: 4 }, (r) => {
    r.on.comp = true;
    r.values.reverbMix = 25;
  }),
  preset('Pushed Tweed', 0, { gain: 8.5, bass: 5, mid: 6, treble: 6, master: 7 }, (r) => {
    r.values.reverbMix = 15;
    r.values.output = -16; // a cranked clean amp is much louder than at noon
  }),
  preset('Brit Crunch', 1, { gain: 5.5, bass: 5, mid: 7, treble: 6, presence: 5.5, master: 6 }, (r) => {
    r.values.reverbMix = 15;
  }),
  preset('Rock Lead', 1, { gain: 9, bass: 5, mid: 7.5, treble: 6, master: 7 }, (r) => {
    r.on.delay = true;
    r.values.delayMix = 22;
    r.values.delayTime = 420;
  }),
  preset('Tight Rhythm', 2, { gain: 6.5, bass: 6, mid: 4.5, treble: 6, presence: 6, resonance: 6, master: 5 }, (r) => {
    r.on.od = true;
    r.values.odDrive = 0;
    r.values.odLevel = 8;
    r.values.gate = -62;
    r.values.reverbMix = 8;
    r.values.output = -6;
  }),
  preset('Obsidian Lead', 2, { gain: 8, bass: 5, mid: 6.5, treble: 5.5, master: 5 }, (r) => {
    r.values.gate = -66;
    r.values.output = -6;
    r.on.delay = true;
    r.values.delayMix = 25;
    r.values.delayTime = 480;
    r.values.reverbMix = 22;
  }),
];

const USER_KEY = 'browsamp.presets.v2';
const LAST_KEY = 'browsamp.state.v2';
const V1_USER_KEY = 'browsamp.presets.v1';
const V1_LAST_KEY = 'browsamp.state.v1';

function read<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full or disabled: presets just won't persist
  }
}

export function userPresets(): Preset[] {
  let list = read<{ name: string; state: unknown }[]>(USER_KEY);
  if (list === null) {
    // One-time import of v1 presets.
    list = read<{ name: string; state: unknown }[]>(V1_USER_KEY) ?? [];
    if (list.length) write(USER_KEY, list.map((p) => ({ name: p.name, state: normalize(p.state) })));
  }
  return list.map((p) => ({ name: p.name, state: normalize(p.state) }));
}

export function saveUserPreset(name: string, state: RigState): void {
  const list = userPresets().filter((p) => p.name !== name);
  list.push({ name, state: structuredClone(state) });
  list.sort((a, b) => a.name.localeCompare(b.name));
  write(USER_KEY, list);
}

export function deleteUserPreset(name: string): void {
  write(USER_KEY, userPresets().filter((p) => p.name !== name));
}

export function loadLastState(): { state: RigState; preset: string | null } {
  const saved = read<{ state: unknown; preset: string | null }>(LAST_KEY);
  if (saved) return { state: normalize(saved.state), preset: saved.preset };
  return { state: normalize(read(V1_LAST_KEY)), preset: null };
}

export function saveLastState(state: RigState, preset: string | null): void {
  write(LAST_KEY, { state, preset });
}
