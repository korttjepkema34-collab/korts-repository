# One-shot setup of the server's studio pieces after Ollama, Docker Desktop and Godot are installed.
# Run from the repo root in PowerShell. Re-runnable.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
if (-not (Test-Path "server\.env")) { Copy-Item server\.env.example server\.env; Write-Host "created server\.env: EDIT IT (Tailscale IP, Redis password, GODOT_BIN, GPU MAC) then rerun" ; exit 1 }
# models
foreach ($m in @("qwen3.6:35b-a3b", "qwen3.6:35b-a3b-coding", "qwen3-vl:8b", "nomic-embed-text")) { ollama pull $m }
Write-Host "Skipping gpt-oss:120b (65 GB). Pull it when you have the disk: ollama pull gpt-oss:120b"
# python env
if (-not (Test-Path "server\.venv")) { python -m venv server\.venv }
.\server\.venv\Scripts\pip install -r server\orchestrator\requirements.txt
# docker services
Set-Location server; docker compose up -d; Set-Location $repo
# godot pieces
.\scripts\install_gdunit4.ps1
.\scripts\dump_godot_docs.ps1
.\studio.ps1 scripts\fetch_godot_docs.py
.\studio.ps1 scripts\build_rag_index.py
.\studio.ps1 scripts\eval_reviewer.py --checks-only
Write-Host ""
Write-Host "Server ready. Start the loop with server\run-orchestrator.ps1 (and put it in Task Scheduler)."
Write-Host ""
Write-Host "--- doctor ---"
.\studio.ps1 scripts\doctor.py
