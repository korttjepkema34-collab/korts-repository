# Style bible

Every art and audio prompt includes the relevant section verbatim. The reviewer rejects
anything that drifts from it. World, characters and places: `docs/14-world-bible.md`.

## Game

- Working title: **Hollowmere**
- Genre: online RPG, story campaign playable solo or co-op, persistent hub (`docs/10-game-design.md`)
- Perspective / camera: top-down, slight front-facing tilt (classic 16-bit RPG), 4-direction characters
- Target resolution: 640x360 base, integer-scaled 3x to 1920x1080

## Visual style

- Medium: pixel art, 16-bit feel
- Tile size: 16x16. Characters occupy roughly 16x24 (one tile wide, one and a half tall).
- Palette: **16 colours, fixed.** Every asset uses only these. Swatch: `style/references/palette.png`.

| # | Hex | Use |
|---|---|---|
| 1 | `#1b1f2a` | deepest shadow, outlines |
| 2 | `#2e3a4f` | deep water, night sky |
| 3 | `#3f6b7a` | mid water, cold stone shadow |
| 4 | `#5fa8a0` | shallow water, kelp highlight |
| 5 | `#a8d8c8` | foam, wet highlights |
| 6 | `#4a3b2f` | dark wood, mud |
| 7 | `#7a5c3e` | wood, rope, leather |
| 8 | `#b08a5a` | sand, dry wood highlight |
| 9 | `#e0c48c` | pale sand, skin highlight |
| 10 | `#6b6b66` | stone |
| 11 | `#9c9a8f` | light stone, weathered paint |
| 12 | `#c8c2b0` | bone, bleached wood, paper |
| 13 | `#c9772e` | lantern light, rust, warmth |
| 14 | `#f2b64d` | lantern core, brass, gold hour |
| 15 | `#8a3a3a` | blood-rust, guild red |
| 16 | `#4f6b3a` | moss, kelp shadow |

- Line and shading: 1 px outline in colour 1 on characters and props; tiles have no outline.
  Flat shading, three tones per material (shadow, base, highlight) from the palette. No
  gradients, no anti-aliasing, no dithering except on water.
- Light: warm from the upper-left (lantern/gold hour), cool shadows toward palette colours 2-3.
- Mood keywords: weathered, damp, warm-lit, patient, salt-stained, quiet.
- Things to avoid: photorealism, text in images, watermarks, gradients, lens flare, purple
  magic glow, skeletons, anime faces, chibi eyes, high-saturation primaries.

## Prompt fragments (copy verbatim into every image job)

- Positive suffix: `pixel art, 16-bit, top-down RPG, 16 colour limited palette, 1px dark outline, flat 3-tone shading, no anti-aliasing, weathered coastal fantasy, warm lantern light, transparent background`
- Negative prompt: `photo, realistic, blurry, text, watermark, signature, gradient, 3d render, extra limbs, anime, chibi, purple glow, neon, skeleton, smooth shading, jpeg artifacts`
- Generate at 512x512 or 1024x1024 and downscale with nearest-neighbour to target. Never upscale.

## Characters

- Proportions: 2.5 heads tall, 16x24 px footprint. Large hands and feet readable at 1x.
- Faces: two-pixel eyes, no mouth unless talking. Expression through posture.
- Reference sheet per character in `style/references/<name>-sheet.png`: front, side, back, on one
  row, transparent background, same scale.
- Sprite standard: 4 directions (down, up, left, right; right is a flip of left), walk 6 frames,
  attack 4 frames, idle 2 frames. Modular layers: body, hair, outfit, held item.
- Player Salvager: oilskin coat (colour 7), hood down, salvage hook on a chain, lantern on the belt.
- The Drowned: same proportions as people, slack posture, palette shifted to 3-5, weed on shoulders.

## Environments

- Tilesets: 16x16, autotile-friendly (47-tile blob or 16-tile bitmask), no outlines.
- Saltreach: wood (6-8), sand (8-9), stone (10-12), lantern posts (13-14). Water animates 4 frames.
- The Shallows: cobble (10-11) under kelp (16, 4), tide pools (3-5), mud (6).
- The Sunken Chapel: stone (10-12), water tiles at knee depth (3-4), stained-glass light patches
  using 13-15 on the floor.
- Props: barrels, nets, crates, bells, carts, lantern posts, kelp clumps, drowned furniture.

## UI

- Font: pixel font, 8 px cap height, colour 12 on colour 1 panels with 1 px border in 11.
- Three bars only in the prototype: health (15), stamina (14), oil (13). Lowercase labels.

## Audio

- Music: slow, sparse, 70-90 bpm. Instruments: nylon guitar, harmonium, low strings, a single
  bell, distant surf. Chiptune-adjacent but warm; think 16-bit era soundtrack recorded in a
  wooden room. Saltreach theme is major-key and tired; Chapel theme is a minor drone with a bell
  every 8 bars.
- SFX: dry, short, retro-sampled feel. Water splashes on every step in water tiles. The Warden's
  hand-bell is the single most important sound in the game: cracked, mid-pitch, 0.6 s.
- No vocals anywhere.

## References

`style/references/`: `palette.png` (generated from the table above), then approved outputs of
task 002: `saltreach-mood.png`, `player-sheet.png`, `drowned-sheet.png`. Every image job cites
at least one.
