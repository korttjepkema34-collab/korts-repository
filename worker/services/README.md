# Local tool APIs

Thin FastAPI wrapper so the worker's audio handler talks to both audio tools the same way. Runs
in its own venv on the gaming PC (and later the server).

- `audio_api.py` on :8190. `POST /music` (ACE-Step 1.5), `POST /sfx` (Stable Audio Open),
  `POST /unload`, `GET /health`. Start with `run-audio-api.ps1`. The two backend calls are
  written from the projects' documented APIs and need a check against the installed versions.

ComfyUI already has an HTTP API, so no wrapper is needed for images.
