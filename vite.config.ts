import { execSync } from 'node:child_process';
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

export default defineConfig({
  plugins: [svelte(), rustDsp()],
  worker: { format: 'es' },
  build: { target: 'es2022' },
});
