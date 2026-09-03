# 06 - Server setup (home server, `server`, **Windows**)

The server runs Windows. Decision (see `decisions.md`): keep Windows, do **not** reinstall Linux.
Run the performance-sensitive and LAN-sensitive pieces natively, and only the stateless services
in Docker Desktop. Reasons:

- Ollama has a native Windows build. Native gets full access to the 96 GB and, later, the GPU
  driver with no WSL2 layer. Inside Docker/WSL2, memory is capped at 50% of host RAM by default
  and CPU inference is slower.
- Wake-on-LAN needs to broadcast on the physical LAN. Docker Desktop containers sit behind a
  NAT and cannot. The orchestrator therefore runs natively.
- Syncthing's Docker `network_mode: host` does not work on Docker Desktop. Native Syncthing does.
- Redis and Forgejo do not care, so they go in Docker.

## 1. Tailscale

Install Tailscale for Windows, sign in, set hostname `server`. Note the Tailscale IP
(`tailscale ip -4` in PowerShell); it is `SERVER_TS_IP` below. Apply the ACL from
`scripts/tailscale-acl.example.json`.

## 2. Ollama (native)

Install from ollama.com (Windows installer). Then in PowerShell (as your user):

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")   # listen on all, ACL restricts
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_THREADS", "16", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "30m", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "2", "User")
# restart Ollama from the tray, then:
ollama pull qwen3.6:35b-a3b      # orchestrator, verify tag (docs/04-models.md)
ollama pull qwen3-vl:8b          # reviewer
ollama pull nomic-embed-text
```

Windows Firewall: allow inbound 11434 on the Tailscale adapter only. Do the same for 6379 (Redis)
and 3000 (Forgejo): Docker Desktop's port proxy does not always honour the host IP in a
`ip:port:port` binding, so after `docker compose up -d` run `netstat -ano | findstr :6379` in
PowerShell and, if it shows `0.0.0.0:6379`, add firewall rules that allow those two ports on the
Tailscale adapter only and block them elsewhere. The compose binding is not the security boundary.

## 3. Docker Desktop (Redis + Forgejo)

Install Docker Desktop (WSL2 backend). Create `%UserProfile%\.wslconfig` so WSL2 does not hog
RAM that Ollama needs:

```ini
[wsl2]
memory=16GB
processors=4
```

Then:

```powershell
cd C:\studio\server
copy .env.example .env      # edit: SERVER_TS_IP, REDIS_PASSWORD, GPU_MAC, LAN_BROADCAST
docker compose up -d        # brings up redis and forgejo only (ollama is behind a profile)
```

If you ever want Ollama in Docker instead (e.g. on a Linux reinstall):
`docker compose --profile ollama-in-docker up -d` and set `LLM_BASE_URL` accordingly.

## 4. Repo + orchestrator (native Python)

```powershell
winget install Python.Python.3.12 Git.Git
git clone <this repo> C:\studio
cd C:\studio\server
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r orchestrator\requirements.txt
.\run-orchestrator.ps1       # loads server\.env, sets REPO_ROOT, starts the loop
```

Start on boot: Task Scheduler, "At startup", run
`powershell -File C:\studio\server\run-orchestrator.ps1`, whether user is logged on or not.

`LLM_BASE_URL` in `.env` should be `http://127.0.0.1:11434/v1` (native Ollama), and
`REDIS_HOST` should be `127.0.0.1` (Docker publishes it on the Tailscale IP and localhost).

## 5. Forgejo

Open `http://SERVER_TS_IP:3000`, create the admin user and a repo named `studio`, push this repo
to it. Add GitHub as a push mirror for an off-site copy.

## 6. Syncthing (native)

Install Syncthing for Windows (SyncTrayzor is a convenient wrapper). Add `C:\studio\assets` as a
folder, pair with the gaming PC over Tailscale. Two-way.

## 7. Wake-on-LAN

The orchestrator sends the magic packet itself (`server/orchestrator/wake.py`) when jobs are
queued and the worker heartbeat is missing. It only needs `GPU_MAC` and `LAN_BROADCAST` in
`.env`. Test manually: `python scripts\wake_gpu.py`.

## 8. Godot on the server: gate, screenshots, optional editor

Install Godot 4 (standard Windows build). Put the path in `.env` as `GODOT_BIN`. The coder
uses it three ways:

1. **Headless gate**: `--headless --import` and gdUnit4. Works with no display.
2. **Windowed screenshots** (`visual_check`): renders a scene in a real window using the i7's
   integrated Intel UHD graphics and hands the PNG to the vision model. This needs an
   **interactive desktop session**: set the server to auto-login (`netplwiz`, untick "users must
   enter a password"; or Sysinternals Autologon), and register the orchestrator's Task Scheduler
   entry as "Run only when user is logged on". The screen can be locked; rendering still works.
3. **Editor tools via MCP** (optional): install a Godot MCP server (docs/11) on the server and
   set `GODOT_MCP_CMD` in `.env`. The coder then gets `mcp_*` tools for launching the editor,
   running the project and reading runtime errors. If it is not set, nothing changes.

Any Godot process the coder starts has a hard timeout and is killed if it hangs on a dialog.

## 9. Test the queue

```powershell
cd C:\studio
.\server\.venv\Scripts\python.exe scripts\enqueue_stub.py
```

Then start the worker on the gaming PC and watch `assets\incoming\000-stub\` appear.

## 10. When the 12 GB GPU arrives

Install the Nvidia driver. Native Ollama picks it up automatically. Switch the orchestrator model
per `docs/04-models.md` and run a second copy of `worker/` on the server for `image` and `music`
kinds (it runs on Windows too).
