<script lang="ts">
  import { rig, session, ui, type SceneId } from '../lib/rig.svelte';
  import Icon, { type IconName } from './Icon.svelte';

  const ITEMS: { id: SceneId; icon: IconName; title: string }[] = [
    { id: 'pre', icon: 'pedal', title: 'Pédales' },
    { id: 'amp', icon: 'amp', title: 'Ampli' },
    { id: 'cab', icon: 'cab', title: 'Baffle' },
    { id: 'post', icon: 'echo', title: 'Effets' },
  ];

  /** Lit when that part of the chain is doing something. */
  let active = $derived<Record<SceneId, boolean>>({
    pre: rig.on.comp || rig.on.od,
    amp: session.running,
    cab: rig.cab.mode !== 'off',
    post: rig.on.delay || rig.on.reverb,
  });
</script>

<nav class="nav" aria-label="Chaîne du signal">
  {#each ITEMS as item, i (item.id)}
    {#if i > 0}<span class="wire" class:live={session.running}></span>{/if}
    <button
      class="item"
      class:current={ui.scene === item.id}
      onclick={() => (ui.scene = item.id)}
      title={item.title}
      aria-label={item.title}
      aria-current={ui.scene === item.id ? 'page' : undefined}
    >
      <Icon name={item.icon} size={26} stroke={1.6} />
      <span class="led" class:on={active[item.id]}></span>
    </button>
  {/each}
</nav>

<style>
  .nav {
    position: absolute;
    left: 50%;
    bottom: 22px;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    z-index: 10;
  }
  .wire {
    width: 30px;
    height: 2px;
    background: rgba(255, 255, 255, 0.18);
  }
  .wire.live {
    background: color-mix(in srgb, var(--accent) 70%, transparent);
  }
  .item {
    position: relative;
    display: grid;
    place-items: center;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.16);
    background: rgba(12, 11, 10, 0.55);
    backdrop-filter: blur(8px);
    color: #bdb5a9;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background 0.15s, box-shadow 0.15s;
  }
  .item:hover {
    color: #f3ede4;
    background: rgba(12, 11, 10, 0.75);
  }
  .item.current {
    color: var(--accent);
    border-color: var(--accent);
    box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  }
  .led {
    position: absolute;
    top: 6px;
    right: 8px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #3a2422;
  }
  .led.on {
    background: #ff4a3a;
    box-shadow: 0 0 7px #ff4a3a;
  }
</style>
