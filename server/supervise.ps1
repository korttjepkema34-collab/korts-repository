# Supervisor: keeps the orchestrator alive, restarts it after the engineer merges a fix, and rolls
# back to the last good commit if it does not come back healthy. Task Scheduler runs THIS script.
#   powershell -File C:\studio\server\supervise.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$backoff = 10
while ($true) {
  $selfChange = Test-Path (Join-Path $root "RESTART_REQUESTED")
  if ($selfChange) { Remove-Item (Join-Path $root "RESTART_REQUESTED") -Force }
  $started = Get-Date
  & powershell -File (Join-Path $PSScriptRoot "run-orchestrator.ps1")
  $code = $LASTEXITCODE
  $ran = (Get-Date) - $started
  if ($code -eq 3) { Write-Host "supervisor: restart requested by the engineer"; $backoff = 5; continue }
  # Crashed. If the last start followed a self-change and it died within 5 minutes, roll back.
  $lastGood = Join-Path $root "reports\last_good.txt"
  $health = Join-Path $root "reports\health.json"
  $healthy = (Test-Path $health) -and ((Get-Date) - (Get-Item $health).LastWriteTime).TotalMinutes -lt 3
  if ($selfChange -and $ran.TotalMinutes -lt 5 -and -not $healthy -and (Test-Path $lastGood)) {
    $sha = (Get-Content $lastGood).Trim()
    Write-Host "supervisor: loop died after the engineer's change; rolling back to $sha"
    git -C $root checkout -q main
    git -C $root revert --no-edit -m 1 HEAD 2>$null; if ($LASTEXITCODE -ne 0) { git -C $root reset -q --hard $sha }
    Add-Content (Join-Path $root "incidents\ROLLBACKS.md") "- $(Get-Date -Format s): rolled back to $sha after a crash within 5 min of an engineer merge (exit $code)"
  }
  Write-Host "supervisor: orchestrator exited with $code after $([int]$ran.TotalSeconds)s; restarting in $backoff s"
  Start-Sleep -Seconds $backoff
  $backoff = [Math]::Min($backoff * 2, 300)
  if ($ran.TotalMinutes -gt 10) { $backoff = 10 }
}
