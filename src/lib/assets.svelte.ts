/**
 * Rendered art comes in several resolutions (see art/build.py). The stage is scaled to the
 * window, so the right file depends on that scale times the screen's pixel density: this
 * keeps small windows light and large Retina / 5K screens sharp.
 */
import { LAYOUT } from './layout';

const BASE = `${import.meta.env.BASE_URL}art/`;
const BG_SCALES = [1, 1.5, 2, 3];

export const view = $state({
  /** Stage pixels → CSS pixels. */
  scale: 1,
  dpr: typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1,
});

/** Device pixels per stage pixel. */
function density(): number {
  return view.scale * view.dpr;
}

/** srcset/sizes for a scene background covering the extended canvas, plus a light preview. */
export function background(name: string): { preview: string; src: string; srcset: string; sizes: string } {
  const w = LAYOUT.canvas.w;
  const files = BG_SCALES.map((k) => `${BASE}${name}-${Math.round(w * k)}.webp ${Math.round(w * k)}w`);
  return {
    preview: `${BASE}${name}-${w}.webp`,
    src: `${BASE}${name}-${w * 2}.webp`,
    srcset: files.join(', '),
    sizes: `${Math.round(w * view.scale)}px`,
  };
}

/** URL of an overlay image (knob sheet, switch, mic) at the density this screen needs. */
export function overlay(name: string): string {
  const d = density();
  const k = d <= 1.05 ? 1 : d <= 2.05 ? 2 : 3;
  return `${BASE}${name}@${k}.webp`;
}
