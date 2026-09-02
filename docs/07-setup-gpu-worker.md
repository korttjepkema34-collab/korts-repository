# 07 - GPU worker setup (gaming PC, `gpu`)

Assumes Windows 11 with an RTX 3080 Ti.

## 1. Tailscale

Install Tailscale for Windows, sign in to the same tailnet, hostname `gpu`.

## 2. Python + repo

```powershell
winget install Python.Python.3.12 Git.Git
git clone <this repo> C:\studio
cd C:\studio\worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.yaml config.yaml
# edit config.yaml: redis host = server's Tailscale IP, password, which kinds this worker accepts
```

## 3. Generative tools

Install each as its own app with its own venv. The worker talks to them over HTTP on localhost.

| Tool | Install | Port | Handler |
|---|---|---|---|
| ComfyUI | github.com/comfyanonymous/ComfyUI, add SDXL checkpoint + LoRAs + IP-Adapter nodes | 8188 | `handlers/comfyui.py` |
| ACE-Step 1.5 | github.com/ace-step/ACE-Step-1.5, has its own API server | 8190 | `handlers/acestep.py` |
| Godot 4 + MCP server | Godot from godotengine.org; pick a Godot MCP server (see docs/03) and note it in decisions.md | per server | coder agent uses this directly |

Put the ComfyUI workflow JSON files in `worker/workflows/` (export from ComfyUI with "Save (API
Format)"). The handler loads them by name from the job.

## 4. Syncthing

Install Syncthing, add `C:\studio\assets` as a folder, pair with the server. Two-way.

## 5. Run the worker

```powershell
cd C:\studio\worker
.\run.ps1
```

It connects to Redis over Tailscale, sends a heartbeat every 30 s, and blocks waiting for jobs of
the kinds listed in `config.yaml`.

## 6. Start on boot

Task Scheduler: trigger "At log on", action `powershell -File C:\studio\worker\run.ps1`, run
whether user is logged on or not, highest privileges.

## 7. Gaming mode

Create the file `C:\studio\worker\GAMING_MODE` to pause the worker. It finishes the current job,
unloads the generative tool's model (calls each tool's free-memory endpoint), and stops pulling.
Delete the file to resume. `toggle-gaming-mode.ps1` does this and is meant for a desktop shortcut.

## 8. Wake-on-LAN

BIOS: enable "Wake on LAN" / "Power On By PCI-E". Windows: Device Manager > network adapter >
Power Management > allow this device to wake the computer, and disable Fast Startup. Note the
adapter MAC in the server's `.env`.
