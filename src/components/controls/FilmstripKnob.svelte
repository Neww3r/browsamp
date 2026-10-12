<script lang="ts">
  import { LAYOUT } from '../../lib/layout';
  import { fromNorm, toNorm, type ParamDef } from '../../params';

  interface Props {
    def: ParamDef;
    value: number;
    onchange: (v: number) => void;
    /** Diameter in stage pixels. */
    size: number;
    /** Sprite sheet of LAYOUT.frames frames in a grid, frame 0 = minimum, row by row. */
    strip: string;
    /** Centre position in stage pixels (the parent is the stage-sized scene). */
    x: number;
    y: number;
    label?: string | null;
    labelDy?: number;
    labelClass?: string;
  }

  let { def, value, onchange, size, strip, x, y, label = def.label, labelDy, labelClass = '' }: Props = $props();

  const DRAG_PX = 240; // screen pixels for a full sweep
  let dragging = $state(false);
  let hovering = $state(false);

  const frames = LAYOUT.frames;
  const { cols, pad } = LAYOUT.knobStrip;
  const rows = Math.ceil(frames / cols);
  let frame = $derived(Math.round(toNorm(def, value) * (frames - 1)));
  // Frames include room for the baked drop shadow around the knob.
  let box = $derived(size * pad);
  let text = $derived(def.fmt(value));

  function set(v: number) {
    v = Math.min(def.max, Math.max(def.min, v));
    if (v !== value) onchange(v);
  }

  function nudge(d: number) {
    set(fromNorm(def, toNorm(def, value) + d));
  }

  let lastY = 0;
  function down(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    el.setPointerCapture(e.pointerId);
    // preventDefault below also prevents focus: give it explicitly so arrow keys work after a click.
    el.focus({ preventScroll: true });
    lastY = e.clientY;
    dragging = true;
    e.preventDefault();
  }
  function move(e: PointerEvent) {
    if (!dragging) return;
    const dy = lastY - e.clientY;
    lastY = e.clientY;
    nudge((dy / DRAG_PX) * (e.shiftKey ? 0.15 : 1));
  }
  function up(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
    dragging = false;
  }
  function wheel(e: WheelEvent) {
    e.preventDefault();
    nudge((-Math.sign(e.deltaY) / 50) * (e.shiftKey ? 0.2 : 1));
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
  style:background-image="url({strip})"
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
></div>
{#if dragging || hovering}
  <div class="tip" style:left="{x}px" style:top="{y - size / 2 - 10}px">{text}</div>
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
  .label {
    position: absolute;
    transform: translate(-50%, -50%);
    white-space: nowrap;
    pointer-events: none;
  }
</style>
