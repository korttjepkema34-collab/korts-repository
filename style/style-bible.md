# Style bible: Reaper's Relics

Every art and audio prompt includes the relevant section verbatim. The reviewer rejects anything
that drifts from it. World, characters and places: `docs/14-world-bible.md`. Approved look:
`style/references/mock-day.png` and `style/references/mock-night.png` (hand-built mock frames;
match their tone, scale and lighting, not their exact pixels).

## Game

- Title: **Reaper's Relics**
- Genre: 2.5D pixel-art online RPG. Day: scavenge and build. Night: hordes. Bosses in dungeons.
- Perspective: three-quarter top-down (building fronts visible, roofs above them), eight-direction
  movement, four-direction sprites. Everything sorts by its feet.
- Base resolution: **960x540**, integer-scaled 2x to 1920x1080. **30x17 tiles on screen.** The
  camera zooms to 1.5x for interiors and 3x for dialogue close-ups.

## Two layers, two rules

1. **Pixel layer**: tiles, sprites, props, UI. Uses **only the 16 palette colours below.** 1 px
   outline in colour 1 on characters and props; no outlines on ground tiles. Flat three-tone
   shading (shadow, base, highlight) per material. No gradients, no anti-aliasing. Dithering only
   on water and lamp halos.
2. **Lighting layer** (Godot 2D lights, `CanvasModulate`, particles, post-process shader): may use
   any colour. Warm lamplight, cold hearth and tech glow, moonlight, fog, smoke, dust, glow,
   vignette, a soft blur on the top and bottom edge. **Readability rule: at night every enemy must
   be identifiable at any distance, and every lamp lights ground, not air.** Mood comes from colour
   and contrast, never from hiding things.

## Palette (pixel layer, fixed)

Swatch: `style/references/palette.png`.

| # | Hex | Use |
|---|---|---|
| 1 | `#0d0c10` | outlines, deepest shadow |
| 2 | `#1c1a22` | night ground, charcoal |
| 3 | `#2e2b33` | ash, shadowed stone, roof shingles |
| 4 | `#4a4650` | stone, plate armour |
| 5 | `#706a72` | light stone, fog |
| 6 | `#a39b93` | bone, skin, blade |
| 7 | `#d9cfbf` | parchment, bleached wood, highlights |
| 8 | `#3a2a22` | dark leather, cloaks, soil |
| 9 | `#6b4a34` | leather, timber, rust shadow |
| 10 | `#9c6a3c` | rust, tarnished bronze, plank highlight |
| 11 | `#c9a24a` | gold: relic trim, pauldrons, stamina bar. Rare. |
| 12 | `#5a1f22` | dried blood, banners |
| 13 | `#8c2f2a` | blood, a Thrall's eyes up close, vigour bar |
| 14 | `#1f3a3a` | deep teal: water, moss shadow, night foliage |
| 15 | `#3e7f76` | corroded copper, moss, kelp, foliage highlight |
| 16 | `#7fd6d1` | cold glow: working tech only, hearths, Herald eyes. Never on the environment. |

## Prompt fragments (copy verbatim into every image job)

- Positive suffix: `pixel art, 32px tiles, three-quarter top-down RPG, 16 colour limited palette, 1px dark outline, flat 3-tone shading, no anti-aliasing, weathered post-collapse medieval, scavenged technology, ash and rust and tarnished gold, transparent background`
- Negative prompt: `photo, realistic, blurry, text, watermark, signature, gradient, 3d render, extra limbs, anime, chibi, purple glow, neon, skeleton, smooth shading, jpeg artifacts, bright saturated colours`
- Generate at 1024x1024 and downscale with nearest-neighbour to target. Never upscale.

## Scale

- Tiles: **32x32**. Characters: **32x48** footprint (one tile wide, one and a half tall).
- Props: barrels 10x10, crates 12x12, lamp posts 12x38, doors 12x19, windows 10x12.
- Buildings: front wall 48 px tall (single storey) or 92 px (two storeys), roof 72-96 px tall,
  4 px roof overhang each side. Chimneys 12x22.

## Characters

- Proportions: roughly 2.5 heads tall at 32x48. Large hands and feet readable at 1x.
- Faces: two-pixel eyes, no mouth unless talking. Expression through posture.
- Reference sheet per character in `style/references/<name>-sheet.png`: front, side, back on one
  row, transparent, same scale.
- Sprite standard: 4 directions (right is a flip of left), walk 6 frames, attack 4, dodge 3,
  idle 2. Modular layers: body, hair, outfit, held item.
- **The Reaper**: hooded leather cloak (8/9), gold relic trim pixel (11), scythe over the shoulder
  (handle 9, blade 6/7), boots 4. Co-op players palette-swap the cloak to 4/5.
- **Thrall**: slack posture, ash body (3), 1 px outline, a hanging wire (15) from the head, eyes
  16 at range and 13 up close.
- **Courser**: a Thrall stretched: narrower, forward lean, longer legs.
- **Herald**: 14x10 drone, stone grey (4/5), two 16 eyes, a searchlight (lighting layer).
- **The Castellan**: 36x60, plate 4/5, gold pauldrons 11, red visor slit 13, siren shield 9/10
  with a 16 lens.
- **Hesper**: grey robe (4/5), ledger (7). **Old Cutter**: brown coat (9/10), hook always in hand.

## Environments

- Ground: ash (3 base) with scattered stones, grass tufts (14/15), rare bone-white flowers (6/7).
- Cobbles: individually shaded stones (4 base, 5 highlight, 3 shadow), moss in the joints.
- Walls: bricks with per-brick tone variation (3/4/5), mortar 2, moss at the base, timber beams 8/9.
- Roofs: shingles (3 base, 2 shadow, 4 highlight), lit ridge (5/6), chimney stone 4/5.
- Floors: planks 9/10 with 8 seams and grain.
- Water: 14 base with random 15 ripple dashes and sparse 16 sparkles (night) or 6 (day).
- The Keep: brick gatehouse, car-door barrier walls with rust (9/10), banners 12/13 with gold 11,
  transformer tower lattice (2/3), cooling pond, strung cables (1).
- The Fallows: overgrown cobble, ivy on roofs, rusted overpass, tall grass.
- The Undercroft: marble (5/6/7), gold-leafed cables (11), reactor glow (16), knee-deep water.
- Props: barrels, crates, scrap piles of car doors, market stalls with a red-and-bone awning,
  wells, signposts, lamp posts, fences, garden plots (8 soil, 15 seedlings).

## Lighting (lighting layer)

- Day: warm sun from the upper-left (`#ffe4af` at ~40%), soft elliptical shadows under every
  object, light ambient tint, no fog in the Keep, chimney smoke, dust motes, crows.
- Night: ambient `#465878` at ~50% multiply, moonlight from the right (`#8cafd7` at ~30%),
  lamps warm `#ffb464` radius ~150 px with a slow flicker, hearths cold `#78e6dc`, Thrall eye
  glows, Herald searchlight cone, drifting fog at low alpha, embers, lamp reflections on water.
- Both: vignette (day ~20%, night ~50%), 1-2 px blur on the top ~10% and bottom ~5% of the frame.

## UI

- Pixel font, 8 px cap height, colour 7 on colour 2 panels, 1 px border in 5.
- Three bars in the prototype: vigour (13), stamina (11), relic (16). Lowercase labels.
- Night counter top-right in colour 16: `night 3 · wave 2 / 5 · wired 120`.

## Audio

- Music: slow, sparse, 70-90 bpm. Nylon guitar, harmonium, low strings, a single bell, distant
  hum of a transformer. Warm 16-bit soundtrack recorded in a wooden room. The Keep's day theme is
  major-key and tired; the night theme is a minor drone with a siren-like swell every 8 bars; the
  Undercroft is reactor hum plus organ.
- SFX: dry, short, retro-sampled. Footsteps change on cobble, planks, water. The Castellan's
  siren is the single most important sound in the game: a cracked mid-pitch klaxon, 0.8 s.
- No vocals anywhere.

## References

`style/references/`: `palette.png`, `mock-day.png`, `mock-night.png`, then approved outputs of
task 002: `keep-mood.png`, `reaper-sheet.png`, `thrall-sheet.png`. Every image job cites at least
one.
