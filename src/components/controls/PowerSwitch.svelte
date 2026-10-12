<script lang="ts">
  import { overlay } from '../../lib/assets.svelte';

  interface Props {
    on: boolean;
    busy?: boolean;
    x: number;
    y: number;
    ontoggle: () => void;
  }
  let { on, busy = false, x, y, ontoggle }: Props = $props();

  /** Rendered box in stage pixels (art/blender/switches.py TOGGLE_PX), centred on the pivot. */
  const BOX = 140;
  /** Clickable area: the lever's travel only, so the pilot lamp next to it is not a switch. */
  const HIT_W = 46;
  const HIT_H = 96;
</script>

<div
  class="art"
  style:left="{x - BOX / 2}px"
  style:top="{y - BOX / 2}px"
  style:width="{BOX}px"
  style:height="{BOX}px"
  style:background-image="url({overlay(on ? 'toggle-on' : 'toggle-off')})"
></div>
<button
  class="power"
  class:hint={!on && !busy}
  class:busy
  style:left="{x - HIT_W / 2}px"
  style:top="{y - HIT_H / 2}px"
  style:width="{HIT_W}px"
  style:height="{HIT_H}px"
  role="switch"
  aria-checked={on}
  aria-label={on ? "Éteindre l'ampli" : "Allumer l'ampli"}
  title={on ? "Éteindre l'ampli" : "Allumer l'ampli"}
  disabled={busy}
  onclick={ontoggle}
></button>

<style>
  .art {
    position: absolute;
    background: transparent center / 100% 100% no-repeat;
    pointer-events: none;
  }
  .power {
    position: absolute;
    border: 0;
    padding: 0;
    background: none;
    cursor: pointer;
    border-radius: 23px;
  }
  /* While the amp is off, a soft pulse around the pivot shows where to start. */
  .power.hint::before {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    width: 40px;
    height: 40px;
    margin: -20px 0 0 -20px;
    border-radius: 50%;
    animation: halo 2.2s ease-out infinite;
  }
  @keyframes halo {
    0% {
      box-shadow: 0 0 0 0 color-mix(in srgb, var(--accent) 60%, transparent);
    }
    70%,
    100% {
      box-shadow: 0 0 0 22px transparent;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .power.hint::before {
      animation: none;
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 50%, transparent);
    }
  }
  .power.busy {
    cursor: progress;
  }
  .power:focus-visible {
    outline: 3px solid var(--accent);
    outline-offset: 2px;
  }
</style>
