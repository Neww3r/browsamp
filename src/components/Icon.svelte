<script lang="ts" module>
  const PATHS = {
    prev: 'M15 5 8 12l7 7',
    next: 'm9 5 7 7-7 7',
    save: 'M5 4h11l3 3v13H5zM8 4v5h7V4M8 20v-6h8v6',
    gear: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm7.4-2.1 1.6 1.3-1.6 2.8-2-.6a7.6 7.6 0 0 1-1.8 1l-.4 2.1h-3.2l-.4-2.1a7.6 7.6 0 0 1-1.8-1l-2 .6-1.6-2.8 1.6-1.3a7.8 7.8 0 0 1 0-2.8L2.2 9.3l1.6-2.8 2 .6a7.6 7.6 0 0 1 1.8-1L8 4h3.2l.4 2.1a7.6 7.6 0 0 1 1.8 1l2-.6 1.6 2.8-1.6 1.3a7.8 7.8 0 0 1 0 2.8Z',
    tuner: 'M9 3v8a3 3 0 0 0 6 0V3M12 14v7M8 21h8',
    power: 'M12 3v8M6.3 6.3a8 8 0 1 0 11.4 0',
    play: 'M8 5v14l11-7z',
    stop: 'M7 7h10v10H7z',
    chevron: 'm6 9 6 6 6-6',
    pedal: 'M7 3h10v18H7zM10 7a2 2 0 1 0 4 0 2 2 0 0 0-4 0M12 15v3',
    amp: 'M3 6h18v12H3zM3 10h18M7 14h.01M11 14h.01M15 14h.01',
    cab: 'M4 3h16v18H4zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
    post: 'M4 12h3l2-6 3 12 3-9 2 3h3',
    close: 'm6 6 12 12M18 6 6 18',
    upload: 'M12 16V4m-5 5 5-5 5 5M4 20h16',
  } as const;
  export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
  interface Props {
    name: IconName;
    size?: number;
  }
  let { name, size = 20 }: Props = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d={PATHS[name]} />
</svg>
