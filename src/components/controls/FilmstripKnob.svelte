<script lang="ts">
  import { overlay } from '../../lib/assets.svelte';
  import { LAYOUT } from '../../lib/layout';
  import { fromNorm, toNorm, type ParamDef } from '../../params';

  interface Props {
    def: ParamDef;
    value: number;
    onchange: (v: number) => void;
    /** Diameter in stage pixels. */
    size: number;
    /** Knob style name: art/knob-{name}@{k}.webp, LAYOUT.frames frames in a grid, frame 0 = minimum. */
    sheet: string;
    /** Centre position in stage pixels (the parent is the stage-sized scene). */
    x: number;
    y: number;
    label?: string | null;
    labelDy?: number;
    labelClass?: string;
    /** Show the value under the knob permanently (global controls) instead of on hover. */
    showValue?: boolean;
    /** Overrides def.fmt, e.g. to read the value on the scale printed around the knob. */
    format?: (v: number) => string;
  }

  let { def, value, onchange, size, sheet, x, y, label = def.label, labelDy, labelClass = '', showValue = false, format }: Props = $props();

  const DRAG_PX = 240; // screen pixels for a full sweep
  let dragging = $state(false);
  let hovering = $state(false);

  const frames = LAYOUT.frames;
  const { cols, pad } = LAYOUT.knobStrip;
  const rows = Math.ceil(frames / cols);
  let frame = $derived(Math.round(toNorm(def, value) * (frames - 1)));
  // Frames include room for the baked drop shadow around the knob.
  let box = $derived(size * pad);
  let text = $derived((format ?? def.fmt)(value));

  function set(v: number) {
    v = Math.min(def.max, Math.max(def.min, v));
    if (v !== value) onchange(v);
  }

  function nudge(d: number) {
    set(fromNorm(def, toNorm(def, value) + d));
  }

  /** Fine adjustment: Shift, or Cmd / Ctrl as in most audio plug-ins. */
  const fine = (e: { shiftKey: boolean; metaKey: boolean; ctrlKey: boolean }) => e.shiftKey || e.metaKey || e.ctrlKey;

  let lastY = 0;
  /** Focused by a click: Chrome counts script focus as keyboard focus, so hide the ring ourselves. */
  let clicked = $state(false);
  function down(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    el.setPointerCapture(e.pointerId);
    // preventDefault below also prevents focus: give it explicitly so arrow keys work after a click.
    clicked = true;
    el.focus({ preventScroll: true });
    lastY = e.clientY;
    dragging = true;
    e.preventDefault();
  }
  function move(e: PointerEvent) {
    if (!dragging) return;
    const dy = lastY - e.clientY;
    lastY = e.clientY;
    nudge((dy / DRAG_PX) * (fine(e) ? 0.15 : 1));
  }
  function up(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
    dragging = false;
  }
  /**
   * Share of the full range per wheel event. A fixed step (not proportional to the delta)
   * so that every single notch registers, even on mice that report tiny deltas.
   */
  const WHEEL_STEP = 0.03;

  function wheel(e: WheelEvent) {
    e.preventDefault();
    // macOS turns Shift+wheel into horizontal scrolling: take whichever axis moved.
    const d = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
    if (d === 0) return;
    nudge(-Math.sign(d) * WHEEL_STEP * (fine(e) ? 0.2 : 1));
  }
  function key(e: KeyboardEvent) {
    const step = e.shiftKey ? 0.005 : 0.02;
    const map: Record<string, number> = { ArrowUp: step, ArrowRight: step, ArrowDown: -step, ArrowLeft: -step, PageUp: 0.1, PageDown: -0.1 };
    if (e.key in map) {
      e.preventDefault();
      nudge(map[e.key]);
    } else if (e.key === 'Home') set(def.min);
    else if (e.key === 'End') set(def.max);
  }
</script>

<div
  class="knob"
  class:active={dragging}
  style:left="{x - box / 2}px"
  style:top="{y - box / 2}px"
  style:width="{box}px"
  style:height="{box}px"
  style:background-image="url({overlay(`knob-${sheet}`)})"
  style:background-size="{cols * 100}% {rows * 100}%"
  style:background-position="{((frame % cols) / (cols - 1)) * 100}% {(Math.floor(frame / cols) / (rows - 1)) * 100}%"
  role="slider"
  tabindex="0"
  aria-label={def.label}
  aria-valuemin={def.min}
  aria-valuemax={def.max}
  aria-valuenow={value}
  aria-valuetext={text}
  onpointerdown={down}
  onpointermove={move}
  onpointerup={up}
  onpointercancel={up}
  onpointerenter={() => (hovering = true)}
  onpointerleave={() => (hovering = false)}
  ondblclick={() => set(def.def)}
  onwheel={wheel}
  onkeydown={key}
  onblur={() => (clicked = false)}
  class:clicked
></div>
{#if showValue}
  <div class="value" class:active={dragging || hovering} style:left="{x}px" style:top="{y + size / 2 + 8}px">{text}</div>
{:else if dragging || hovering}
  <div class="tip" style:left="{x}px" style:top="{y - size / 2 - 10}px"><span>{def.label}</span> {text}</div>
{/if}
{#if label}
  <div class="label {labelClass}" style:left="{x}px" style:top="{y + (labelDy ?? size / 2 + 10)}px">{label}</div>
{/if}

<style>
  .knob {
    position: absolute;
    background-repeat: no-repeat;
    cursor: ns-resize;
    touch-action: none;
    border-radius: 50%;
    outline-offset: -8px;
  }
  .knob:focus-visible {
    outline: 3px solid var(--accent);
  }
  .knob.clicked:focus-visible {
    outline: none;
  }
  .tip span {
    color: #a39a8e;
    font-weight: 500;
    margin-right: 4px;
  }
  .tip {
    position: absolute;
    transform: translate(-50%, -100%);
    padding: 5px 10px;
    border-radius: 6px;
    background: rgba(12, 11, 10, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #f3ede4;
    font: 600 15px/1 var(--ui-font);
    letter-spacing: 0.02em;
    white-space: nowrap;
    pointer-events: none;
    z-index: 5;
  }
  .value {
    position: absolute;
    transform: translateX(-50%);
    color: #d9d2c6;
    font: 600 14px/1 var(--ui-font);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    pointer-events: none;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
  }
  .value.active {
    color: var(--accent);
  }
  .label {
    position: absolute;
    transform: translate(-50%, -50%);
    white-space: nowrap;
    pointer-events: none;
  }
</style>
