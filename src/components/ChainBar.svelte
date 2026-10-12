<script lang="ts">
  import { LAYOUT } from '../lib/layout';
  import { rig, session, toggleTest, ui, type SceneId } from '../lib/rig.svelte';
  import Icon, { type IconName } from './Icon.svelte';

  const amp = $derived(LAYOUT.amps[rig.model]);

  const blocks = $derived<{ id: SceneId; title: string; sub: string; icon: IconName; on: boolean }[]>([
    { id: 'pre', title: 'Pre-FX', sub: [rig.on.comp && 'Comp', rig.on.od && 'Drive'].filter(Boolean).join(' · ') || 'Bypass', icon: 'pedal', on: rig.on.comp || rig.on.od },
    { id: 'amp', title: amp.name, sub: amp.voice, icon: 'amp', on: true },
    { id: 'cab', title: 'Cab', sub: rig.cab.mode === 'off' ? 'Bypass' : rig.cab.mode === 'ir' ? 'IR perso' : 'Micros', icon: 'cab', on: rig.cab.mode !== 'off' },
    { id: 'post', title: 'Post-FX', sub: [rig.on.delay && 'Delay', rig.on.reverb && 'Reverb'].filter(Boolean).join(' · ') || 'Bypass', icon: 'post', on: rig.on.delay || rig.on.reverb },
  ]);
</script>

<nav class="chain" aria-label="Chaîne du signal">
  <button class="test" class:on={session.testing} onclick={() => toggleTest()} title="Boucle de guitare synthétique, sans instrument">
    <Icon name={session.testing ? 'stop' : 'play'} size={16} />
    {session.testing ? 'Arrêter le test' : 'Signal de test'}
  </button>

  <div class="blocks">
    {#each blocks as b, i (b.id)}
      {#if i > 0}<span class="wire" class:live={b.on}></span>{/if}
      <button class="block" class:active={ui.scene === b.id} onclick={() => (ui.scene = b.id)} aria-current={ui.scene === b.id ? 'page' : undefined}>
        <span class="led" class:on={b.on}></span>
        <Icon name={b.icon} size={22} />
        <span class="txt"><b>{b.title}</b><small>{b.sub}</small></span>
      </button>
    {/each}
  </div>
</nav>

<style>
  .chain {
    position: absolute;
    left: 0;
    right: 0;
    top: 904px;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(0deg, rgba(14, 13, 12, 0.97), rgba(14, 13, 12, 0.84));
    border-top: 1px solid rgba(255, 255, 255, 0.07);
    box-shadow: 0 -6px 24px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(6px);
    z-index: 10;
  }
  .blocks {
    display: flex;
    align-items: center;
  }
  .wire {
    width: 34px;
    height: 2px;
    background: #3a352f;
  }
  .wire.live {
    background: linear-gradient(90deg, #3a352f, var(--accent), #3a352f);
  }
  .block {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    width: 230px;
    height: 62px;
    padding: 0 16px 0 18px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.09);
    background: rgba(255, 255, 255, 0.03);
    color: #b9b0a4;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
  }
  .block:hover {
    background: rgba(255, 255, 255, 0.07);
  }
  .block.active {
    color: #f3ede4;
    border-color: color-mix(in srgb, var(--accent) 70%, transparent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    box-shadow: 0 0 24px color-mix(in srgb, var(--accent) 18%, transparent);
  }
  .txt {
    display: grid;
    gap: 4px;
    min-width: 0;
  }
  .txt b {
    font: 600 18px/1 var(--ui-font);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .txt small {
    font: 12px/1 var(--body-font);
    color: #8a8176;
    white-space: nowrap;
  }
  .led {
    position: absolute;
    top: 9px;
    right: 10px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #3a2422;
  }
  .led.on {
    background: #ff4a3a;
    box-shadow: 0 0 8px #ff4a3a;
  }
  .test {
    position: absolute;
    left: 28px;
    display: flex;
    align-items: center;
    gap: 8px;
    height: 40px;
    padding: 0 14px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.04);
    color: #d8d0c4;
    font: 600 15px/1 var(--ui-font);
    cursor: pointer;
  }
  .test.on {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
