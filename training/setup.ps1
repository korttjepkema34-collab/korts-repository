# One-time setup of the training environment on the GPU box (Windows, RTX 3080 Ti).
# Run from the repo root in PowerShell:  .\training\setup.ps1
# Makes training\.venv with torch (CUDA), Unsloth, TRL, kohya sd-scripts. ~10 GB of downloads.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
# CUDA 12.4 wheels; the 3080 Ti (Ampere) is fine with these. Change cu124 if your driver is older.
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
.\.venv\Scripts\pip install -r requirements.txt
# Unsloth on native Windows needs the Windows Triton build. If `import unsloth` fails, run:
#   .\.venv\Scripts\pip install triton-windows
# and if it still fails, use WSL2 instead (docs/15-training.md, "WSL2 route").
if (-not (Test-Path sd-scripts)) { git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git }
.\.venv\Scripts\pip install -r sd-scripts\requirements.txt
.\.venv\Scripts\python.exe -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
Write-Host "Training venv ready. Point worker\config.yaml tools.training_python at $PSScriptRoot\.venv\Scripts\python.exe"
