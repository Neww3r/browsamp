<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    /** Returns the analyser to read, or null when audio is stopped. */
    source: () => AnalyserNode | null;
    height?: number;
    width?: number;
    label?: string;
  }
  let { source, height = 58, width = 8, label = 'Niveau' }: Props = $props();

  // LED segments from -48 dBFS (bottom) to 0 dBFS (top), like a hardware meter.
  const SEGMENTS = 16;
  const FLOOR = -48;
  const segDb = Array.from({ length: SEGMENTS }, (_, i) => FLOOR + ((i + 1) * -FLOOR) / SEGMENTS);
  const color = (db: number) => (db > -3 ? 'red' : db > -12 ? 'amber' : 'green');

  let level = $state(-90);
  let hold = $state(-90);
  /** Latched until clicked: a single over is easy to miss on a moving meter. */
  let clipped = $state(false);

  onMount(() => {
    let buf = new Float32Array(2048);
    let holdUntil = 0;
    let raf = 0;
    const tick = (now: number) => {
      const an = source();
      let peak = 0;
      if (an) {
        if (buf.length !== an.fftSize) buf = new Float32Array(an.fftSize);
        an.getFloatTimeDomainData(buf);
        for (let i = 0; i < buf.length; i++) peak = Math.max(peak, Math.abs(buf[i]));
      }
      const db = peak > 0 ? 20 * Math.log10(peak) : -90;
      level = db > level ? db : Math.max(db, level - 1.0); // ~60 dB/s fall
      if (db >= hold) {
        hold = db;
        holdUntil = now + 1500;
      } else if (now > holdUntil) hold = Math.max(db, hold - 0.5);
      if (peak >= 0.995) clipped = true;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  });

  const HALF = -FLOOR / SEGMENTS / 2;
  /** Index of the highest segment the peak-hold reaches. */
  let holdSeg = $derived.by(() => {
    let i = -1;
    while (i + 1 < SEGMENTS && hold >= segDb[i + 1] - HALF) i++;
    return i;
  });
</script>

<div class="meter" style:height="{height}px" style:width="{width}px">
  <button
    class="clip"
    class:on={clipped}
    onclick={() => (clipped = false)}
    title={clipped ? 'Écrêtage détecté : cliquez pour réinitialiser' : 'Témoin d’écrêtage'}
    aria-label="{label} : témoin d’écrêtage{clipped ? ' (allumé)' : ''}"
  ></button>
  <div class="segs" role="meter" aria-label={label} aria-valuemin={FLOOR} aria-valuemax={0} aria-valuenow={Math.max(FLOOR, Math.round(level))}>
    {#each segDb as d, i (i)}
      <span class="seg {color(d)}" class:lit={level >= d - HALF} class:hold={i === holdSeg && hold > FLOOR}></span>
    {/each}
  </div>
</div>

<style>
  .meter {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .clip {
    flex: 0 0 5px;
    padding: 0;
    border: 0;
    border-radius: 1.5px;
    background: #3a1714;
    cursor: pointer;
  }
  .clip.on {
    background: #ff3b2f;
    box-shadow: 0 0 6px #ff3b2f;
  }
  .segs {
    flex: 1;
    display: flex;
    flex-direction: column-reverse;
    gap: 1px;
    padding: 1px;
    border-radius: 2px;
    background: rgba(6, 6, 6, 0.75);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  }
  .seg {
    flex: 1;
    border-radius: 1px;
    opacity: 0.16;
  }
  .seg.green {
    background: #4fd16b;
  }
  .seg.amber {
    background: #f0b43c;
  }
  .seg.red {
    background: #ff4a3a;
  }
  .seg.lit,
  .seg.hold {
    opacity: 1;
  }
</style>
