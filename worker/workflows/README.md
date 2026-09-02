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

`default.json` is included: plain SDXL text-to-image with the titles already set. Edit only
`ckpt_name` in node 1 to match the checkpoint file in your ComfyUI `models/checkpoints/` folder.
Add a pixel-art LoRA by inserting a `LoraLoader` between node 1 and nodes 2/3/5 in ComfyUI, then
re-export; keep the titles.

Planned next: `character_sheet.json` with an IP-Adapter `REFERENCE` node for consistency,
`tileset.json` at 512x512 with a tiling LoRA.
