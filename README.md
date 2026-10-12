# browsamp

Ampli de guitare virtuel dans le navigateur. La guitare entre par l'interface audio, le signal est traité en temps réel (DSP en Rust compilé en WebAssembly, exécuté dans des AudioWorklets) puis renvoyé vers le casque.

## Lancer

Prérequis : Node ≥ 20, Rust (`rustup`) avec la cible `wasm32-unknown-unknown`.

```bash
rustup target add wasm32-unknown-unknown
npm install
npm run dev
```

Ouvrir l'URL affichée dans **Chrome**. On allume l'ampli avec son interrupteur **POWER** (ce qui ouvre l'entrée audio) ; la roue crantée en haut à droite donne accès au choix de l'interface, du canal et de la sortie, et à la mesure de latence. En développement (`npm run dev`) seulement, un panneau « dev » en bas à gauche joue un riff synthétique ou un enregistrement DI à la place de la guitare : il n'existe pas dans le build de production.

- `npm test` : tests du DSP (filtres, aliasing, tonestack, accordeur, stabilité, budget CPU)
- `npm run build` : build de production dans `dist/` (servir en HTTPS ou sur `localhost`, sinon le navigateur refuse l'accès à l'entrée audio)

En dev, toute modification d'un fichier `dsp/src/*.rs` recompile le WASM et recharge la page.

## En ligne

https://browsamp.kazibo.app (Chrome recommandé).

Déploiement sur Kazibo : la VM NixOS sert le build publié en asset de release GitHub, épinglé par son empreinte ([deploy/kazibo/configuration.nix](deploy/kazibo/configuration.nix)). Pour une nouvelle version : `npm run build`, `tar -C dist -czf browsamp-dist.tar.gz .`, publier une release avec l'archive, mettre à jour `version` et `hash` dans la configuration, redéployer.

## Interface

Svelte 5. L'application occupe toute la fenêtre : la scène utile (1600×1000) est mise à l'échelle pour tenir dans la fenêtre, et les rendus débordent largement autour (2240×1400) pour remplir n'importe quel format d'écran. Les commandes flottent sur le rendu : entrée, gate et sortie en haut (valeur sous le potard, vu-mètre à côté), presets au centre, accordeur et réglages à droite, navigation en icônes en bas (pédales, ampli, baffle, effets). Chaque ampli garde ses propres réglages ; les presets s'exportent et s'importent en `.json`.

| Fichier | Rôle |
| --- | --- |
| `src/lib/rig.svelte.ts` | état de l'application (runes) et actions qui pilotent le moteur audio |
| `src/lib/presets.ts` | modèle d'état, presets d'usine, validation des fichiers importés |
| `src/lib/assets.svelte.ts` | choix de la résolution des images selon l'échelle et la densité de l'écran |
| `src/scenes/*.svelte` | les scènes ; les contrôles sont posés en coordonnées de scène |
| `src/components/controls/FilmstripKnob.svelte` | potard à partir d'une planche d'images rendues |
| `art/layout.json` | géométrie partagée par l'interface et les rendus Blender |

## Images (rendus Blender)

Les visuels de `public/art/` sont rendus par des scripts, à partir de `art/layout.json` ; ils sont commités, Blender n'est donc nécessaire que pour les modifier.

```bash
npm run art                       # tout (environ 1 h 30 sur un M4)
npm run art -- amp-brixton        # une cible : amp-<id>, knob-<style>, board-<pre|post>, cab, footswitch, toggle, mic-<type>
npm run art -- knobs switches     # ou des groupes : knobs, switches, amps, pedals, cabinet
npm run art -- --fast knobs       # aperçu rapide, peu d'échantillons
```

- `art/textures.py` (Pillow) imprime sérigraphies, graduations et logos avec les polices de l'interface ;
- `art/blender/` modélise et rend : `lib.py` (scène, lumières de studio, matériaux procéduraux), `knobs.py` et `switches.py` (potards et interrupteurs vus légèrement de dessus), `amps.py`, `pedals.py`, `cab.py` ;
- `art/build.py` enchaîne le tout et produit plusieurs résolutions de chaque image : décors de 2240 à 6720 px de large (choisis par `srcset`), potards et interrupteurs en @1/@2/@3 (choisis selon l'échelle × la densité de l'écran).

Blender est attendu dans `/Applications/Blender.app`. Sans Blender, `python3 art/placeholders.py` complète les images manquantes de `public/art/` par des versions provisoires (même géométrie, mêmes sérigraphies) ; il ne remplace les rendus existants qu'avec `--force`.

## Chaîne de traitement

```
entrée → gain → noise gate → passe-haut / bright / mid-boost (selon le modèle)
      → [suréchantillonnage ×4 : étages triode → tonestack FMV → étage de puissance (sag, presence, resonance)]
      → baffle (ConvolverNode, IR intégrée ou perso) → delay → reverb FDN → volume → limiteur de sécurité
```

| Fichier | Rôle |
| --- | --- |
| `dsp/src/amp.rs` | assemble la chaîne de l'ampli, IDs des paramètres |
| `dsp/src/models.rs` | les voicings Clean / Crunch / High-gain |
| `dsp/src/oversample.rs` | demi-bandes IIR polyphasées (style HIIR), retard quasi nul |
| `dsp/src/tonestack.rs` | modèle analytique de Yeh, discrétisé par bilinéaire |
| `dsp/src/tuner.rs` | YIN, calcul étalé sur les échantillons (pas de pic CPU) |
| `src/audio/worklet.ts` | processeurs AudioWorklet qui pilotent le WASM (ABI `extern "C"`, sans wasm-bindgen) |
| `src/audio/engine.ts` | graphe Web Audio, périphériques, latence, test de boucle |
| `src/audio/ir.ts` | IR de baffle intégrées (synthétiques) et chargement de `.wav` |

## Latence : réglages conseillés

- Brancher le casque **sur l'interface audio**, pas sur l'ordinateur.
- Mettre l'interface à 48 kHz et réduire son buffer au minimum dans son panneau de réglages.
- La latence affichée en haut à droite est celle annoncée par le navigateur. Pour la valeur réelle, relier une sortie de l'interface à l'entrée choisie avec un câble, puis **Mesurer l'aller-retour**. Le son de l'ampli est coupé pendant la mesure.
- Le DSP n'ajoute aucun buffer : tout tient dans le bloc de 128 échantillons de Web Audio, et le traitement utilise environ 2 % du budget temps réel.

## IR de baffle

Les trois baffles intégrés sont des approximations synthétiques. Pour un son vraiment réaliste, chargez une IR au format `.wav` (de nombreux packs gratuits existent). Le début silencieux est retiré, la durée tronquée à 200 ms et le niveau normalisé. La dernière IR chargée est mémorisée dans le navigateur.
