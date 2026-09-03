# Run a repo script with the orchestrator's venv and server\.env loaded. Server only.
#   .\studio.ps1 scripts\override.py session
#   .\studio.ps1 scripts\enqueue_train.py sdxl_lora
#   .\studio.ps1 training\eval_coder.py --model reapers-coder
$root = $PSScriptRoot
$py = Join-Path $root "server\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "server\.venv missing: run server\run-orchestrator.ps1 once (it creates the venv)"; exit 1 }
$envFile = Join-Path $root "server\.env"
if (Test-Path $envFile) {
  Get-Content $envFile | Where-Object { $_ -match '^\s*[^#][^=]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    $v = ($v -split '\s+#', 2)[0]
    [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
  }
}
$env:REPO_ROOT = $root
$env:PYTHONPATH = "$root;$root\server"
Set-Location $root
& $py @args
