# Dump the installed Godot's own class reference (exact version) for the coder's search tool.
# Run from the repo root on the server. Needs GODOT_BIN in server/.env or the environment.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $repo "server\.env"
if (Test-Path $envFile) { Get-Content $envFile | Where-Object { $_ -match '^GODOT_BIN=' } | ForEach-Object { $env:GODOT_BIN = ($_ -split '=', 2)[1].Trim() } }
if (-not $env:GODOT_BIN) { throw "GODOT_BIN not set" }
$out = Join-Path $repo "server\godot-docs"
New-Item $out -ItemType Directory -Force | Out-Null
& $env:GODOT_BIN --headless --doctool $out --no-docbase
Write-Host "class reference dumped to $out ($((Get-ChildItem $out -Recurse -Filter *.xml).Count) files)"
