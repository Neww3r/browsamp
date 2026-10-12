<script lang="ts">
  import { getValue, setValue } from '../lib/rig.svelte';
  import { PARAM } from '../params';
  import FilmstripKnob from './controls/FilmstripKnob.svelte';
  import Meter from './controls/Meter.svelte';

  interface Props {
    param: string;
    /** Analyser for the level meter beside the knob, if any. */
    meter?: () => AnalyserNode | null;
  }
  let { param, meter }: Props = $props();

  const SIZE = 54;
  let def = $derived(PARAM[param]);
</script>

<div class="global" class:with-meter={!!meter}>
  <div class="title">{def.label}</div>
  <div class="knob-slot">
    <FilmstripKnob {def} value={getValue(param)} onchange={(v) => setValue(param, v)} size={SIZE} sheet="header" x={SIZE / 2 + 8} y={SIZE / 2 + 6} label={null} showValue />
  </div>
  {#if meter}
    <div class="meter"><Meter source={meter} height={64} width={8} label={def.label} /></div>
  {/if}
</div>

<style>
  .global {
    position: relative;
    width: 72px;
    height: 112px;
  }
  .global.with-meter {
    width: 88px;
  }
  .title {
    position: absolute;
    left: 36px;
    top: 0;
    transform: translateX(-50%);
    font: 600 11px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #cfc7bb;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
    white-space: nowrap;
  }
  .knob-slot {
    position: absolute;
    left: 0;
    top: 16px;
    width: 72px;
    height: 96px;
  }
  .meter {
    position: absolute;
    left: 72px;
    top: 18px;
  }
</style>
