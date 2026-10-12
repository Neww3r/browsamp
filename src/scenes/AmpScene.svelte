<script lang="ts">
  import { fade } from 'svelte/transition';
  import FilmstripKnob from '../components/controls/FilmstripKnob.svelte';
  import Led from '../components/controls/Led.svelte';
  import { LAYOUT, art } from '../lib/layout';
  import { getValue, rig, selectModel, session, setValue } from '../lib/rig.svelte';
  import { PARAM } from '../params';

  const JEWEL = ['#ff3b2f', '#ff3b2f', '#3fa9ff'];
  let amp = $derived(LAYOUT.amps[rig.model]);
</script>

{#key rig.model}
  <div class="amp amp-{amp.id}" transition:fade={{ duration: 220 }}>
    <img class="bg" src={art(`amp-${amp.id}.webp`)} alt="" draggable="false" />
    {#each amp.knobs as k (k.key)}
      <FilmstripKnob
        def={PARAM[k.key]}
        value={getValue(k.key)}
        onchange={(v) => setValue(k.key, v)}
        size={amp.knobSize}
        strip={art(`knob-${amp.knobStyle}.webp`)}
        x={k.x}
        y={amp.knobY}
        label={null}
      />
    {/each}
    <Led on={session.running} x={amp.jewel.x} y={amp.jewel.y} size={40} color={JEWEL[rig.model]} glow />
  </div>
{/key}

<div class="selector" role="radiogroup" aria-label="Choix de l'ampli">
  {#each LAYOUT.amps as a, i (a.id)}
    <button class="pick pick-{a.id}" class:on={rig.model === i} role="radio" aria-checked={rig.model === i} onclick={() => selectModel(i)}>
      <span class="pname">{a.name}</span>
      <span class="pvoice">{a.voice}</span>
    </button>
  {/each}
</div>

<style>
  .amp {
    position: absolute;
    inset: 0;
  }
  .bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    user-select: none;
  }

  /* ---- amp selector ---- */
  .selector {
    position: absolute;
    top: 118px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 10px;
    padding: 6px;
    border-radius: 14px;
    background: rgba(10, 9, 8, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(8px);
    z-index: 2;
  }
  .pick {
    display: grid;
    gap: 3px;
    width: 196px;
    padding: 10px 14px;
    border-radius: 10px;
    border: 1px solid transparent;
    background: none;
    color: #a39a8e;
    cursor: pointer;
    text-align: center;
  }
  .pick:hover {
    background: rgba(255, 255, 255, 0.05);
  }
  .pick.on {
    color: #f3ede4;
    background: rgba(255, 255, 255, 0.07);
    border-color: color-mix(in srgb, var(--accent) 60%, transparent);
  }
  .pname {
    font: 600 21px/1 var(--ui-font);
  }
  .pvoice {
    font: 500 13px/1 var(--body-font);
    color: #8a8176;
  }
</style>
