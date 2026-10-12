<script lang="ts">
  interface Props {
    on: boolean;
    x: number;
    y: number;
    size?: number;
    color?: string;
    /** Light only: lights up a lamp that is part of the rendered background. */
    glow?: boolean;
    /** Radius of the rendered glass, in stage pixels (glow mode). */
    lens?: number;
  }
  let { on, x, y, size = 14, color = '#ff3b2f', glow = false, lens = 8 }: Props = $props();
</script>

<div class="led" class:on class:glow style:left="{x}px" style:top="{y}px" style:width="{size}px" style:height="{size}px" style:--c={color} style:--lens="{lens}px"></div>

<style>
  .led {
    position: absolute;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: radial-gradient(circle at 40% 35%, color-mix(in srgb, var(--c) 35%, #2a1d1b), #0d0b0a 70%);
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.8);
    pointer-events: none;
    transition: background 0.08s, box-shadow 0.08s;
  }
  .led.on {
    background: radial-gradient(circle at 40% 35%, #fff 0%, var(--c) 35%, color-mix(in srgb, var(--c) 60%, #000) 100%);
    box-shadow:
      0 0 6px 1px var(--c),
      0 0 22px 6px color-mix(in srgb, var(--c) 45%, transparent);
  }
  /* Off: shade the rendered glass, which otherwise reads as lit. On: light it up. */
  .led.glow {
    background: radial-gradient(circle var(--lens), rgba(8, 4, 4, 0.6) 0%, rgba(8, 4, 4, 0.5) 75%, transparent 100%);
    box-shadow: none;
  }
  .led.glow.on {
    mix-blend-mode: screen;
  }
  .led.glow.on {
    background: radial-gradient(circle, #fff 0%, var(--c) 22%, color-mix(in srgb, var(--c) 40%, transparent) 45%, transparent 70%);
    box-shadow: 0 0 40px 12px color-mix(in srgb, var(--c) 35%, transparent);
  }
</style>
