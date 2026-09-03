---
name: asset-review
description: Review a generated image against the style bible the way the reviewer agent does: deterministic palette/size/transparency checks, then a judgement. Use when asked to review, approve or reject an asset, or to check assets/incoming.
---
1. Run the deterministic check: `python -c "import sys; sys.path[:0]=['.','server']; from pathlib import Path; from orchestrator import checks; print(checks.check_image(Path('.'), Path('<file>'), {'transparent_bg': True}))"`.
2. Open the image and `style/references/mock-day.png` / `mock-night.png`. Apply `agents/reviewer.md`: spec, style bible (three-quarter view, 1 px outlines, flat 3-tone shading, 32 px scale, no baked lighting), consistency with `assets/approved/`, artefacts, licence in the sidecar.
3. Write the verdict JSON into the sidecar's `review` field and move the file and sidecar to `assets/approved/` or `assets/rejected/`. Be strict on consistency, lenient on minor quality.
