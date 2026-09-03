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

Three workflows ship:

| File | Use | Needs |
|---|---|---|
| `default.json` | plain SDXL text-to-image | a checkpoint |
| `tileset.json` | tiles and props, pixel-art LoRA at 0.9 | checkpoint + a pixel-art LoRA in `models/loras/` (edit `lora_name` in node 10) |
| `character_sheet.json` | characters and anything that must match a reference: LoRA + IP-Adapter on the `REFERENCE` image | checkpoint + LoRA + the **ComfyUI_IPAdapter_plus** custom nodes (node classes `IPAdapterUnifiedLoader`, `IPAdapter`) and their model files |

The handler uploads the first `spec.references` entry and sets it on the `REFERENCE` node. Jobs
pick a workflow with `spec.workflow`. If a custom node is missing, ComfyUI returns a validation
error and the job fails cleanly; install the node pack or use `tileset.json`. Node ids and titles
are the contract; re-export from ComfyUI freely as long as the titles survive.
