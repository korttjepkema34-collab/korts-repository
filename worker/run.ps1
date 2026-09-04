# Start the GPU worker and keep it alive. Task Scheduler "At log on" target.
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
$backoff = 10
while ($true) {
  $started = Get-Date
  .\.venv\Scripts\python.exe worker.py
  $ran = (Get-Date) - $started
  Write-Host "worker exited ($LASTEXITCODE) after $([int]$ran.TotalSeconds)s; restarting in $backoff s"
  Start-Sleep -Seconds $backoff
  $backoff = if ($ran.TotalMinutes -gt 10) { 10 } else { [Math]::Min($backoff * 2, 300) }
}
