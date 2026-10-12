<script lang="ts">
  import { fade } from 'svelte/transition';
  import { Engine } from '../audio/engine';
  import { measureRoundTrip, session, setChannel, setInputDevice, setOutputDevice, start, stop, toggleTest, ui } from '../lib/rig.svelte';
  import Icon from './Icon.svelte';

  let measuring = $state(false);
  const ms = (s: number | null | undefined) => (s == null ? '?' : (s * 1000).toFixed(1));

  async function rtt() {
    measuring = true;
    await measureRoundTrip();
    measuring = false;
  }
  function onDi(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) void toggleTest(file);
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (ui.settings = false)} />

<div class="scrim" transition:fade={{ duration: 150 }} onclick={() => (ui.settings = false)} role="presentation"></div>
<div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" transition:fade={{ duration: 150 }}>
  <header>
    <h2 id="settings-title">Réglages audio</h2>
    <button class="x" onclick={() => (ui.settings = false)} aria-label="Fermer"><Icon name="close" /></button>
  </header>

  <div class="grid">
    <label>
      <span>Entrée</span>
      <select value={session.inputId} onchange={(e) => setInputDevice((e.target as HTMLSelectElement).value)}>
        <option value="">Par défaut</option>
        {#each session.inputs as d, i (d.deviceId)}<option value={d.deviceId}>{d.label || `Entrée ${i + 1}`}</option>{/each}
      </select>
    </label>
    <label>
      <span>Canal de la guitare</span>
      <select value={session.channel} onchange={(e) => setChannel(Number((e.target as HTMLSelectElement).value))}>
        <option value={0}>Entrée 1</option>
        <option value={1} disabled={session.running && session.inputChannels < 2}>Entrée 2</option>
      </select>
    </label>
    {#if Engine.canSelectOutput()}
      <label>
        <span>Sortie</span>
        <select value={session.outputId} onchange={(e) => setOutputDevice((e.target as HTMLSelectElement).value)}>
          <option value="default">Par défaut</option>
          {#each session.outputs as d, i (d.deviceId)}<option value={d.deviceId}>{d.label || `Sortie ${i + 1}`}</option>{/each}
        </select>
      </label>
    {/if}
  </div>

  <div class="row">
    <button class="btn primary" disabled={session.starting} onclick={() => (session.running && session.withInput ? stop() : start(true))}>
      <Icon name="power" size={18} />
      {session.running && session.withInput ? "Arrêter l'audio" : 'Démarrer avec l’entrée'}
    </button>
    <button class="btn" onclick={() => toggleTest()}><Icon name={session.testing ? 'stop' : 'play'} size={16} /> {session.testing ? 'Arrêter le test' : 'Signal de test'}</button>
    <label class="btn">DI…<input type="file" accept="audio/*" hidden onchange={onDi} /></label>
  </div>

  <section class="lat">
    <h3>Latence</h3>
    {#if session.latency}
      <dl>
        <div><dt>Fréquence</dt><dd>{(session.latency.sampleRate / 1000).toFixed(1)} kHz</dd></div>
        <div><dt>Entrée</dt><dd>{ms(session.latency.input)} ms</dd></div>
        <div><dt>Traitement</dt><dd>{ms(session.latency.base)} ms</dd></div>
        <div><dt>Sortie</dt><dd>{ms(session.latency.output)} ms</dd></div>
      </dl>
    {:else}
      <p>Démarrez l'audio pour voir la latence.</p>
    {/if}
    <button class="btn" disabled={!session.running || !session.withInput || measuring} onclick={rtt}>
      {measuring ? 'Mesure…' : "Mesurer l'aller-retour"}
    </button>
    <p class="hint">Reliez une sortie de l'interface à l'entrée choisie avec un câble, et baissez le volume : la mesure envoie un clic. Pour une latence minimale, branchez le casque sur l'interface, réglez-la à 48 kHz et réduisez son buffer au minimum.</p>
  </section>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    background: rgba(6, 5, 5, 0.6);
    z-index: 30;
  }
  .modal {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 720px;
    display: grid;
    gap: 22px;
    padding: 28px 32px 30px;
    border-radius: 18px;
    background: #181614;
    border: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: 0 30px 90px rgba(0, 0, 0, 0.7);
    color: #e8e1d6;
    z-index: 31;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  h2,
  h3 {
    margin: 0;
    font: 500 22px/1 var(--ui-font);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  h3 {
    font-size: 15px;
    color: #a39a8e;
  }
  .x {
    border: 0;
    background: none;
    color: #a39a8e;
    cursor: pointer;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  label:not(.btn) {
    display: grid;
    gap: 7px;
    font: 500 12px/1 var(--ui-font);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8a8176;
  }
  select {
    height: 42px;
    padding: 0 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: #0f0e0d;
    color: #f3ede4;
    font: 15px var(--body-font);
    text-transform: none;
    letter-spacing: 0;
  }
  .row {
    display: flex;
    gap: 10px;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .lat {
    display: grid;
    gap: 14px;
    padding-top: 18px;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
    justify-items: start;
  }
  dl {
    display: flex;
    gap: 34px;
    margin: 0;
  }
  dt {
    font: 500 11px/1 var(--ui-font);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8a8176;
  }
  dd {
    margin: 6px 0 0;
    font: 600 20px/1 var(--ui-font);
    font-variant-numeric: tabular-nums;
  }
  p {
    margin: 0;
    font: 14px/1.5 var(--body-font);
    color: #a39a8e;
  }
  .hint {
    font-size: 13px;
  }
</style>
