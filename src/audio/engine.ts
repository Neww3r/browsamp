/**
 * Audio graph:
 *   mic → splitter[channel] ─┐
 *   test loop ───────────────┴→ inputBus → amp (WASM) → cab (Convolver | bypass) → fx (WASM) → out
 *
 * Latency rules: the context runs at the device rate with the smallest latency hint, browser
 * voice processing is disabled, and every DSP block works inside the 128-frame render quantum.
 */

import workletUrl from './worklet.ts?worker&url';
import wasmUrl from '../wasm/dsp.wasm?url';
import { AMP_TUNER, AMP_TUNER_MUTE, type ParamDef } from '../params';
import type { WorkletMessage } from './worklet';
import { builtinIr, irFromFile } from './ir';

export interface StartOptions {
  inputId?: string;
  outputId?: string;
  channel: number;
  useMic: boolean;
}

export interface LatencyInfo {
  sampleRate: number;
  /** null: not reported by this browser (Firefox reports neither input nor processing). */
  input: number | null;
  base: number | null;
  output: number;
}

export type TunerListener = (freq: number, clarity: number) => void;

let wasmBytes: Promise<ArrayBuffer> | null = null;
function loadWasm(): Promise<ArrayBuffer> {
  wasmBytes ??= fetch(wasmUrl).then((r) => {
    if (!r.ok) throw new Error(`DSP introuvable (${r.status})`);
    return r.arrayBuffer();
  });
  return wasmBytes;
}

export class Engine {
  ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private micSource: MediaStreamAudioSourceNode | null = null;
  private splitter: ChannelSplitterNode | null = null;
  private inputBus!: GainNode;
  private amp!: AudioWorkletNode;
  private fx!: AudioWorkletNode;
  /** Two convolvers crossfaded on every IR change, so moving a mic never clicks. */
  private convolvers: ConvolverNode[] = [];
  private convGains: GainNode[] = [];
  private activeConv = 0;
  private cabBypass!: GainNode;
  private testGain!: GainNode;
  private testSource: AudioBufferSourceNode | null = null;
  private testBuffer: AudioBuffer | null = null;
  private loopback: AudioWorkletNode | null = null;
  inAnalyser!: AnalyserNode;
  outAnalyser!: AnalyserNode;
  onTuner: TunerListener | null = null;
  channel = 0;

  get running(): boolean {
    return this.ctx !== null;
  }

  async start(opts: StartOptions): Promise<void> {
    await this.stop();
    if (opts.useMic) {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: opts.inputId ? { exact: opts.inputId } : undefined,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          channelCount: { ideal: 2 },
          // Chrome-specific constraint, not in lib.dom yet.
          ...({ latency: { ideal: 0 } } as object),
        },
      });
    }
    const settings = this.stream?.getAudioTracks()[0]?.getSettings();
    // Run at the device rate: any resampling would add latency and cost CPU.
    const ctx = new AudioContext({ latencyHint: 0, sampleRate: settings?.sampleRate });
    this.ctx = ctx;
    try {
      if (opts.outputId) await this.setOutput(opts.outputId);
      const [bytes] = await Promise.all([loadWasm(), ctx.audioWorklet.addModule(workletUrl)]);

      this.inputBus = new GainNode(ctx);
      this.amp = new AudioWorkletNode(ctx, 'browsamp-amp', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
        channelCount: 1,
        channelCountMode: 'explicit',
        channelInterpretation: 'discrete',
        processorOptions: { wasm: bytes },
      });
      this.fx = new AudioWorkletNode(ctx, 'browsamp-fx', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [2],
        channelCount: 1,
        channelCountMode: 'explicit',
        channelInterpretation: 'speakers',
        processorOptions: { wasm: bytes },
      });
      this.convolvers = [0, 1].map(() => new ConvolverNode(ctx, { disableNormalization: true }));
      this.convGains = [0, 1].map(() => new GainNode(ctx, { gain: 0 }));
      this.activeConv = 0;
      this.cabBypass = new GainNode(ctx, { gain: 0 });
      this.testGain = new GainNode(ctx);
      this.inAnalyser = new AnalyserNode(ctx, { fftSize: 2048 });
      this.outAnalyser = new AnalyserNode(ctx, { fftSize: 2048 });

      this.testGain.connect(this.inputBus);
      this.inputBus.connect(this.amp);
      this.inputBus.connect(this.inAnalyser);
      this.convolvers.forEach((c, i) => {
        this.amp.connect(c);
        c.connect(this.convGains[i]).connect(this.fx);
      });
      this.amp.connect(this.cabBypass).connect(this.fx);
      this.fx.connect(ctx.destination);
      this.fx.connect(this.outAnalyser);

      if (this.stream) {
        this.micSource = new MediaStreamAudioSourceNode(ctx, { mediaStream: this.stream });
        this.setChannel(opts.channel);
      }

      this.amp.port.onmessage = (e: MessageEvent<{ type: string; freq: number; clarity: number }>) => {
        if (e.data.type === 'tuner') this.onTuner?.(e.data.freq, e.data.clarity);
      };
      // Not awaited: without a user gesture resume() stays pending until the next click.
      void ctx.resume();
    } catch (err) {
      await this.stop();
      throw err;
    }
  }

  async stop(): Promise<void> {
    this.stopTest();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.micSource = null;
    this.splitter = null;
    this.loopback = null;
    if (this.ctx) {
      for (const n of [this.amp, this.fx]) n?.port.postMessage({ type: 'dispose' } satisfies WorkletMessage);
      const ctx = this.ctx;
      this.ctx = null;
      await ctx.close();
    }
  }

  /** Number of channels the input device delivers (1 if unknown). */
  get inputChannels(): number {
    return this.stream?.getAudioTracks()[0]?.getSettings().channelCount ?? 1;
  }

  /** Picks which input of the interface carries the guitar. */
  setChannel(channel: number): void {
    this.channel = channel;
    if (!this.ctx || !this.micSource) return;
    this.micSource.disconnect();
    this.splitter?.disconnect();
    this.splitter = new ChannelSplitterNode(this.ctx, { numberOfOutputs: Math.max(2, this.inputChannels) });
    this.micSource.connect(this.splitter);
    this.splitter.connect(this.inputBus, this.activeChannel);
  }

  private get activeChannel(): number {
    return Math.min(this.channel, this.inputChannels - 1);
  }

  async setOutput(deviceId: string): Promise<void> {
    const ctx = this.ctx as (AudioContext & { setSinkId?: (id: string) => Promise<void> }) | null;
    if (ctx?.setSinkId) await ctx.setSinkId(deviceId === 'default' ? '' : deviceId);
  }

  static canSelectOutput(): boolean {
    return 'setSinkId' in AudioContext.prototype;
  }

  setParam(p: ParamDef, value: number): void {
    const node = p.target === 'amp' ? this.amp : this.fx;
    if (!this.ctx || !node) return;
    const msg: WorkletMessage = { type: 'param', id: p.id, value: p.toDsp ? p.toDsp(value) : value };
    node.port.postMessage(msg);
  }

  setRaw(target: 'amp' | 'fx', id: number, value: number): void {
    if (!this.ctx) return;
    (target === 'amp' ? this.amp : this.fx).port.postMessage({ type: 'param', id, value } satisfies WorkletMessage);
  }

  setModel(id: number): void {
    if (this.ctx) this.amp.port.postMessage({ type: 'model', id } satisfies WorkletMessage);
  }

  setTuner(on: boolean, mute: boolean): void {
    this.setRaw('amp', AMP_TUNER, on ? 1 : 0);
    this.setRaw('amp', AMP_TUNER_MUTE, mute ? 1 : 0);
  }

  /** Raised-cosine crossfade: zero slope at both ends, so the switch has no audible kink. */
  private fadeTo(target: GainNode, level: number): void {
    const ctx = this.ctx!;
    const t = ctx.currentTime + 0.005;
    const steps = 64;
    for (const g of [...this.convGains, this.cabBypass]) {
      const from = g.gain.value;
      const to = g === target ? level : 0;
      g.gain.cancelScheduledValues(0);
      g.gain.setValueAtTime(from, ctx.currentTime);
      if (Math.abs(to - from) < 1e-4) {
        g.gain.setValueAtTime(to, t);
        continue;
      }
      const curve = new Float32Array(steps);
      for (let i = 0; i < steps; i++) curve[i] = from + (to - from) * (0.5 - 0.5 * Math.cos((Math.PI * i) / (steps - 1)));
      g.gain.setValueCurveAtTime(curve, t, Engine.CAB_FADE_S);
    }
  }

  private static readonly CAB_FADE_S = 0.04;

  /**
   * Loads a cabinet IR into the idle convolver and crossfades to it (~30 ms).
   * `null` bypasses the cabinet (e.g. when going into a real cab or an external IR loader).
   */
  async setCab(source: { builtin: number } | { file: ArrayBuffer } | { ir: AudioBuffer } | null): Promise<void> {
    if (!this.ctx) return;
    if (source === null) {
      this.fadeTo(this.cabBypass, 0.5);
      return;
    }
    const buf =
      'ir' in source ? source.ir : 'builtin' in source ? await builtinIr(this.ctx, source.builtin) : await irFromFile(this.ctx, source.file);
    if (!this.ctx) return;
    const next = 1 - this.activeConv;
    this.convolvers[next].buffer = buf;
    this.activeConv = next;
    this.fadeTo(this.convGains[next], 1);
  }

  /** Development builds only: plays the synthetic riff (or a DI file) instead of the input. */
  async startTest(file?: ArrayBuffer): Promise<void> {
    // Statically false in production, so the test riff module is left out of the bundle.
    if (!import.meta.env.DEV || !this.ctx) return;
    this.stopTest();
    if (file) this.testBuffer = await this.ctx.decodeAudioData(file);
    // Loaded on demand: the test riff only exists in development builds.
    this.testBuffer ??= (await import('./test-source')).makeTestRiff(this.ctx);
    const src = new AudioBufferSourceNode(this.ctx, { buffer: this.testBuffer, loop: true });
    src.connect(this.testGain);
    src.start();
    this.testSource = src;
  }

  stopTest(): void {
    this.testSource?.stop();
    this.testSource?.disconnect();
    this.testSource = null;
  }

  get testing(): boolean {
    return this.testSource !== null;
  }

  latency(): LatencyInfo | null {
    if (!this.ctx) return null;
    const s = this.stream?.getAudioTracks()[0]?.getSettings() as (MediaTrackSettings & { latency?: number }) | undefined;
    return {
      sampleRate: this.ctx.sampleRate,
      input: s?.latency ?? null,
      // A render quantum is never 0 s long: 0 means "not reported".
      base: this.ctx.baseLatency || null,
      output: this.ctx.outputLatency ?? 0,
    };
  }

  /**
   * Measures the true round trip (output → cable → input) with a click, bypassing the amp.
   * Returns milliseconds, or null if nothing came back.
   */
  async measureRoundTrip(): Promise<number | null> {
    if (!this.ctx || !this.micSource) throw new Error("Allumez l'ampli avec une entrée audio pour mesurer la latence");
    const ctx = this.ctx;
    if (!this.loopback) {
      this.loopback = new AudioWorkletNode(ctx, 'browsamp-loopback', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
        channelCount: 1,
        channelCountMode: 'explicit',
        channelInterpretation: 'discrete',
      });
    }
    const lb = this.loopback;
    this.splitter!.connect(lb, this.activeChannel);
    lb.connect(ctx.destination);
    this.fx.disconnect(ctx.destination); // keep the amp out of the measurement
    try {
      const results: number[] = [];
      for (let i = 0; i < 5; i++) {
        const r = await new Promise<number | null>((resolve) => {
          lb.port.onmessage = (e: MessageEvent<{ type: string; samples?: number }>) =>
            resolve(e.data.type === 'result' ? e.data.samples! : null);
          lb.port.postMessage({ type: 'ping' });
        });
        if (r === null) return null;
        results.push(r);
        await new Promise((r) => setTimeout(r, 150));
      }
      results.sort((a, b) => a - b);
      return (results[2] / ctx.sampleRate) * 1000;
    } finally {
      this.splitter?.disconnect(lb);
      lb.disconnect();
      this.fx.connect(ctx.destination);
    }
  }
}
