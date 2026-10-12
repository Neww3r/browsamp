import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig, type Plugin } from 'vite';

/** Rebuilds the Rust DSP when a .rs file changes and reloads the page. */
function rustDsp(): Plugin {
  const build = () => {
    try {
      execSync('npm run -s wasm', { stdio: 'inherit' });
      return true;
    } catch {
      return false;
    }
  };
  return {
    name: 'browsamp-rust-dsp',
    apply: 'serve',
    configureServer(server) {
      server.watcher.add('dsp/src');
      server.watcher.on('change', (file) => {
        if (file.endsWith('.rs') && build()) server.ws.send({ type: 'full-reload' });
      });
    },
  };
}

/** Fingerprint of the rendered art: re-rendered files keep their names, so URLs carry it to bust caches. */
function artRevision(): string {
  const hash = createHash('sha256');
  for (const f of readdirSync('public/art').sort()) hash.update(f).update(readFileSync(`public/art/${f}`));
  return hash.digest('hex').slice(0, 10);
}

export default defineConfig({
  plugins: [svelte(), rustDsp()],
  define: { __ART_REV__: JSON.stringify(artRevision()) },
  worker: { format: 'es' },
  build: { target: 'es2022' },
});
