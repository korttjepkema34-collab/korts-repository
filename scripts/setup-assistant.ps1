# Run from the personal repository. Installs only the local Python environment; no cloud purchases.
param([ValidateSet('server','gpu')][string]$Role='server',[switch]$PullModels)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
Set-Location $repo
function CheckExit { if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" } }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11+ from python.org, with Tcl/Tk and PATH enabled.' }
python -c "import sys,sqlite3; assert sys.version_info >= (3,11); c=sqlite3.connect(':memory:'); c.execute('CREATE VIRTUAL TABLE t USING fts5(body)')"
CheckExit
if (-not (Test-Path '.venv')) { python -m venv .venv; CheckExit }
& .\.venv\Scripts\python.exe -m assistant.run init
CheckExit
if ($PullModels) {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw 'Install Ollama first.' }
    $model=if ($Role -eq 'server') {'qwen3.5:4b'} else {'qwen3.5:9b'}
    ollama pull $model; CheckExit
}
Write-Host 'Setup files created. Read docs/assistant/SETUP.md; model accounts and qualification are still required.'
