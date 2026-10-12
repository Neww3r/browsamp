<script lang="ts">
  import { FACTORY } from '../lib/presets';
  import { exportPresets, importPresets, isFactory, loadPreset, presets, removePreset, savePreset, stepPreset } from '../lib/rig.svelte';
  import Icon from './Icon.svelte';

  let open = $state(false);
  let saving = $state(false);
  let name = $state('');
  let input: HTMLInputElement | undefined = $state();

  function startSave() {
    name = presets.current && !isFactory(presets.current) ? presets.current : '';
    saving = true;
    open = false;
    queueMicrotask(() => input?.select());
  }
  function confirmSave(e: Event) {
    e.preventDefault();
    const n = name.trim();
    if (!n) return;
    if (isFactory(n)) {
      name = `${n} (perso)`;
      return;
    }
    savePreset(n);
    saving = false;
  }
  function onImport(e: Event) {
    const el = e.target as HTMLInputElement;
    const file = el.files?.[0];
    el.value = '';
    open = false;
    if (file) void importPresets(file);
  }
</script>

<div class="browser">
  <button class="arrow" onclick={() => stepPreset(-1)} aria-label="Preset précédent"><Icon name="prev" /></button>
  <button class="name" onclick={() => (open = !open)} aria-expanded={open}>
    <span class="text">{presets.current ?? 'Sans titre'}{presets.dirty ? ' *' : ''}</span>
    <Icon name="chevron" size={16} />
  </button>
  <button class="arrow" onclick={() => stepPreset(1)} aria-label="Preset suivant"><Icon name="next" /></button>
  <button class="arrow" onclick={startSave} aria-label="Enregistrer le preset" title="Enregistrer"><Icon name="save" /></button>

  {#if open}
    <div class="menu" role="listbox">
      <div class="group">Usine</div>
      {#each FACTORY as p (p.name)}
        <button class="item" class:sel={p.name === presets.current} onclick={() => { loadPreset(p); open = false; }}>{p.name}</button>
      {/each}
      {#if presets.user.length}
        <div class="group">Mes presets</div>
        {#each presets.user as p (p.name)}
          <div class="row">
            <button class="item" class:sel={p.name === presets.current} onclick={() => { loadPreset(p); open = false; }}>{p.name}</button>
            <button class="del" aria-label="Supprimer {p.name}" onclick={() => removePreset(p.name)}><Icon name="close" size={14} /></button>
          </div>
        {/each}
      {/if}
      <div class="sep"></div>
      <button class="item tool" onclick={() => { exportPresets('current'); open = false; }}><Icon name="download" size={16} /> Exporter ce preset</button>
      <button class="item tool" disabled={!presets.user.length} onclick={() => { exportPresets('all'); open = false; }}><Icon name="download" size={16} /> Exporter tous mes presets</button>
      <label class="item tool"><Icon name="upload" size={16} /> Importer des presets…<input type="file" accept=".json,application/json" hidden onchange={onImport} /></label>
    </div>
  {/if}

  {#if saving}
    <form class="menu save" onsubmit={confirmSave}>
      <label for="preset-name">Nom du preset</label>
      <input id="preset-name" bind:this={input} bind:value={name} maxlength="40" />
      <div class="actions">
        <button type="button" class="btn" onclick={() => (saving = false)}>Annuler</button>
        <button type="submit" class="btn primary">Enregistrer</button>
      </div>
    </form>
  {/if}
</div>

<svelte:window onkeydown={(e) => e.key === 'Escape' && ((open = false), (saving = false))} />

<style>
  .browser {
    position: absolute;
    left: 50%;
    top: 26px;
    width: 470px;
    transform: translateX(-50%);
    display: flex;
    gap: 6px;
    z-index: 11;
  }
  .arrow,
  .name {
    height: 44px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(12, 11, 10, 0.5);
    backdrop-filter: blur(8px);
    color: #e2dbcf;
    cursor: pointer;
  }
  .arrow {
    width: 44px;
    display: grid;
    place-items: center;
  }
  .arrow:hover,
  .name:hover {
    background: rgba(12, 11, 10, 0.72);
  }
  .sep {
    height: 1px;
    margin: 8px 6px;
    background: rgba(255, 255, 255, 0.08);
  }
  .tool {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #c8bfb3;
  }
  .tool:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .name {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 0 14px;
    font: 600 19px/1 var(--ui-font);
    color: #f3ede4;
    min-width: 0;
  }
  .text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .menu {
    position: absolute;
    top: 52px;
    left: 50px;
    right: 100px;
    max-height: 560px;
    overflow: auto;
    padding: 8px;
    border-radius: 12px;
    background: #191715;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.6);
    z-index: 20;
  }
  .group {
    padding: 10px 10px 6px;
    font: 600 12px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8a8176;
  }
  .row {
    display: flex;
  }
  .item {
    flex: 1;
    display: block;
    width: 100%;
    text-align: left;
    padding: 10px 12px;
    border: 0;
    border-radius: 8px;
    background: none;
    color: #e8e1d6;
    font: 15px/1.2 var(--body-font);
    cursor: pointer;
  }
  .item:hover {
    background: rgba(255, 255, 255, 0.06);
  }
  .item.sel {
    color: var(--accent);
  }
  .del {
    border: 0;
    background: none;
    color: #8a8176;
    padding: 0 10px;
    cursor: pointer;
  }
  .del:hover {
    color: #e5483c;
  }
  .save {
    display: grid;
    gap: 10px;
    padding: 16px;
  }
  .save label {
    font: 600 14px/1 var(--ui-font);
    color: #a39a8e;
  }
  .save input {
    height: 40px;
    padding: 0 12px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    background: #0f0e0d;
    color: #f3ede4;
    font: 16px var(--body-font);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
</style>
