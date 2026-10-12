<script lang="ts">
  import { untrack } from 'svelte';
  import { fade } from 'svelte/transition';
  import { session, setTuner, start, ui } from '../lib/rig.svelte';
  import Icon from './Icon.svelte';

  const NAMES = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'];
  const STRINGS = [
    { n: 'E', f: 82.41 },
    { n: 'A', f: 110 },
    { n: 'D', f: 146.83 },
    { n: 'G', f: 196 },
    { n: 'B', f: 246.94 },
    { n: 'E', f: 329.63 },
  ];

  let cents = $state(0);
  let note = $state<{ name: string; octave: number } | null>(null);
  let clearTimer = 0;

  // Each reading smooths against the previous one, so the update must not track its own state.
  $effect(() => {
    const f = ui.tunerFreq;
    untrack(() => update(f));
  });

  function update(f: number) {
    clearTimeout(clearTimer);
    if (f <= 0) {
      // YIN drops out briefly as a note decays: only clear after a pause.
      clearTimer = window.setTimeout(() => (note = null), 700);
      return;
    }
    const midi = 69 + 12 * Math.log2(f / 440);
    const n = Math.round(midi);
    const name = NAMES[((n % 12) + 12) % 12];
    const c = (midi - n) * 100;
    cents = note && note.name === name ? cents + (c - cents) * 0.4 : c;
    note = { name, octave: Math.floor(n / 12) - 1 };
  }

  let inTune = $derived(note !== null && Math.abs(cents) < 3);
  let nearest = $derived(ui.tunerFreq > 0 ? STRINGS.reduce((a, b) => (Math.abs(Math.log2(b.f / ui.tunerFreq)) < Math.abs(Math.log2(a.f / ui.tunerFreq)) ? b : a)) : null);
</script>

<div class="tuner" transition:fade={{ duration: 160 }} role="dialog" aria-label="Accordeur">
  <button class="close" onclick={() => setTuner(false)} aria-label="Fermer l'accordeur"><Icon name="close" size={26} /></button>

  <div class="strings">
    {#each STRINGS as s, i (i)}
      <span class:near={nearest === s}>{s.n}</span>
    {/each}
  </div>

  <div class="note" class:active={note} class:ok={inTune}>
    {#if note}{note.name}<sub>{note.octave}</sub>{:else}—{/if}
  </div>

  <div class="scale">
    {#each Array.from({ length: 21 }, (_, i) => i - 10) as t (t)}
      <span class="tick" class:major={t % 5 === 0} class:center={t === 0} style:left="{50 + t * 4.5}%"></span>
    {/each}
    {#if note}
      <span class="needle" class:ok={inTune} style:left="{50 + Math.max(-50, Math.min(50, cents)) * 0.9}%"></span>
    {/if}
    <span class="flat">♭</span><span class="sharp">♯</span>
  </div>

  <div class="readout">
    {#if note}{ui.tunerFreq.toFixed(1)} Hz · {cents >= 0 ? '+' : ''}{cents.toFixed(0)} cents{:else if !session.running}L'audio est arrêté{:else}Jouez une corde à vide{/if}
  </div>

  <div class="actions">
    {#if !session.running}
      <button class="btn primary" onclick={() => start(true)}>Démarrer l'audio</button>
    {/if}
    <label class="mute"><input type="checkbox" checked={ui.tunerMute} onchange={(e) => setTuner(true, (e.target as HTMLInputElement).checked)} /> Couper la sortie pendant l'accordage</label>
  </div>
</div>

<style>
  .tuner {
    position: absolute;
    inset: 84px 0 96px 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 34px;
    background: radial-gradient(800px 500px at 50% 45%, rgba(30, 27, 24, 0.97), rgba(9, 8, 8, 0.98));
    z-index: 20;
    color: #f3ede4;
  }
  .close {
    position: absolute;
    top: 24px;
    right: 28px;
    border: 0;
    background: none;
    color: #a39a8e;
    cursor: pointer;
  }
  .strings {
    display: flex;
    gap: 22px;
    font: 500 24px/1 var(--ui-font);
    color: #5d564e;
  }
  .strings .near {
    color: var(--accent);
  }
  .note {
    font: 600 220px/0.9 var(--ui-font);
    color: #4a443d;
    transition: color 0.15s;
  }
  .note sub {
    font-size: 64px;
    margin-left: 6px;
  }
  .note.active {
    color: #f3ede4;
  }
  .note.ok {
    color: #6fe08a;
    text-shadow: 0 0 40px rgba(111, 224, 138, 0.45);
  }
  .scale {
    position: relative;
    width: 900px;
    height: 70px;
  }
  .tick {
    position: absolute;
    top: 22px;
    width: 3px;
    height: 26px;
    margin-left: -1.5px;
    border-radius: 2px;
    background: #3c3731;
  }
  .tick.major {
    top: 14px;
    height: 42px;
    background: #5d564e;
  }
  .tick.center {
    top: 4px;
    height: 62px;
    width: 4px;
    background: #8a8176;
  }
  .needle {
    position: absolute;
    top: 0;
    width: 10px;
    height: 70px;
    margin-left: -5px;
    border-radius: 5px;
    background: #f0a33a;
    box-shadow: 0 0 18px rgba(240, 163, 58, 0.6);
    transition: left 0.08s linear;
  }
  .needle.ok {
    background: #6fe08a;
    box-shadow: 0 0 24px rgba(111, 224, 138, 0.7);
  }
  .flat,
  .sharp {
    position: absolute;
    top: 14px;
    font: 34px/1 var(--body-font);
    color: #5d564e;
  }
  .flat {
    left: -50px;
  }
  .sharp {
    right: -50px;
  }
  .readout {
    font: 500 22px/1 var(--ui-font);
    letter-spacing: 0.06em;
    color: #a39a8e;
    font-variant-numeric: tabular-nums;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .mute {
    display: flex;
    align-items: center;
    gap: 10px;
    font: 16px/1 var(--body-font);
    color: #c8bfb3;
  }
  .mute input {
    width: 18px;
    height: 18px;
    accent-color: var(--accent);
  }
</style>
