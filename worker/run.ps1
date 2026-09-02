# Start the GPU worker. Meant for Task Scheduler "At log on".
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
.\.venv\Scripts\python.exe worker.py
