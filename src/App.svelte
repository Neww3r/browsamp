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
</script>

<svelte:window bind:innerWidth={vw} bind:innerHeight={vh} />

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
