<script lang="ts">
  import { fade } from 'svelte/transition';
  import ChainBar from './components/ChainBar.svelte';
  import Header from './components/Header.svelte';
  import SettingsModal from './components/SettingsModal.svelte';
  import TunerOverlay from './components/TunerOverlay.svelte';
  import { LAYOUT } from './lib/layout';
  import { ui } from './lib/rig.svelte';
  import AmpScene from './scenes/AmpScene.svelte';
  import CabScene from './scenes/CabScene.svelte';
  import PedalScene from './scenes/PedalScene.svelte';

  const { w: W, h: H } = LAYOUT.stage;
  let vw = $state(window.innerWidth);
  let vh = $state(window.innerHeight);
  let scale = $derived(Math.min(vw / W, vh / H));
  // In portrait on a phone the stage would shrink to a quarter of its size.
  let portraitDismissed = $state(false);
  let portrait = $derived(vw < 700 && vh > vw && !portraitDismissed);
</script>

<svelte:window bind:innerWidth={vw} bind:innerHeight={vh} />

{#if portrait}
  <div class="rotate" role="dialog" aria-label="Orientation">
    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <rect x="7" y="2" width="10" height="20" rx="2" /><path d="M3 9a9 9 0 0 1 4-5M21 15a9 9 0 0 1-4 5" />
    </svg>
    <p>Tournez l'appareil à l'horizontale : l'ampli est fait pour un écran large.</p>
    <button class="btn" onclick={() => (portraitDismissed = true)}>Continuer quand même</button>
  </div>
{/if}

<div class="viewport">
  <div class="stage" style:width="{W}px" style:height="{H}px" style:transform="translate(-50%, -50%) scale({scale})">
    {#key ui.scene}
      <main class="scene" transition:fade={{ duration: 200 }}>
        {#if ui.scene === 'amp'}
          <AmpScene />
        {:else if ui.scene === 'cab'}
          <CabScene />
        {:else}
          <PedalScene scene={ui.scene} />
        {/if}
      </main>
    {/key}

    <Header />
    <ChainBar />

    {#if ui.tuner}<TunerOverlay />{/if}
    {#if ui.settings}<SettingsModal />{/if}
    {#if ui.toast}
      <div class="toast" role="status" transition:fade={{ duration: 150 }}>{ui.toast}</div>
    {/if}
  </div>
</div>

<style>
  .viewport {
    position: fixed;
    inset: 0;
    overflow: hidden;
    background: #070606;
  }
  .stage {
    position: absolute;
    left: 50%;
    top: 50%;
    transform-origin: center;
    overflow: hidden;
    background: #121110;
  }
  .scene {
    position: absolute;
    inset: 0;
  }
  .rotate {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 22px;
    padding: 32px;
    text-align: center;
    background: #0d0c0b;
    color: #e8e1d6;
  }
  .rotate svg {
    color: var(--accent);
  }
  .rotate p {
    margin: 0;
    max-width: 300px;
    font: 17px/1.5 var(--body-font);
  }
  .toast {
    position: absolute;
    left: 50%;
    bottom: 120px;
    transform: translateX(-50%);
    max-width: 900px;
    padding: 14px 22px;
    border-radius: 12px;
    background: #1d1b18;
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    font: 17px/1.4 var(--body-font);
    color: #f3ede4;
    z-index: 40;
  }
</style>
