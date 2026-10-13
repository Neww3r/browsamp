<script lang="ts">
  import { fade } from 'svelte/transition';
  import { Engine } from '../audio/engine';
  import { measureRoundTrip, session, setChannel, setInputDevice, setOutputDevice, ui } from '../lib/rig.svelte';
  import Icon from './Icon.svelte';

  let measuring = $state(false);
  const ms = (s: number | null | undefined) => (s == null ? '?' : (s * 1000).toFixed(1));

  async function rtt() {
    measuring = true;
    await measureRoundTrip();
    measuring = false;
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

  <section class="keys">
    <h3>Raccourcis</h3>
    <dl>
      <div><dt>1 – 4</dt><dd>Pédales, ampli, baffle, effets</dd></div>
      <div><dt>T</dt><dd>Accordeur</dd></div>
      <div><dt>Molette</dt><dd>Tourner un potard (avec Maj ou Cmd : réglage fin)</dd></div>
      <div><dt>Double-clic</dt><dd>Valeur par défaut</dd></div>
    </dl>
  </section>

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
      <p>Allumez l'ampli pour voir la latence.</p>
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
    font: 600 24px/1 var(--ui-font);
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
    /* minmax(0, …): a long device name must not widen its column past the dialog. */
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  label:not(.btn) {
    display: grid;
    gap: 7px;
    font: 600 12px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8a8176;
  }
  select {
    width: 100%;
    min-width: 0;
    text-overflow: ellipsis;
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
  .keys {
    display: grid;
    gap: 12px;
    padding-top: 18px;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
  }
  .keys dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 24px;
  }
  .keys div {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }
  .keys dt {
    flex: 0 0 auto;
    min-width: 34px;
    padding: 3px 7px;
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.08);
    color: #e8e1d6;
    text-align: center;
    letter-spacing: 0.02em;
    text-transform: none;
  }
  .keys dd {
    margin: 0;
    font: 14px/1.35 var(--body-font);
    color: #c8bfb3;
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
    font: 600 11px/1 var(--ui-font);
    letter-spacing: 0.08em;
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
