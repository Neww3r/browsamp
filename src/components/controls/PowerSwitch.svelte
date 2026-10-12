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

  /** Rendered box in stage pixels (art/blender/switches.py TOGGLE_PX), centred on the bushing. */
  const BOX = 110;
</script>

<button
  class="power"
  class:busy
  style:left="{x - BOX / 2}px"
  style:top="{y - BOX / 2}px"
  style:width="{BOX}px"
  style:height="{BOX}px"
  style:background-image="url({overlay(on ? 'toggle-on' : 'toggle-off')})"
  role="switch"
  aria-checked={on}
  aria-label={on ? "Éteindre l'ampli" : "Allumer l'ampli"}
  title={on ? "Éteindre l'ampli" : "Allumer l'ampli"}
  disabled={busy}
  onclick={ontoggle}
></button>

<style>
  .power {
    position: absolute;
    border: 0;
    padding: 0;
    background: transparent center / 100% 100% no-repeat;
    cursor: pointer;
    border-radius: 50%;
  }
  .power.busy {
    cursor: progress;
  }
  .power:focus-visible {
    outline: 3px solid var(--accent);
    outline-offset: -26px;
  }
</style>
