# START HERE

Everything the studio needs is in this repo. What it cannot do is click installers, sign into
Tailscale, or set a BIOS option. This page is the whole of your part, in order. Budget an
afternoon. **After each block, run the doctor and fix what it names until it says READY.**

## A. Server (Windows, the always-on box)

1. Install: [Tailscale](https://tailscale.com/download) (hostname `server`), [Ollama](https://ollama.com/download),
   [Docker Desktop](https://www.docker.com/products/docker-desktop/), [Godot 4](https://godotengine.org/download/windows/) (standard build),
   [Python 3.12](https://www.python.org/downloads/) (tick "Add to PATH"), [Git](https://git-scm.com/download/win).
2. Ollama: in PowerShell run the four `SetEnvironmentVariable` lines from `docs/06-setup-server.md` §2, then restart Ollama from the tray.
3. `git clone <this repo> C:\studio`, then `cd C:\studio` and `copy server\.env.example server\.env`.
4. Edit `server\.env`: `SERVER_TS_IP` (from `tailscale ip -4`), `REDIS_PASSWORD` (anything long), `GODOT_BIN` (path to the Godot exe), `GPU_MAC` and `LAN_BROADCAST` (from `ipconfig /all` on the gaming PC).
5. `.\scripts\bootstrap_server.ps1` (pulls models, makes the venv, starts Redis and Forgejo, installs gdUnit4, dumps and indexes the docs). About 60 GB of downloads.
6. `.\studio.ps1 scripts\doctor.py` and fix anything marked FAIL.
7. Windows: enable auto-login (`netplwiz`, untick "users must enter a password"), set the power plan to never sleep, pause Windows Update for the week.
8. In the Godot editor once: Editor > Manage Export Templates > Download, so the nightly Windows build works.
9. Task Scheduler: new task, trigger "At log on", action `powershell -File C:\studio\server\supervise.ps1`, "Run only when user is logged on". The supervisor keeps the loop alive and rolls back bad self-fixes (docs/23). Do not start it yet.
10. Optional, recommended: free cloud escalation for the hard problems. On the server run `ollama signin`; make an OpenRouter key and put it in `OPENROUTER_API_KEY`; leave `ESCALATION_LADDER` as shipped. Details and the privacy caveat: `docs/24-cloud-escalation.md`.
11. Optional: install the free ntfy app on your phone, make a topic, and set `NOTIFY_URL` in `server\.env` for a daily one-liner and incident pushes.

## B. Gaming PC (Windows, the GPU box)

1. Install: Tailscale (hostname `gpu`), Python 3.12, Git, the current Nvidia driver.
2. `git clone <this repo> C:\studio`, then `copy worker\config.example.yaml worker\config.yaml` and set `redis.host` to the server's Tailscale IP and `redis.password`.
3. `.\scripts\bootstrap_gpu.ps1` (installs ComfyUI, node packs, SDXL, the pixel-art LoRA, IP-Adapter). About 10 GB.
4. Start ComfyUI: `powershell -File C:\studio-tools\ComfyUI\run-comfyui.ps1`. Leave it running.
5. `cd C:\studio\worker`, `.\run.ps1` once to create its venv; then `..\worker\.venv\Scripts\python.exe ..\scripts\doctor.py --gpu` and fix FAILs.
6. Task Scheduler: "At log on", `powershell -File C:\studio\worker\run.ps1`. Wake-on-LAN: enable in BIOS and in the network adapter's Power Management; turn off Fast Startup.
7. Optional, strongly recommended: `ollama pull qwen3.6:27b`, set `OLLAMA_HOST=0.0.0.0:11434`, and put `http://<this PC's Tailscale IP>:11434/v1` in the server's `CODER_BASE_URL_GPU`. Code jobs then use this GPU whenever the PC is on.
8. Syncthing on both machines sharing `C:\studio\assets` (two-way). Five minutes; `docs/07-setup-gpu-worker.md` §4.

## C. Prove it, then walk away (15 minutes)

1. Server: `.\studio.ps1 scripts\enqueue_stub.py`. Gaming PC's worker logs `running 000-stub-...` then `done`; `C:\studio\assets\incoming\000-stub\stub.txt` appears on the server within a minute.
2. Server: start `server\supervise.ps1`. Within a minute task 001 moves to `tasks\in-progress\` and then `tasks\done\`; `PROGRESS.md` appears.
3. Watch task 003 (verify the skeleton) get planned and merged. If it defers, read the task file's last lines; that is the first real bug for you or a Claude Code session with the `godot-check` skill.
4. Leave. Come back in a few days. Read `PROGRESS.md`, then `tasks\deferred\`.

## D. When you come back

`PROGRESS.md` (open incidents are at the bottom), `incidents\` for anything the studio could not fix itself, then `reports/playtest-<date>.md` (what the bot saw last night), then `builds\reapers-relics-<date>\ReapersRelics.exe` to play it yourself, then `tasks\deferred\`.

## E. Later, when you feel like it

`docs/16-when-you-get-home.md`: the learning loop (grade the reviewer ten minutes a week, train a style LoRA from approved art).
`worker/workflows/README.md`: the FLUX.2 klein upgrade for better sprites and walk cycles.

## If something is wrong

Run the doctor on the machine that misbehaves. Every FAIL line names the fix. The full reference is
`docs/13-before-you-walk-away.md`; the two bootstrap scripts are re-runnable and skip what exists.
