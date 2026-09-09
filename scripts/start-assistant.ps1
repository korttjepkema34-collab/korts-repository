param([switch]$Desktop,[double]$Hours=8)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
Set-Location $repo
$python=Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run scripts/setup-assistant.ps1 first.' }
if ($Desktop) { & $python -m assistant.desktop }
else {
    & $python -m assistant.run doctor
    if ($LASTEXITCODE -ne 0) { throw 'Resolve doctor findings before starting overnight work.' }
    & $python -m assistant.run run --hours $Hours
}
if ($LASTEXITCODE -ne 0) { throw "Assistant exited with code $LASTEXITCODE" }
