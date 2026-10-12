/**
 * Application state (Svelte runes) and the actions that keep the audio engine in sync with it.
 * Components read `rig`, `session` and `ui` directly and change things only through the actions.
 */

import { renderMicIr } from '../audio/cab-sim';
import { Engine, type LatencyInfo } from '../audio/engine';
import { BUILTIN_CABS } from '../audio/ir';
import { loadUserIr, saveUserIr, type StoredIr } from '../ir-store';
import { AMP_COMP_ON, AMP_OD_ON, PARAM, PARAMS, isAmpKnob, type ParamDef } from '../params';
import {
  FACTORY,
  deleteUserPreset,
  loadLastState,
  normalize,
  saveLastState,
  saveUserPreset,
  userPresets,
  type FxId,
  type Preset,
  type RigState,
} from './presets';

export type SceneId = 'pre' | 'amp' | 'cab' | 'post';

export const engine = new Engine();

const last = loadLastState();

export const rig: RigState = $state(last.state);

export const presets = $state({
  current: last.preset as string | null,
  dirty: false,
  user: userPresets(),
});

export const session = $state({
  running: false,
  starting: false,
  testing: false,
  withInput: false,
  latency: null as LatencyInfo | null,
  inputs: [] as MediaDeviceInfo[],
  outputs: [] as MediaDeviceInfo[],
  inputId: '',
  outputId: 'default',
  channel: 0,
  inputChannels: 1,
  userIr: null as StoredIr | null,
});

export const ui = $state({
  scene: 'amp' as SceneId,
  settings: false,
  tuner: false,
  tunerMute: true,
  tunerFreq: 0,
  toast: '',
});

// ---------- values ----------

export function getValue(key: string): number {
  return isAmpKnob(key) ? rig.amps[rig.model][key] : rig.values[key];
}

/** Value actually sent to the DSP: mixes of bypassed effects are sent as 0. */
function effective(def: ParamDef, v: number): number {
  if (def.key === 'delayMix' && !rig.on.delay) return 0;
  if (def.key === 'reverbMix' && !rig.on.reverb) return 0;
  return v;
}

function send(def: ParamDef): void {
  if (def.target === 'cab') {
    scheduleCab();
    return;
  }
  engine.setParam(def, effective(def, getValue(def.key)));
}

export function setValue(key: string, v: number): void {
  const def = PARAM[key];
  if (isAmpKnob(key)) rig.amps[rig.model][key] = v;
  else rig.values[key] = v;
  send(def);
  changed();
}

export function selectModel(i: number): void {
  if (i === rig.model) return;
  rig.model = i;
  engine.setModel(i);
  for (const def of PARAMS) if (isAmpKnob(def.key)) send(def);
  if (rig.cab.cabinet === -1) void applyCab();
  changed();
}

export function toggleFx(id: FxId): void {
  rig.on[id] = !rig.on[id];
  sendSwitch(id);
  changed();
}

function sendSwitch(id: FxId): void {
  if (id === 'comp') engine.setRaw('amp', AMP_COMP_ON, rig.on.comp ? 1 : 0);
  else if (id === 'od') engine.setRaw('amp', AMP_OD_ON, rig.on.od ? 1 : 0);
  else send(PARAM[`${id}Mix`]);
}

function pushAll(): void {
  engine.setModel(rig.model);
  for (const def of PARAMS) if (def.target !== 'cab') send(def);
  for (const id of ['comp', 'od'] as const) sendSwitch(id);
  engine.setTuner(ui.tuner, ui.tunerMute);
}

// ---------- cabinet ----------

/** Cabinet that goes with each amp when the cab is set to follow the amp. */
const AMP_CABINET = [2, 1, 0];

export function activeCabinet(): number {
  return rig.cab.cabinet === -1 ? AMP_CABINET[rig.model] : rig.cab.cabinet;
}

export const CABINETS = BUILTIN_CABS.map((c) => c.name);

let cabTimer = 0;
function scheduleCab(): void {
  clearTimeout(cabTimer);
  cabTimer = window.setTimeout(() => void applyCab(), 60);
}

let cabSeq = 0;
export async function applyCab(): Promise<void> {
  if (!engine.running) return;
  // IR renders are async: only the most recent request may reach the engine.
  const seq = ++cabSeq;
  const latest = () => seq === cabSeq;
  try {
    if (rig.cab.mode === 'off') await engine.setCab(null);
    else if (rig.cab.mode === 'ir' && session.userIr) await engine.setCab({ file: session.userIr.bytes.slice(0) });
    else {
      const ir = await renderMicIr(engine.ctx!, activeCabinet(), micSpecs());
      if (latest()) await engine.setCab({ ir });
    }
  } catch (e) {
    if (!latest()) return;
    toast(`IR illisible : ${(e as Error).message}`);
    rig.cab.mode = 'mics';
    await engine.setCab({ builtin: activeCabinet() });
  }
}

function micSpecs() {
  return rig.cab.mics.map((m, i) => ({
    type: m.type,
    r: Math.hypot(m.x, m.y),
    distCm: rig.values[`mic${i + 1}Dist`],
    levelDb: rig.values[`mic${i + 1}Level`],
  }));
}

export function setCab(patch: Partial<RigState['cab']>): void {
  Object.assign(rig.cab, patch);
  void applyCab();
  changed();
}

export function moveMic(i: 0 | 1, x: number, y: number): void {
  const r = Math.hypot(x, y);
  if (r > 1) {
    x /= r;
    y /= r;
  }
  rig.cab.mics[i].x = x;
  rig.cab.mics[i].y = y;
  scheduleCab();
  changed();
}

export async function loadIrFile(file: File): Promise<void> {
  session.userIr = { name: file.name.replace(/\.[^.]+$/, ''), bytes: await file.arrayBuffer() };
  void saveUserIr(session.userIr);
  setCab({ mode: 'ir' });
}

// ---------- presets & persistence ----------

let persistTimer = 0;
function changed(): void {
  presets.dirty = presets.current !== null;
  clearTimeout(persistTimer);
  persistTimer = window.setTimeout(() => saveLastState($state.snapshot(rig), presets.current), 300);
}

export function allPresets(): Preset[] {
  return [...FACTORY, ...presets.user];
}

export function loadPreset(p: Preset): void {
  const keepIr = p.state.cab.mode === 'ir' && !session.userIr;
  Object.assign(rig, normalize(structuredClone(p.state)));
  if (keepIr) rig.cab.mode = 'mics';
  presets.current = p.name;
  pushAll();
  void applyCab();
  changed();
  presets.dirty = false;
}

export function stepPreset(dir: 1 | -1): void {
  const list = allPresets();
  const i = list.findIndex((p) => p.name === presets.current);
  loadPreset(list[(i + dir + list.length) % list.length]);
}

export function savePreset(name: string): void {
  saveUserPreset(name, $state.snapshot(rig));
  presets.user = userPresets();
  presets.current = name;
  presets.dirty = false;
  changed();
  presets.dirty = false;
}

export function removePreset(name: string): void {
  deleteUserPreset(name);
  presets.user = userPresets();
  if (presets.current === name) presets.current = null;
}

export const isFactory = (name: string | null) => FACTORY.some((p) => p.name === name);

// ---------- audio session ----------

export async function start(withInput: boolean): Promise<boolean> {
  session.starting = true;
  try {
    await engine.start({ useMic: withInput, inputId: session.inputId || undefined, outputId: session.outputId, channel: session.channel });
    engine.onTuner = (f) => (ui.tunerFreq = f);
    session.running = true;
    session.withInput = withInput;
    session.inputChannels = engine.inputChannels;
    if (session.inputChannels < 2) session.channel = 0;
    pushAll();
    await applyCab();
    await refreshDevices();
    return true;
  } catch (e) {
    const err = e as DOMException;
    toast(
      err.name === 'NotAllowedError'
        ? "Accès à l'entrée audio refusé. Autorisez le micro pour ce site."
        : err.name === 'NotFoundError'
          ? 'Aucune entrée audio trouvée.'
          : `Impossible de démarrer : ${err.message}`,
    );
    session.running = false;
    return false;
  } finally {
    session.starting = false;
    session.testing = engine.testing;
  }
}

export async function stop(): Promise<void> {
  await engine.stop();
  session.running = false;
  session.testing = false;
  session.latency = null;
  ui.tunerFreq = 0;
}

export async function toggleTest(file?: File): Promise<void> {
  if (engine.testing && !file) {
    engine.stopTest();
  } else {
    if (!engine.running && !(await start(false))) return;
    try {
      await engine.startTest(file ? await file.arrayBuffer() : undefined);
    } catch {
      toast('Fichier audio illisible');
    }
  }
  session.testing = engine.testing;
}

export function setChannel(ch: number): void {
  session.channel = ch;
  engine.setChannel(ch);
}

export function setInputDevice(id: string): void {
  session.inputId = id;
  if (session.running && session.withInput) void start(true);
}

export function setOutputDevice(id: string): void {
  session.outputId = id;
  engine.setOutput(id).catch((err) => toast(`Sortie indisponible : ${err.message}`));
}

export async function refreshDevices(): Promise<void> {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const devices = await navigator.mediaDevices.enumerateDevices();
  const keep = (kind: MediaDeviceKind) => devices.filter((d) => d.kind === kind && d.deviceId && d.deviceId !== 'default');
  session.inputs = keep('audioinput');
  session.outputs = keep('audiooutput');
}

export async function measureRoundTrip(): Promise<void> {
  try {
    const ms = await engine.measureRoundTrip();
    toast(ms === null ? "Aucun retour détecté : reliez une sortie de l'interface à l'entrée choisie." : `Latence aller-retour mesurée : ${ms.toFixed(1)} ms`);
  } catch (e) {
    toast((e as Error).message);
  }
}

export function setTuner(open: boolean, mute = ui.tunerMute): void {
  ui.tuner = open;
  ui.tunerMute = mute;
  engine.setTuner(open, mute);
  if (!open) ui.tunerFreq = 0;
}

let toastTimer = 0;
export function toast(msg: string): void {
  ui.toast = msg;
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (ui.toast = ''), 5000);
}

// ---------- boot ----------

if (import.meta.env.DEV) Object.assign(window, { browsamp: { engine, rig, setValue, toggleFx, moveMic, selectModel } });

// Deep links: ?scene=cab, ?amp=2 (also handy for screenshots).
{
  const q = new URLSearchParams(location.search);
  const scene = q.get('scene');
  if (scene === 'pre' || scene === 'amp' || scene === 'cab' || scene === 'post') ui.scene = scene;
  const amp = Number(q.get('amp'));
  if (q.has('amp') && Number.isInteger(amp) && amp >= 0 && amp < rig.amps.length) rig.model = amp;
}

setInterval(() => {
  session.latency = engine.latency();
}, 1000);
navigator.mediaDevices?.addEventListener?.('devicechange', () => void refreshDevices());
void refreshDevices();
void loadUserIr().then((ir) => {
  session.userIr = ir;
  if (!ir && rig.cab.mode === 'ir') rig.cab.mode = 'mics';
});
