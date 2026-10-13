<script lang="ts">
  import { engine, session, setTuner, ui } from '../lib/rig.svelte';
  import GlobalKnob from './GlobalKnob.svelte';
  import Icon from './Icon.svelte';
  import PresetBrowser from './PresetBrowser.svelte';

  /** The measured round trip when there is one, else what the browser announces. */
  let latency = $derived.by(() => {
    if (session.measured !== null) return { ms: session.measured, partial: false, measured: true };
    const l = session.latency;
    if (!l) return null;
    // Firefox announces the output only: the real figure is higher.
    return { ms: ((l.input ?? 0) + (l.base ?? 0) + l.output) * 1000, partial: l.input === null || l.base === null, measured: false };
  });
</script>

<div class="left">
  <GlobalKnob param="input" meter={() => (session.running ? engine.inAnalyser : null)} />
  <GlobalKnob param="gate" />
</div>

<PresetBrowser />

<div class="right">
  {#if latency}
    <div
      class="latency"
      class:warn={latency.ms > 20}
      title={latency.measured
        ? 'Latence aller-retour mesurée avec un câble'
        : latency.partial
          ? "Ce navigateur n'annonce qu'une partie de la latence : mesurez l'aller-retour dans les réglages pour le vrai chiffre"
          : 'Latence annoncée par le navigateur (entrée + traitement + sortie)'}
    >
      <span>{latency.measured ? 'Mesurée' : 'Latence'}</span>{latency.partial ? '≥ ' : ''}{latency.ms.toFixed(1)} ms
    </div>
  {/if}
  <button class="round" class:on={ui.tuner} onclick={() => setTuner(!ui.tuner)} title="Accordeur (T)" aria-label="Accordeur">
    <Icon name="tuner" size={22} />
  </button>
  <button class="round" onclick={() => (ui.settings = true)} title="Réglages audio" aria-label="Réglages audio">
    <Icon name="gear" size={22} />
  </button>
  <GlobalKnob param="output" meter={() => (session.running ? engine.outAnalyser : null)} />
</div>

<style>
  .left,
  .right {
    position: absolute;
    top: 18px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    z-index: 10;
  }
  .left {
    left: 26px;
  }
  .right {
    right: 26px;
    align-items: center;
  }
  .round {
    display: grid;
    place-items: center;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(12, 11, 10, 0.5);
    backdrop-filter: blur(8px);
    color: #e2dbcf;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }
  .round:hover {
    background: rgba(12, 11, 10, 0.72);
  }
  .round.on {
    color: var(--accent);
    border-color: var(--accent);
  }
  .latency {
    display: grid;
    justify-items: end;
    gap: 4px;
    font: 600 15px/1 var(--ui-font);
    font-variant-numeric: tabular-nums;
    color: #a8e8b4;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
    margin-right: 4px;
  }
  .latency span {
    font: 600 10px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #a39a8e;
  }
  .latency.warn {
    color: #f0c060;
  }
</style>
