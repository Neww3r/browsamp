<script lang="ts">
  import { background } from '../lib/assets.svelte';
  import { LAYOUT } from '../lib/layout';

  interface Props {
    /** Scene render, without size suffix (e.g. "amp-sunset"). */
    name: string;
  }
  let { name }: Props = $props();

  const C = LAYOUT.canvas;
  let img = $derived(background(name));
  // The light 1x render shows at once; the sharp one fades in over it when it has loaded.
  let sharpLoaded = $state(false);
  $effect(() => {
    void name;
    sharpLoaded = false;
  });
</script>

<div class="backdrop" style:left="{C.x}px" style:top="{C.y}px" style:width="{C.w}px" style:height="{C.h}px">
  <img src={img.preview} alt="" draggable="false" />
  <img
    class="sharp"
    class:ready={sharpLoaded}
    src={img.src}
    srcset={img.srcset}
    sizes={img.sizes}
    alt=""
    draggable="false"
    decoding="async"
    onload={() => (sharpLoaded = true)}
  />
</div>

<style>
  .backdrop {
    position: absolute;
    user-select: none;
    pointer-events: none;
  }
  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  .sharp {
    opacity: 0;
    transition: opacity 0.35s;
  }
  .sharp.ready {
    opacity: 1;
  }
</style>
