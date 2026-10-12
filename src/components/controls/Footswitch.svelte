<script lang="ts">
  import { overlay } from '../../lib/assets.svelte';
  import { LAYOUT } from '../../lib/layout';

  interface Props {
    on: boolean;
    label: string;
    x: number;
    y: number;
    r: number;
    ontoggle: () => void;
  }
  let { on, label, x, y, r, ontoggle }: Props = $props();
  let pressed = $state(false);
  // The rendered image includes room for its drop shadow.
  let half = $derived(r * LAYOUT.knobStrip.pad);
</script>

<button
  class="fs"
  style:left="{x - half}px"
  style:top="{y - half}px"
  style:width="{half * 2}px"
  style:height="{half * 2}px"
  style:background-image="url({overlay(pressed ? 'footswitch-down' : 'footswitch-up')})"
  aria-pressed={on}
  aria-label={label}
  onpointerdown={() => (pressed = true)}
  onpointerup={() => (pressed = false)}
  onpointerleave={() => (pressed = false)}
  onclick={ontoggle}
></button>

<style>
  .fs {
    position: absolute;
    border: 0;
    padding: 0;
    border-radius: 50%;
    background-color: transparent;
    background-size: 100% 100%;
    cursor: pointer;
  }
  .fs:focus-visible {
    outline: 3px solid var(--accent);
    outline-offset: -10px;
  }
</style>
