/// <reference path="./worklet-env.d.ts" />
// Runs on the audio rendering thread. Rules: no allocation and no await in process().

interface DspExports {
  memory: WebAssembly.Memory;
  max_block(): number;
  amp_init(sr: number): void;
  amp_in_ptr(): number;
  amp_out_ptr(): number;
  amp_process(n: number): void;
  amp_set_param(id: number, v: number): void;
  amp_set_model(id: number): void;
  amp_tuner_freq(): number;
  amp_tuner_clarity(): number;
  fx_init(sr: number): void;
  fx_in_ptr(): number;
  fx_out_l_ptr(): number;
  fx_out_r_ptr(): number;
  fx_process(n: number): void;
  fx_set_param(id: number, v: number): void;
}

export type WorkletMessage =
  | { type: 'param'; id: number; value: number }
  | { type: 'model'; id: number }
  | { type: 'dispose' };

function instantiate(options: AudioWorkletNodeOptions): DspExports {
  // Synchronous compile is allowed off the main thread, and the module is ~100 KB.
  const module = new WebAssembly.Module(options.processorOptions.wasm as ArrayBuffer);
  return new WebAssembly.Instance(module, {}).exports as unknown as DspExports;
}

/** Float32Array view into WASM memory, re-created only if memory ever grows. */
class View {
  private arr: Float32Array;
  private sub: Float32Array;
  constructor(private readonly ex: DspExports, private readonly ptr: number) {
    this.arr = new Float32Array(ex.memory.buffer, ptr, ex.max_block());
    this.sub = this.arr;
  }
  get(n: number): Float32Array {
    if (this.arr.buffer !== this.ex.memory.buffer) {
      this.arr = new Float32Array(this.ex.memory.buffer, this.ptr, this.ex.max_block());
      this.sub = this.arr;
    }
    if (this.sub.length !== n) this.sub = this.arr.subarray(0, n);
    return this.sub;
  }
}

class AmpProcessor extends AudioWorkletProcessor {
  private readonly ex: DspExports;
  private readonly inV: View;
  private readonly outV: View;
  private alive = true;
  private tunerCountdown = 0;
  private lastFreq = 0;

  constructor(options: AudioWorkletNodeOptions) {
    super(options);
    this.ex = instantiate(options);
    this.ex.amp_init(sampleRate);
    this.inV = new View(this.ex, this.ex.amp_in_ptr());
    this.outV = new View(this.ex, this.ex.amp_out_ptr());
    this.port.onmessage = (e: MessageEvent<WorkletMessage>) => {
      const m = e.data;
      if (m.type === 'param') this.ex.amp_set_param(m.id, m.value);
      else if (m.type === 'model') this.ex.amp_set_model(m.id);
      else if (m.type === 'dispose') this.alive = false;
    };
  }

  process(inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const out = outputs[0];
    const n = out[0].length;
    const inV = this.inV.get(n);
    const src = inputs[0];
    if (src.length > 0) inV.set(src[0]);
    else inV.fill(0);
    this.ex.amp_process(n);
    const outV = this.outV.get(n);
    for (let c = 0; c < out.length; c++) out[c].set(outV);

    this.tunerCountdown -= n;
    if (this.tunerCountdown <= 0) {
      this.tunerCountdown = sampleRate / 20;
      const freq = this.ex.amp_tuner_freq();
      if (freq > 0 || this.lastFreq > 0) {
        this.port.postMessage({ type: 'tuner', freq, clarity: this.ex.amp_tuner_clarity() });
      }
      this.lastFreq = freq;
    }
    return this.alive;
  }
}

class FxProcessor extends AudioWorkletProcessor {
  private readonly ex: DspExports;
  private readonly inV: View;
  private readonly outL: View;
  private readonly outR: View;
  private alive = true;

  constructor(options: AudioWorkletNodeOptions) {
    super(options);
    this.ex = instantiate(options);
    this.ex.fx_init(sampleRate);
    this.inV = new View(this.ex, this.ex.fx_in_ptr());
    this.outL = new View(this.ex, this.ex.fx_out_l_ptr());
    this.outR = new View(this.ex, this.ex.fx_out_r_ptr());
    this.port.onmessage = (e: MessageEvent<WorkletMessage>) => {
      const m = e.data;
      if (m.type === 'param') this.ex.fx_set_param(m.id, m.value);
      else if (m.type === 'dispose') this.alive = false;
    };
  }

  process(inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const out = outputs[0];
    const n = out[0].length;
    const inV = this.inV.get(n);
    const src = inputs[0];
    if (src.length > 0) inV.set(src[0]);
    else inV.fill(0);
    this.ex.fx_process(n);
    out[0].set(this.outL.get(n));
    if (out.length > 1) out[1].set(this.outR.get(n));
    return this.alive;
  }
}

/**
 * Round-trip latency probe: emits a click and timestamps (to the sample) when it comes back
 * on the input. Needs a physical loopback (cable from an output to an input of the interface).
 */
class LoopbackProcessor extends AudioWorkletProcessor {
  private state: 'idle' | 'waiting' = 'idle';
  private sentAt = 0;
  private pendingClick = false;
  private alive = true;

  constructor(options: AudioWorkletNodeOptions) {
    super(options);
    this.port.onmessage = (e: MessageEvent<{ type: string }>) => {
      if (e.data.type === 'ping') this.pendingClick = true;
      else if (e.data.type === 'dispose') this.alive = false;
    };
  }

  process(inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const out = outputs[0][0];
    const input = inputs[0].length > 0 ? inputs[0][0] : null;
    out.fill(0);
    if (this.pendingClick) {
      this.pendingClick = false;
      for (let i = 0; i < 4; i++) out[i] = 0.7;
      this.sentAt = currentFrame;
      this.state = 'waiting';
      return this.alive; // never detect our own click in the same block
    }
    if (this.state === 'waiting') {
      if (input) {
        for (let i = 0; i < input.length; i++) {
          if (Math.abs(input[i]) > 0.1) {
            this.port.postMessage({ type: 'result', samples: currentFrame + i - this.sentAt });
            this.state = 'idle';
            return this.alive;
          }
        }
      }
      if (currentFrame - this.sentAt > sampleRate) {
        this.port.postMessage({ type: 'timeout' });
        this.state = 'idle';
      }
    }
    return this.alive;
  }
}

registerProcessor('browsamp-amp', AmpProcessor);
registerProcessor('browsamp-fx', FxProcessor);
registerProcessor('browsamp-loopback', LoopbackProcessor);
