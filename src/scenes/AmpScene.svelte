<script lang="ts">
  import { fade } from 'svelte/transition';
  import Backdrop from '../components/Backdrop.svelte';
  import FilmstripKnob from '../components/controls/FilmstripKnob.svelte';
  import Led from '../components/controls/Led.svelte';
  import PowerSwitch from '../components/controls/PowerSwitch.svelte';
  import { LAYOUT } from '../lib/layout';
  import { getValue, rig, selectModel, session, setValue, togglePower } from '../lib/rig.svelte';
  import { PARAM } from '../params';

  const JEWEL = ['#ff3b2f', '#ff3b2f', '#3fa9ff'];
  let amp = $derived(LAYOUT.amps[rig.model]);

  /** Reads a knob on the numbers printed around it (1–12 on the tweed panel, 0–10 elsewhere). */
  function onScale(key: string) {
    const def = PARAM[key];
    const [lo, hi] = amp.scale;
    return (v: number) => (lo + ((v - def.min) / (def.max - def.min)) * (hi - lo)).toFixed(1);
  }
</script>

{#key rig.model}
  <div class="amp" transition:fade={{ duration: 220 }}>
    <Backdrop name="amp-{amp.id}" />
    {#each amp.knobs as k (k.key)}
      <FilmstripKnob
        def={PARAM[k.key]}
        value={getValue(k.key)}
        onchange={(v) => setValue(k.key, v)}
        size={amp.knobSize}
        sheet={amp.knobStyle}
        format={onScale(k.key)}
        x={k.x}
        y={amp.knobY}
        label={null}
      />
    {/each}
    <Led on={session.running} x={amp.jewel.x} y={amp.jewel.y} size={44} color={JEWEL[rig.model]} glow lens={17} />
    <PowerSwitch on={session.running} hint={!session.running || session.suspended} busy={session.starting} x={amp.power.x} y={amp.power.y} ontoggle={togglePower} />
  </div>
{/key}

<div class="selector" role="radiogroup" aria-label="Choix de l'ampli">
  {#each LAYOUT.amps as a, i (a.id)}
    <button class="pick" class:on={rig.model === i} role="radio" aria-checked={rig.model === i} onclick={() => selectModel(i)}>{a.voice}</button>
  {/each}
</div>

<style>
  .amp {
    position: absolute;
    inset: 0;
  }
  .selector {
    position: absolute;
    top: 150px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: rgba(10, 9, 8, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(8px);
    z-index: 2;
  }
  .pick {
    min-width: 116px;
    height: 38px;
    padding: 0 18px;
    border-radius: 999px;
    border: 0;
    background: none;
    color: #c4bcb0;
    font: 600 17px/1 var(--ui-font);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .pick:hover {
    color: #f3ede4;
  }
  .pick.on {
    background: rgba(255, 255, 255, 0.14);
    color: #fff;
  }
</style>
