<script lang="ts">
  // Development builds only (see App.svelte): play a synthetic riff or a DI file instead of
  // a guitar. Not part of the deployed app.
  import { session, toggleTest } from '../lib/rig.svelte';
  import Icon from './Icon.svelte';

  function onDi(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) void toggleTest(file);
  }
</script>

<div class="dev">
  <span class="tag">dev</span>
  <button class:on={session.testing} onclick={() => toggleTest()}>
    <Icon name={session.testing ? 'stop' : 'play'} size={14} />
    {session.testing ? 'Arrêter le test' : 'Signal de test'}
  </button>
  <label>DI…<input type="file" accept="audio/*" hidden onchange={onDi} /></label>
</div>

<style>
  .dev {
    position: absolute;
    left: 26px;
    bottom: 30px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border-radius: 10px;
    border: 1px dashed rgba(255, 200, 80, 0.5);
    background: rgba(12, 11, 10, 0.7);
    z-index: 10;
  }
  .tag {
    font: 700 11px/1 var(--ui-font);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #f0c060;
    padding: 0 4px;
  }
  button,
  label {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 10px;
    border-radius: 7px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(255, 255, 255, 0.05);
    color: #e2dbcf;
    font: 600 14px/1 var(--ui-font);
    cursor: pointer;
  }
  button.on {
    color: var(--accent);
    border-color: var(--accent);
  }
</style>
