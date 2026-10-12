# browsamp

Ampli de guitare virtuel dans le navigateur. La guitare entre par l'interface audio, le signal est traité en temps réel (DSP en Rust compilé en WebAssembly, exécuté dans des AudioWorklets) puis renvoyé vers le casque.

## Lancer

Prérequis : Node ≥ 20, Rust (`rustup`) avec la cible `wasm32-unknown-unknown`.

```bash
rustup target add wasm32-unknown-unknown
npm install
npm run dev
```

Ouvrir l'URL affichée dans **Chrome** (meilleure latence et `setSinkId` pour choisir la sortie). Le bouton **Démarrer** du bandeau ouvre l'entrée audio ; la roue dentée donne accès au choix de l'interface, du canal et de la sortie. Sans guitare, **Signal de test** (en bas à gauche) joue une boucle synthétique ; **DI…** dans les réglages charge un enregistrement de guitare directe.

- `npm test` : tests du DSP (filtres, aliasing, tonestack, accordeur, stabilité, budget CPU)
- `npm run build` : build de production dans `dist/` (servir en HTTPS ou sur `localhost`, sinon le navigateur refuse l'accès à l'entrée audio)

En dev, toute modification d'un fichier `dsp/src/*.rs` recompile le WASM et recharge la page.

## En ligne

https://browsamp.kazibo.app (Chrome recommandé).

Déploiement sur Kazibo : la VM NixOS sert le build publié en asset de release GitHub, épinglé par son empreinte ([deploy/kazibo/configuration.nix](deploy/kazibo/configuration.nix)). Pour une nouvelle version : `npm run build`, `tar -C dist -czf browsamp-dist.tar.gz .`, publier une release avec l'archive, mettre à jour `version` et `hash` dans la configuration, redéployer.

## Interface

Svelte 5, une scène fixe de 1600×1000 mise à l'échelle de la fenêtre, à la manière d'un plugin : bandeau (entrée, gate, accordeur, presets, sortie), une scène par module (Pre-FX, Ampli, Baffle, Post-FX), barre de chaîne du signal en bas pour naviguer. Chaque ampli garde ses propres réglages.

| Fichier | Rôle |
| --- | --- |
| `src/lib/rig.svelte.ts` | état de l'application (runes) et actions qui pilotent le moteur audio |
| `src/lib/presets.ts` | modèle d'état v2, presets d'usine, migration des presets v1 |
| `src/scenes/*.svelte` | les scènes ; les contrôles sont posés en coordonnées de scène |
| `src/components/controls/FilmstripKnob.svelte` | potard à partir d'une planche d'images rendues |
| `art/layout.json` | géométrie partagée par l'interface et les rendus Blender |

## Images (rendus Blender)

Les visuels de `public/art/` sont rendus par des scripts, à partir de `art/layout.json` ; ils sont commités, Blender n'est donc nécessaire que pour les modifier.

```bash
npm run art                       # tout (une quinzaine de minutes sur un M4)
npm run art -- amp-brixton        # une cible : amp-<id>, knob-<style>, ou les groupes amps / knobs
npm run art -- --fast knobs       # aperçu rapide, peu d'échantillons
```

- `art/textures.py` (Pillow) imprime sérigraphies, graduations et logos avec les polices de l'interface ;
- `art/blender/` modélise et rend : `lib.py` (scène, lumières, matériaux procéduraux), `knobs.py`, `amps.py` ;
- `art/build.py` enchaîne le tout et assemble les planches de potards (grille 8×8, ombre portée incluse) en WebP.

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
