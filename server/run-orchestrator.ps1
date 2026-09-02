# Start the orchestrator natively on the Windows server. Task Scheduler target.
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r orchestrator\requirements.txt }
Get-Content .env | Where-Object { $_ -match '^\s*[^#][^=]*=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
}
$env:REPO_ROOT = (Resolve-Path "..").Path
$env:PYTHONPATH = "$env:REPO_ROOT;$PSScriptRoot"
.\.venv\Scripts\python.exe -m orchestrator.main
