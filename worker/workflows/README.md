# ComfyUI workflows

Export each workflow from ComfyUI with **Save (API Format)** and drop it here as `<name>.json`.
Jobs reference it by `spec.workflow`.

Before exporting, set these node titles (right-click a node > Title) so the handler can find them:

| Title | Node type | Purpose |
|---|---|---|
| `POSITIVE` | CLIPTextEncode | positive prompt |
| `NEGATIVE` | CLIPTextEncode | negative prompt |
| `LATENT` | EmptyLatentImage | width, height, batch size |
| `SEED` | KSampler | seed |
| `SAVE` | SaveImage | filename prefix |
| `REFERENCE` | LoadImage | optional, for IP-Adapter or img2img reference |

Planned workflows: `sdxl_pixelart_character`, `sdxl_pixelart_tile`, `sdxl_background`,
`flux_concept`.
