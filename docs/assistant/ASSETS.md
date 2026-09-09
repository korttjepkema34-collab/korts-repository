# Art, sprites and audio setup

The repository already has ComfyUI workflow JSON, image postprocessing, a GPU worker, and audio
service code. Those belong to the older Redis-based studio. The new assistant does not yet dispatch
these binary jobs; their profiles are explicitly unconfigured. Do not enable the old autonomous
reviewer to bridge this gap: it automatically approves some non-image outputs and conflicts with
cloud-only approval. This is an integration requirement, not a completed feature.

## Environment art and sprites on the 3080 Ti

1. Install ComfyUI locally using the [official Windows/local instructions](https://docs.comfy.org/installation/manual_install).
   Keep its Python/PyTorch dependencies separate from the assistant. Prefer a stable supported
   installer/runtime; verify the installed NVIDIA driver against the selected release.
2. Start on localhost. Confirm the UI loads and a small workflow generates an actual image.
3. Begin with one checkpoint and one workflow. The existing `worker/workflows/default.json` is an
   SDXL workflow; inspect its checkpoint name and install exactly the corresponding checkpoint.
4. Existing `tileset.json` additionally needs its named LoRA. `character_sheet.json` additionally
   needs IP-Adapter custom nodes/models and a real reference image. Missing prerequisites must fail
   clearly. Do not assume the old bootstrap's unpinned downloads are still correct.
5. Record source/model version, file checksum, required node versions and license for each download.
6. Export **API-format** workflows, retaining POSITIVE, NEGATIVE, LATENT, SEED, SAVE and REFERENCE
   titles expected by `worker/handlers/comfyui.py`. Read `worker/workflows/README.md` for this contract.
7. Generate one building and one character example matching `style/style-bible.md` and the existing
   day/night references. Save seeds and the workflow next to the output.
8. Validate dimensions, transparency, palette, edges and seams. For sprites verify frame grid,
   baseline alignment, direction consistency and actual animation playback in Godot.
9. A cloud vision-capable reviewer must receive actual image data and compare to references before
   promotion. A text-only model cannot certify an image. Add transport and review to the new
   controller before enabling its media adapters.

Stop/unload local LLM inference before large generation jobs until a shared GPU scheduler is proven.
Start with single images and modest resolution/batch size. Do not buy capacity or assume every
recent image model fits 12 GB. Keep binaries outside Git; use a private asset folder and existing
local transfer/backup tools.

## Sound effects and music

Sword swings, doors and enemy sounds are SFX, not spoken voice or music. The older code references
Stable Audio Open for effects and ACE-Step for music. Inspect `worker/services/audio_api.py`, its
requirements and model-loading behavior before installing. Qualify these tools separately; do not
reuse the assistant's Python environment for heavy audio dependencies.

1. Select an actual locally runnable model and inspect its model card/license and supported output.
   [Stable Audio Open model card](https://huggingface.co/stabilityai/stable-audio-open-1.0) is one starting point,
   not a promise of unrestricted use or the best result.
2. Install the model's documented dependencies in its own environment and run its sample generation.
3. Generate a short sword swing, a door sound and an enemy variation. Listen to actual files.
4. Check sample rate, channel count, clipping, initial/trailing silence, file duration and loop seams.
5. Import into Godot; check timing, volume and repeated variations in context.
6. Save source/license, prompt, seed, generator version and processing steps in sidecars.
7. Integrate the binary transport, deterministic audio checks and a suitable review path. Cloud
   text review may inspect metrics and logs but cannot pretend it listened to audio.

Human taste review remains valuable for both visuals and sound. Missing qualified review should
produce awaiting_review/blocked, never automatic approval based on file existence.

## Concrete remaining adapter contract

Input: job ID, project, kind, style/reference paths, workflow/model version, seed, output constraints.
Output: actual private artifact paths, hashes, metadata, deterministic checks, errors and logs.
Resource: acquire one shared GPU lease before loading a heavy model; renew and release it safely.
Review: route to cloud with the required modality, preserve evidence, reject missing evidence.
Retry: distinguish generation failure, transport delay, review rejection and provider outage.
Integration: accepted candidate assets still need tested Godot import before they count as complete.
