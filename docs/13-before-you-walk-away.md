# 13 - Before you walk away (one-time setup checklist)

The studio cannot install its own tools. Do this once on each machine, run the smoke test,
then leave it. Estimated time: an afternoon.

## Server (Windows)

- [ ] Tailscale installed, hostname `server`, ACL applied (`scripts/tailscale-acl.example.json`).
- [ ] Ollama native, env vars set per `docs/06-setup-server.md`, models pulled:
      orchestrator, coder, reviewer (vision), escalation, embeddings. Verify tags first.
      `ollama list` shows all of them. `ollama run <orchestrator> "say hi"` responds.
- [ ] Docker Desktop with `.wslconfig` memory cap; `docker compose up -d` in `server/` brings up
      redis and forgejo; Forgejo admin user created; this repo pushed to it.
- [ ] Godot 4 installed; path in `server/.env` as `GODOT_BIN`.
      `"%GODOT_BIN%" --headless --path game --quit` exits without errors.
- [ ] gdUnit4 unzipped into `game/addons/gdUnit4` (from the Godot Asset Library or GitHub
      releases). Optional but strongly recommended; without it the coder gate is only a load check.
- [ ] Syncthing native, `assets/` folder shared with the gaming PC.
- [ ] `server/.env` filled in: Tailscale IP, Redis password, model names, GPU MAC, broadcast.
- [ ] `server/run-orchestrator.ps1` runs in a window and prints "orchestrator up".
- [ ] Task Scheduler entry so it starts on boot.
- [ ] Windows Update set to not auto-restart during active hours, or paused for the week.
- [ ] Power plan: never sleep.

## Gaming PC (Windows)

- [ ] Tailscale installed, hostname `gpu`.
- [ ] ComfyUI installed with an SDXL checkpoint, at least one pixel-art LoRA, and the IP-Adapter
      nodes. At least one workflow exported in API format into `worker/workflows/` with the node
      titles from `worker/workflows/README.md`. Name the first one `default.json`.
- [ ] `worker/config.yaml` filled in; `worker/run.ps1` runs and prints "worker gpu up".
- [ ] Task Scheduler entry so the worker starts at logon.
- [ ] Wake-on-LAN enabled in BIOS and the adapter; Fast Startup off.
- [ ] Syncthing paired with the server.
- [ ] Optional for now: TRELLIS and ACE-Step. Their handlers fail cleanly until the API
      wrappers in `worker/services/` exist, and the studio defers those tasks.

## Smoke test (10 minutes)

1. On the server: `python scripts\enqueue_stub.py`. Queue depth shows 1.
2. On the gaming PC the worker logs `running 000-stub-... (stub)` then `done`.
3. `assets\incoming\000-stub\stub.txt` appears on the server within a minute (Syncthing).
4. Put the gaming PC to sleep. `python scripts\wake_gpu.py` wakes it.
5. Start the orchestrator. Within a minute it plans task 001, and the task file in
   `tasks/in-progress/` gains a "planned stub job" line. Within a few minutes it moves to
   `tasks/done/`.
6. Check `PROGRESS.md` exists.

If all six pass, walk away. Everything after this is the studio's job.

## What to expect when you return

Read `PROGRESS.md` first, then `tasks/deferred/`. Deferred tasks are the ones that need a
human; everything else either got done or is still cycling.
