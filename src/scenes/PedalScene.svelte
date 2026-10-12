<script lang="ts">
  import FilmstripKnob from '../components/controls/FilmstripKnob.svelte';
  import Footswitch from '../components/controls/Footswitch.svelte';
  import Led from '../components/controls/Led.svelte';
  import Backdrop from '../components/Backdrop.svelte';
  import { LAYOUT } from '../lib/layout';
  import { getValue, rig, setValue, toggleFx } from '../lib/rig.svelte';
  import { PARAM } from '../params';

  interface Props {
    scene: 'pre' | 'post';
  }
  let { scene }: Props = $props();

  const P = LAYOUT.pedal;
  let pedals = $derived(LAYOUT.pedals.filter((p) => p.scene === scene));
</script>

<div class="board">
  <Backdrop name="board-{scene}" />
  {#each pedals as p (p.id)}
    {#each p.knobs as k (k.key)}
      <FilmstripKnob
        def={PARAM[k.key]}
        value={getValue(k.key)}
        onchange={(v) => setValue(k.key, v)}
        size={P.knobSize}
        sheet="pedal"
        x={p.cx + k.dx}
        y={p.cy + k.dy}
        label={null}
      />
    {/each}
    <Led on={rig.on[p.id]} x={p.cx + P.led.dx} y={p.cy + P.led.dy} size={34} glow />
    <Footswitch on={rig.on[p.id]} label="{p.name} on/off" x={p.cx + P.footswitch.dx} y={p.cy + P.footswitch.dy} r={P.footswitch.r} ontoggle={() => toggleFx(p.id)} />
  {/each}
</div>

<style>
  .board {
    position: absolute;
    inset: 0;
  }
</style>
