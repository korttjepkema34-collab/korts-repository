# One-shot setup of the gaming PC's generation tools. Run from the repo root in PowerShell.
#   .\scripts\bootstrap_gpu.ps1            # ComfyUI + node packs + SDXL + pixel-art LoRA + IP-Adapter
# Re-runnable: skips anything already present. Needs git, python 3.12, and an Nvidia driver.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$tools = "C:\studio-tools"; New-Item $tools -ItemType Directory -Force | Out-Null

function Get-File($url, $dest) {
  if (Test-Path $dest) { Write-Host "have  $dest"; return }
  Write-Host "fetch $url"; New-Item (Split-Path $dest) -ItemType Directory -Force | Out-Null
  Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

# 1. ComfyUI
$comfy = Join-Path $tools "ComfyUI"
if (-not (Test-Path $comfy)) { git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $comfy }
Set-Location $comfy
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\pip install --upgrade pip
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
.\.venv\Scripts\pip install -r requirements.txt

# 2. Custom node packs (Manager for later, IP-Adapter for the character workflow)
foreach ($n in @("ltdrdata/ComfyUI-Manager", "cubiq/ComfyUI_IPAdapter_plus")) {
  $d = Join-Path $comfy ("custom_nodes\" + ($n -split "/")[1])
  if (-not (Test-Path $d)) { git clone --depth 1 "https://github.com/$n.git" $d }
  if (Test-Path (Join-Path $d "requirements.txt")) { .\.venv\Scripts\pip install -r (Join-Path $d "requirements.txt") }
}

# 3. Models. SDXL base (6.9 GB), Pixel Art XL LoRA, IP-Adapter Plus SDXL + its image encoder.
Get-File "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" "$comfy\models\checkpoints\sd_xl_base_1.0.safetensors"
Get-File "https://huggingface.co/nerijs/pixel-art-xl/resolve/main/pixel-art-xl.safetensors" "$comfy\models\loras\pixel-art-xl.safetensors"
Get-File "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors" "$comfy\models\ipadapter\ip-adapter-plus_sdxl_vit-h.safetensors"
Get-File "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" "$comfy\models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# 4. Run script for ComfyUI on localhost:8188 (the worker talks to it there)
$run = Join-Path $comfy "run-comfyui.ps1"
Set-Content $run "Set-Location `"$comfy`"`n.\.venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --preview-method none"
Write-Host ""
Write-Host "ComfyUI ready at $comfy. Start it with: powershell -File $run"
Write-Host "Optional upgrade (FLUX.2 klein 4B + pixel-art and sprite-sheet LoRAs): see worker\workflows\README.md"
Write-Host "Then: copy worker\config.example.yaml to worker\config.yaml, set the server's Tailscale IP, and run worker\run.ps1"
Write-Host ""
Write-Host "--- doctor ---"
& "$repo\worker\.venv\Scripts\python.exe" "$repo\scripts\doctor.py" --gpu 2>$null; if ($LASTEXITCODE -ne 0) { Write-Host "(run worker\run.ps1 once to create its venv, then: worker\.venv\Scripts\python.exe scripts\doctor.py --gpu)" }
