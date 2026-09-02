# Local tool APIs (to be written)

Thin FastAPI wrappers so the worker handlers talk to each tool the same way. Each runs in its own
venv on the gaming PC (and later the server).

- `trellis_api.py` on :8189. `POST /generate`, `POST /unload`. Wraps TRELLIS 2, falls back to
  Hunyuan3D for texturing when `texture: true` and VRAM allows.
- `audio_api.py` on :8190. `POST /music` (ACE-Step 1.5), `POST /sfx` (Stable Audio Open),
  `POST /unload`.

ComfyUI already has an HTTP API, so no wrapper is needed for images.
