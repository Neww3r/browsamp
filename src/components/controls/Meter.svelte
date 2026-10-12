<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    /** Returns the analyser to read, or null when audio is stopped. */
    source: () => AnalyserNode | null;
    height?: number;
    width?: number;
  }
  let { source, height = 52, width = 7 }: Props = $props();

  let level = $state(-90);
  let hold = $state(-90);
  let clip = $state(false);

  onMount(() => {
    let buf = new Float32Array(2048);
    let holdUntil = 0;
    let clipUntil = 0;
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
      level = db > level ? db : Math.max(db, level - 1.2);
      if (db >= hold) {
        hold = db;
        holdUntil = now + 1200;
      } else if (now > holdUntil) hold = Math.max(db, hold - 0.6);
      if (peak >= 0.99) clipUntil = now + 1500;
      clip = now < clipUntil;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  });

  const pos = (d: number) => Math.max(0, Math.min(1, (d + 60) / 60));
</script>

<div class="meter" class:clip style:--h="{height}px" style:height="{height}px" style:width="{width}px" title="{hold <= -89 ? '-∞' : hold.toFixed(1)} dBFS">
  <div class="bar" style:height="{pos(level) * 100}%"></div>
  <div class="hold" style:bottom="{pos(hold) * 100}%"></div>
</div>

<style>
  .meter {
    position: relative;
    border-radius: 3px;
    background: #0b0a09;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.9), 0 0 0 1px rgba(255, 255, 255, 0.06);
    overflow: hidden;
  }
  .bar {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(0deg, #3fbf5f 0%, #3fbf5f 70%, #e8b13c 85%, #e5483c 100%);
    background-size: 100% var(--h);
    background-position: bottom;
  }
  .hold {
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: #f3ede4;
  }
  .clip {
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.9), 0 0 0 1px #e5483c, 0 0 8px #e5483c;
  }
</style>
