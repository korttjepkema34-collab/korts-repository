# 009 Lighting layer: clock tint, lamps, hearths, post-process
priority: 9
roles: coder, reviewer
depends_on: 005

## Goal
The 2.5D look from `mock-night.png`, built the Godot way.

## Acceptance
- `CanvasModulate` driven by `clock.gd`: day `#f0e4cd` at 22%, night `#465878` at 50%, tweened over the last minute of each phase.
- `PointLight2D` on lamp posts (warm `#ffb464`, radius ~150 px, slow flicker) and hearths (cold `#78e6dc`). Lamps light ground: light texture is a soft disc, energy tuned so the Reaper reads at 3 tiles.
- `GPUParticles2D`: chimney smoke on the guild house, dust motes by day, embers by night.
- Post-process shader on a full-screen `ColorRect`: vignette (day 20%, night 50%), soft glow on pixels above a luminance threshold, 1-2 px blur on the top 10% and bottom 5%.
- Readability rule verified with `visual_check` at night: every placeholder enemy identifiable.
