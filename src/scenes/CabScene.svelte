<script lang="ts">
  import FilmstripKnob from '../components/controls/FilmstripKnob.svelte';
  import Icon from '../components/Icon.svelte';
  import Backdrop from '../components/Backdrop.svelte';
  import { overlay } from '../lib/assets.svelte';
  import { LAYOUT } from '../lib/layout';
  import type { MicType } from '../lib/presets';
  import { CABINETS, activeCabinet, getValue, loadIrFile, moveMic, rig, session, setCab, setValue } from '../lib/rig.svelte';
  import { PARAM } from '../params';

  const S = LAYOUT.cab.speaker;
  const PANEL = LAYOUT.cab.panel;
  const MIC_IMG = ['mic-dynamic', 'mic-ribbon'];
  const MIC_NAME = ['Dynamique', 'Ruban'];

  let area: HTMLDivElement | undefined = $state();
  let dragging = $state<0 | 1 | null>(null);
  let micsActive = $derived(rig.cab.mode === 'mics');

  function toSpeaker(e: PointerEvent): [number, number] {
    const r = area!.getBoundingClientRect();
    return [((e.clientX - r.left) / r.width) * 2 - 1, ((e.clientY - r.top) / r.height) * 2 - 1];
  }
  function down(i: 0 | 1, e: PointerEvent) {
    if (!micsActive) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragging = i;
    e.preventDefault();
  }
  function move(i: 0 | 1, e: PointerEvent) {
    if (dragging !== i) return;
    moveMic(i, ...toSpeaker(e));
  }
  function up() {
    dragging = null;
  }

  function onIrFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) void loadIrFile(file);
  }

  const micLabel = (i: number) => {
    const m = rig.cab.mics[i];
    const r = Math.min(1, Math.hypot(m.x, m.y));
    return r < 0.12 ? 'centre du cône' : r > 0.88 ? 'bord du cône' : `${Math.round(r * 100)} % vers le bord`;
  };

  let mic2On = $derived(getValue('mic2Level') > -29.9);
  function toggleMic2() {
    setValue('mic2Level', mic2On ? -30 : -6);
  }
</script>

<div class="cab" class:dim={!micsActive}>
  <Backdrop name="cab" />

  <div class="speaker" bind:this={area} style:left="{S.cx - S.r}px" style:top="{S.cy - S.r}px" style:width="{S.r * 2}px" style:height="{S.r * 2}px">
    {#each rig.cab.mics as m, i (i)}
      {@const idx = i as 0 | 1}
      {#if i === 0 || getValue('mic2Level') > -29.9}
        <div
          class="mic"
          class:drag={dragging === i}
          style:left="{50 + m.x * 50}%"
          style:top="{50 + m.y * 50}%"
          style:background-image="url({overlay(MIC_IMG[m.type])})"
        ></div>
        <!-- The grab handle sits on the capsule: that point is what the mic "hears". -->
        <button
          class="grab"
          class:drag={dragging === i}
          style:left="{50 + m.x * 50}%"
          style:top="{50 + m.y * 50}%"
          aria-label="Micro {i + 1}, position {micLabel(i)}"
          onpointerdown={(e) => down(idx, e)}
          onpointermove={(e) => move(idx, e)}
          onpointerup={up}
          onpointercancel={up}
          onkeydown={(e) => {
            const d = 0.04;
            const k: Record<string, [number, number]> = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] };
            if (k[e.key]) {
              e.preventDefault();
              moveMic(idx, m.x + k[e.key][0], m.y + k[e.key][1]);
            }
          }}
        >
          <span class="tag">{i + 1}</span>
        </button>
      {/if}
    {/each}
  </div>

  <aside class="panel" style:left="{PANEL.x}px" style:top="{PANEL.y}px" style:width="{PANEL.w}px" style:max-height="{PANEL.h}px">
    <div class="seg" role="radiogroup" aria-label="Source du baffle">
      {#each [['mics', 'Micros'], ['ir', 'IR perso'], ['off', 'Bypass']] as [mode, label] (mode)}
        <button
          role="radio"
          aria-checked={rig.cab.mode === mode}
          class:on={rig.cab.mode === mode}
          disabled={mode === 'ir' && !session.userIr}
          title={mode === 'ir' && !session.userIr ? 'Chargez d’abord une IR (.wav) avec le bouton en bas du panneau' : undefined}
          onclick={() => setCab({ mode: mode as 'mics' | 'ir' | 'off' })}>{label}</button
        >
      {/each}
    </div>

    {#if rig.cab.mode === 'ir'}
      <p class="hint">Réponse impulsionnelle chargée : <b>{session.userIr?.name ?? '—'}</b></p>
    {:else if rig.cab.mode === 'off'}
      <p class="hint">Baffle désactivé : pour jouer dans un vrai baffle ou un chargeur d’IR externe.</p>
    {/if}

    {#if micsActive}
    <label class="field">
      <span>Baffle</span>
      <select value={rig.cab.cabinet} onchange={(e) => setCab({ cabinet: Number((e.target as HTMLSelectElement).value) })}>
        <option value={-1}>Auto ({CABINETS[activeCabinet()]})</option>
        {#each CABINETS as name, i (name)}
          <option value={i}>{name}</option>
        {/each}
      </select>
    </label>
    {/if}

    {#if micsActive}
      {#each [0, 1] as i (i)}
        {@const enabled = i === 0 || mic2On}
        <section class="micbox" class:off={!enabled}>
          <header>
            <span class="num">{i + 1}</span>
            <span class="title">Micro {i + 1}</span>
            {#if i === 1}
              <button class="switch" role="switch" aria-checked={mic2On} aria-label="Activer le micro 2" title={mic2On ? 'Désactiver le micro 2' : 'Ajouter un second micro'} onclick={toggleMic2}></button>
            {/if}
          </header>
          {#if enabled}
            <div class="seg small" role="radiogroup" aria-label="Type du micro {i + 1}">
              {#each [0, 1] as t (t)}
                <button role="radio" aria-checked={rig.cab.mics[i].type === t} class:on={rig.cab.mics[i].type === t} onclick={() => ((rig.cab.mics[i].type = t as MicType), setCab({}))}>{MIC_NAME[t]}</button>
              {/each}
            </div>
            <p class="pos">Position : <b>{micLabel(i)}</b></p>
            <div class="knobs">
              {#each [`mic${i + 1}Dist`, `mic${i + 1}Level`] as key, j (key)}
                <FilmstripKnob
                  def={PARAM[key]}
                  value={getValue(key)}
                  onchange={(v) => setValue(key, v)}
                  size={54}
                  sheet="header"
                  x={100 + j * 170}
                  y={50}
                  labelDy={-42}
                  labelClass="cab-label"
                  showValue
                />
              {/each}
            </div>
          {:else}
            <p class="hint">Un second micro, mélangé au premier, élargit le son (par exemple dynamique au centre et ruban sur le bord).</p>
          {/if}
        </section>
      {/each}
      <p class="hint">Glissez les micros sur le haut-parleur : vers le centre le son est plus brillant, vers le bord plus doux.</p>
    {/if}

    <label class="load">
      <Icon name="upload" size={18} /> Charger une IR (.wav)
      <input type="file" accept=".wav,audio/*" hidden onchange={onIrFile} />
    </label>
  </aside>
</div>

<style>
  .cab {
    position: absolute;
    inset: 0;
  }
  .speaker {
    position: absolute;
    border-radius: 50%;
  }
  .dim .speaker {
    opacity: 0.35;
    filter: grayscale(1);
  }
  /* Images are 320x360 with the capsule 34px above the bottom centre: that point is the position. */
  .mic {
    position: absolute;
    width: 320px;
    height: 360px;
    transform: translate(-50%, calc(-100% + 34px));
    background: transparent center / contain no-repeat;
    pointer-events: none;
    filter: drop-shadow(14px 22px 16px rgba(0, 0, 0, 0.65));
    transition: filter 0.15s;
  }
  .mic.drag {
    filter: drop-shadow(22px 34px 22px rgba(0, 0, 0, 0.7));
  }
  .grab {
    position: absolute;
    width: 84px;
    height: 84px;
    transform: translate(-50%, -50%);
    border: 2px dashed transparent;
    border-radius: 50%;
    padding: 0;
    background: none;
    cursor: grab;
    touch-action: none;
  }
  .grab:hover,
  .grab.drag {
    border-color: color-mix(in srgb, var(--accent) 70%, transparent);
  }
  .grab.drag {
    cursor: grabbing;
  }
  .grab:focus-visible {
    outline: 3px solid var(--accent);
    outline-offset: 2px;
  }
  .tag {
    position: absolute;
    left: -14px;
    top: -14px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--accent);
    color: #1b1408;
    font: 700 15px/1 var(--ui-font);
  }

  .panel {
    position: absolute;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 22px;
    border-radius: 18px;
    background: rgba(14, 13, 12, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .seg {
    display: flex;
    padding: 4px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
  }
  .seg button {
    flex: 1;
    height: 38px;
    border: 0;
    border-radius: 7px;
    background: none;
    color: #a39a8e;
    font: 600 15px/1 var(--ui-font);
    cursor: pointer;
  }
  .seg button.on {
    background: var(--accent);
    color: #1b1408;
  }
  .seg button:disabled {
    opacity: 0.35;
    cursor: default;
  }
  .seg.small button {
    height: 30px;
    font-size: 13px;
  }
  .hint {
    margin: 0;
    font: 14px/1.45 var(--body-font);
    color: #a39a8e;
  }
  .hint b {
    color: #e8e1d6;
    font-weight: 600;
  }
  .field {
    display: grid;
    gap: 6px;
    font: 600 12px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8a8176;
  }
  select {
    height: 40px;
    padding: 0 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: #121110;
    color: #f3ede4;
    font: 15px var(--body-font);
  }
  .micbox {
    display: grid;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .micbox header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title {
    flex: 1;
    font: 600 16px/1 var(--ui-font);
    color: #e8e1d6;
  }
  .micbox.off .num {
    background: #4a443d;
  }
  .micbox.off .title {
    color: #8a8176;
  }
  .switch {
    position: relative;
    width: 42px;
    height: 24px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    background: rgba(255, 255, 255, 0.06);
    cursor: pointer;
  }
  .switch::after {
    content: '';
    position: absolute;
    top: 3px;
    left: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #8a8176;
    transition: transform 0.15s, background 0.15s;
  }
  .switch[aria-checked='true'] {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 25%, transparent);
  }
  .switch[aria-checked='true']::after {
    transform: translateX(18px);
    background: var(--accent);
  }
  .num {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--accent);
    color: #1b1408;
    font: 700 15px/1 var(--ui-font);
  }
  .pos {
    margin: 0;
    font: 14px/1 var(--body-font);
    color: #a39a8e;
  }
  .pos b {
    color: #e8e1d6;
    font-weight: 600;
  }
  .knobs {
    position: relative;
    height: 104px;
    margin-top: 6px;
  }
  .cab :global(.cab-label) {
    font: 600 11px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #a39a8e;
  }
  .load {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    height: 44px;
    border-radius: 10px;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    color: #d8d0c4;
    font: 600 15px/1 var(--ui-font);
    cursor: pointer;
  }
  .load:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
