<script lang="ts" module>
  const PATHS = {
    prev: 'M15 5 8 12l7 7',
    next: 'm9 5 7 7-7 7',
    save: 'M5 4h11l3 3v13H5zM8 4v5h7V4M8 20v-6h8v6',
    // Classic cog (after Lucide's "settings", ISC licence).
    gear: 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    tuner: 'M9 3v8a3 3 0 0 0 6 0V3M12 14v7M8 21h8',
    play: 'M8 5v14l11-7z',
    stop: 'M7 7h10v10H7z',
    chevron: 'm6 9 6 6 6-6',
    close: 'm6 6 12 12M18 6 6 18',
    upload: 'M12 16V4m-5 5 5-5 5 5M4 20h16',
    download: 'M12 4v12m-5-5 5 5 5-5M4 20h16',
    // Signal chain.
    pedal: 'M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM9 5.4a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM15 5.4a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM12 14.8a2.2 2.2 0 1 0 0 4.4 2.2 2.2 0 0 0 0-4.4z',
    amp: 'M4 7h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM9 7V5h6v2M6 11h.01M9.5 11h.01M13 11h.01M16.5 11h.01M2 14.5h20',
    cab: 'M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12zM12 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z',
    echo: 'M4.5 12h.01M8.5 8.5a5 5 0 0 1 0 7M12.5 6a8.5 8.5 0 0 1 0 12M16.5 3.5a12 12 0 0 1 0 17',
  } as const;
  export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
  interface Props {
    name: IconName;
    size?: number;
    stroke?: number;
  }
  let { name, size = 20, stroke = 1.8 }: Props = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width={stroke} stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d={PATHS[name]} />
</svg>
