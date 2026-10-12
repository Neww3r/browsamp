<script lang="ts">
  import FilmstripKnob from '../components/controls/FilmstripKnob.svelte';
  import Icon from '../components/Icon.svelte';
  import { LAYOUT, art } from '../lib/layout';
  import type { MicType } from '../lib/presets';
  import { CABINETS, activeCabinet, getValue, loadIrFile, moveMic, rig, session, setCab, setValue } from '../lib/rig.svelte';
  import { PARAM } from '../params';

  const S = LAYOUT.cab.speaker;
  const PANEL = LAYOUT.cab.panel;
  const MIC_IMG = ['mic-dynamic.webp', 'mic-ribbon.webp'];
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
    return r < 0.15 ? 'Centre' : r > 0.8 ? 'Bord' : `${Math.round(r * 100)} %`;
  };
</script>

<div class="cab" class:dim={!micsActive}>
  <img class="bg" src={art('cab.webp')} alt="" draggable="false" />

  <div class="speaker" bind:this={area} style:left="{S.cx - S.r}px" style:top="{S.cy - S.r}px" style:width="{S.r * 2}px" style:height="{S.r * 2}px">
    {#each rig.cab.mics as m, i (i)}
      {@const idx = i as 0 | 1}
      {#if i === 0 || getValue('mic2Level') > -29.9}
        <div
          class="mic"
          class:drag={dragging === i}
          style:left="{50 + m.x * 50}%"
          style:top="{50 + m.y * 50}%"
          style:background-image="url({art(MIC_IMG[m.type])})"
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

  <aside class="panel" style:left="{PANEL.x}px" style:top="{PANEL.y}px" style:width="{PANEL.w}px" style:height="{PANEL.h}px">
    <div class="seg" role="radiogroup" aria-label="Source du baffle">
      {#each [['mics', 'Micros'], ['ir', 'IR perso'], ['off', 'Bypass']] as [mode, label] (mode)}
        <button
          role="radio"
          aria-checked={rig.cab.mode === mode}
          class:on={rig.cab.mode === mode}
          disabled={mode === 'ir' && !session.userIr}
          onclick={() => setCab({ mode: mode as 'mics' | 'ir' | 'off' })}>{label}</button
        >
      {/each}
    </div>

    {#if rig.cab.mode === 'ir' || !micsActive}
      <div class="ir">
        <p>{rig.cab.mode === 'off' ? 'Baffle désactivé : pour un baffle réel ou un chargeur d’IR externe.' : `IR : ${session.userIr?.name ?? '—'}`}</p>
      </div>
    {/if}

    <label class="field">
      <span>Baffle</span>
      <select value={rig.cab.cabinet} disabled={!micsActive} onchange={(e) => setCab({ cabinet: Number((e.target as HTMLSelectElement).value) })}>
        <option value={-1}>Auto ({CABINETS[activeCabinet()]})</option>
        {#each CABINETS as name, i (name)}
          <option value={i}>{name}</option>
        {/each}
      </select>
    </label>

    {#each [0, 1] as i (i)}
      <section class="micbox" class:off={i === 1 && getValue('mic2Level') <= -29.9}>
        <header>
          <span class="num">{i + 1}</span>
          <div class="seg small">
            {#each [0, 1] as t (t)}
              <button class:on={rig.cab.mics[i].type === t} disabled={!micsActive} onclick={() => ((rig.cab.mics[i].type = t as MicType), setCab({}))}>{MIC_NAME[t]}</button>
            {/each}
          </div>
          <span class="pos">{micLabel(i)}</span>
        </header>
        <div class="knobs">
          {#each [`mic${i + 1}Dist`, `mic${i + 1}Level`] as key, j (key)}
            <FilmstripKnob
              def={PARAM[key]}
              value={getValue(key)}
              onchange={(v) => setValue(key, v)}
              size={58}
              strip={art('knob-header.webp')}
              x={110 + j * 180}
              y={52}
              labelDy={44}
              labelClass="cab-label"
            />
          {/each}
        </div>
      </section>
    {/each}

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
  .bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    user-select: none;
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
    font: 500 15px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
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
  .ir p {
    margin: 0;
    font: 14px/1.4 var(--body-font);
    color: #c8bfb3;
  }
  .field {
    display: grid;
    gap: 6px;
    font: 500 12px/1 var(--ui-font);
    letter-spacing: 0.14em;
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
    gap: 6px;
    padding: 12px 14px 4px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .micbox header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .micbox .seg {
    flex: 1;
  }
  .micbox.off .knobs :global(.knob:first-child) {
    opacity: 0.5;
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
    width: 54px;
    text-align: right;
    font: 13px/1 var(--body-font);
    color: #a39a8e;
  }
  .knobs {
    position: relative;
    height: 120px;
  }
  .cab :global(.cab-label) {
    font: 500 11px/1 var(--ui-font);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #a39a8e;
  }
  .load {
    margin-top: auto;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    height: 44px;
    border-radius: 10px;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    color: #d8d0c4;
    font: 500 14px/1 var(--ui-font);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .load:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
