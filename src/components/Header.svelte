<script lang="ts">
  import { art } from '../lib/layout';
  import { engine, getValue, session, setTuner, setValue, start, stop, ui } from '../lib/rig.svelte';
  import { PARAM } from '../params';
  import FilmstripKnob from './controls/FilmstripKnob.svelte';
  import Meter from './controls/Meter.svelte';
  import Icon from './Icon.svelte';
  import PresetBrowser from './PresetBrowser.svelte';

  const strip = art('knob-header.webp');
  const KNOB = 46;

  let latencyMs = $derived.by(() => {
    const l = session.latency;
    return l ? ((l.input ?? 0) + l.base + l.output) * 1000 : null;
  });
</script>

<header class="header">
  <div class="brand">browsamp</div>

  <FilmstripKnob def={PARAM.input} value={getValue('input')} onchange={(v) => setValue('input', v)} size={KNOB} {strip} x={232} y={34} labelDy={36} labelClass="hlabel" />
  <div class="meter-slot" style:left="264px"><Meter source={() => (session.running ? engine.inAnalyser : null)} height={48} /></div>
  <FilmstripKnob def={PARAM.gate} value={getValue('gate')} onchange={(v) => setValue('gate', v)} size={KNOB} {strip} x={322} y={34} labelDy={36} labelClass="hlabel" />

  <button class="chip tuner" class:on={ui.tuner} onclick={() => setTuner(!ui.tuner)} title="Accordeur">
    <Icon name="tuner" size={22} />
  </button>

  <PresetBrowser />

  <div class="right">
    <button class="power" class:on={session.running} disabled={session.starting} onclick={() => (session.running ? stop() : start(true))} title={session.running ? "Arrêter l'audio" : "Démarrer l'audio"}>
      <Icon name="power" size={18} />
      <span>{session.starting ? 'Démarrage…' : session.running ? (session.withInput ? 'En marche' : 'Sans entrée') : 'Démarrer'}</span>
    </button>
    {#if latencyMs !== null}
      <div class="latency" class:warn={latencyMs > 20} title="Latence annoncée par le navigateur (entrée + traitement + sortie)">
        {latencyMs.toFixed(1)} ms
        <small>{((session.latency?.sampleRate ?? 0) / 1000).toFixed(1)} kHz</small>
      </div>
    {/if}
    <button class="chip" onclick={() => (ui.settings = true)} title="Réglages audio"><Icon name="gear" size={22} /></button>
  </div>

  <FilmstripKnob def={PARAM.output} value={getValue('output')} onchange={(v) => setValue('output', v)} size={KNOB} {strip} x={1530} y={34} labelDy={36} labelClass="hlabel" />
  <div class="meter-slot" style:left="1562px"><Meter source={() => (session.running ? engine.outAnalyser : null)} height={48} /></div>
</header>

<style>
  .header {
    position: absolute;
    inset: 0 0 auto 0;
    height: 84px;
    background: linear-gradient(180deg, rgba(14, 13, 12, 0.96), rgba(14, 13, 12, 0.82));
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(6px);
    z-index: 10;
  }
  .brand {
    position: absolute;
    left: 28px;
    top: 26px;
    font: 600 26px/1 var(--brand-font);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #f3ede4;
  }
  .brand::first-letter {
    color: var(--accent);
  }
  :global(.hlabel) {
    font: 500 11px/1 var(--ui-font);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #a39a8e;
  }
  .meter-slot {
    position: absolute;
    top: 12px;
  }
  .chip {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.04);
    color: #d8d0c4;
    cursor: pointer;
  }
  .chip:hover {
    background: rgba(255, 255, 255, 0.08);
  }
  .chip.on {
    color: var(--accent);
    border-color: var(--accent);
  }
  .tuner {
    position: absolute;
    left: 372px;
    top: 20px;
  }
  .right {
    position: absolute;
    right: 128px;
    top: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .power {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 44px;
    padding: 0 16px;
    border-radius: 10px;
    border: 1px solid var(--accent);
    background: var(--accent);
    color: #1b1408;
    font: 600 15px/1 var(--ui-font);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .power.on {
    background: rgba(255, 255, 255, 0.04);
    color: #8fe39f;
    border-color: rgba(143, 227, 159, 0.5);
  }
  .power:disabled {
    opacity: 0.6;
  }
  .latency {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    font: 600 17px/1.1 var(--ui-font);
    color: #8fe39f;
    font-variant-numeric: tabular-nums;
  }
  .latency.warn {
    color: #e8b13c;
  }
  .latency small {
    font-size: 11px;
    color: #8a8176;
    letter-spacing: 0.08em;
  }
</style>
