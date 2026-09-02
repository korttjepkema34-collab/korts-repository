# Start the audio API on the gaming PC. Own venv so torch versions do not fight ComfyUI's.
Set-Location $PSScriptRoot
if (-not (Test-Path .venv-audio)) { python -m venv .venv-audio; .\.venv-audio\Scripts\pip install -r requirements-audio.txt }
.\.venv-audio\Scripts\python.exe -m uvicorn audio_api:app --host 127.0.0.1 --port 8190
