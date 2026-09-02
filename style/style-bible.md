# Style bible

**This is a template.** The game's genre and look are not decided yet (see
`docs/open-questions.md`). Every art, 3D, and audio prompt must include the relevant section of
this file once it is filled in. The reviewer rejects anything that drifts from it.

## Game

- Working title: TBD
- Genre: TBD
- Perspective / camera: TBD (top-down, side-on, isometric, 3D third-person)
- Target resolution: TBD (e.g. 640x360 pixel art scaled 3x)

## Visual style

- Medium: TBD (pixel art / hand-painted / low-poly / cel-shaded)
- Palette: TBD. Put the swatch PNG in `style/references/palette.png` and list hex codes here.
- Line and shading: TBD (e.g. 1 px dark outline, 3-tone shading, no gradients)
- Mood keywords: TBD (e.g. "warm, worn, hopeful")
- Things to avoid: photorealism, text in images, watermarks, gradients, lens flare

## Prompt fragments (copy verbatim into every image job)

- Positive suffix: `TBD, e.g. "pixel art, 16-bit, limited palette, clean 1px outline, flat shading, transparent background"`
- Negative prompt: `photo, realistic, blurry, text, watermark, signature, gradient, 3d render, extra limbs`

## Characters

- Proportions: TBD (e.g. 3 heads tall, chibi)
- Reference sheet per character in `style/references/<name>-sheet.png` (front, side, back)

## Environments

- Tile size: TBD (e.g. 16x16)
- Lighting: TBD

## 3D (if applicable)

- Poly budget per prop / character: TBD
- Texture style: TBD (flat colour / hand-painted / PBR)
- Scale: 1 unit = 1 metre, Y-up

## Audio

- Music: instrumentation, tempo range, mood words: TBD
- SFX: dry, short, retro / realistic: TBD
- Reference tracks (describe, do not copy): TBD

## References

Drop images in `style/references/`. Name them by purpose: `palette.png`, `player-sheet.png`,
`env-forest-mood.png`. Every image job should cite at least one.
