# 13 - Before you walk away (one-time setup checklist)

The studio cannot install its own tools. Do this once on each machine, run the smoke test,
then leave it. Estimated time: an afternoon.

## Server (Windows)

- [ ] Tailscale installed, hostname `server`, ACL applied (`scripts/tailscale-acl.example.json`).
- [ ] Ollama native, env vars set per `docs/06-setup-server.md`, models pulled with the
      commands in `docs/04-models.md` (about 115 GB of downloads). `ollama list` shows all of
      them. `ollama run qwen3.6:35b-a3b "say hi"` responds.
- [ ] Docker Desktop with `.wslconfig` memory cap; `docker compose up -d` in `server/` brings up
      redis and forgejo; Forgejo admin user created; this repo pushed to it.
- [ ] Godot 4 installed; path in `server/.env` as `GODOT_BIN`.
      `"%GODOT_BIN%" --headless --path game --quit` exits without errors.
- [ ] Auto-login enabled and the orchestrator task set to "run only when user is logged on", so
      windowed screenshots work. Test:
      `"%GODOT_BIN%" --path game -s res://scripts/dev/screenshot.gd -- res://scenes/main/main.tscn C:\studio\reports\test.png`
      produces a PNG.
- [ ] Optional: a Godot MCP server installed on the server and `GODOT_MCP_CMD` set (docs/11).
- [ ] `scripts\dump_godot_docs.ps1` so the coder can search the exact class reference (rerun after any Godot upgrade).
- [ ] gdUnit4: run `scripts\install_gdunit4.ps1` from the repo root. It is already enabled in
      `project.godot`; `game/tests/test_smoke.gd` should pass headless afterwards:
      `"%GODOT_BIN%" --headless --path game -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --add res://tests --ignoreHeadlessMode`
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
- [ ] Optional for now: audio. `worker/services/audio_api.py` wraps ACE-Step and Stable Audio
      Open; install both per their READMEs into the venv `run-audio-api.ps1` creates, then
      verify the two generate functions against the installed versions. Until then audio tasks
      defer cleanly.

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
