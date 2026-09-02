# Install gdUnit4 into game/addons/gdUnit4 on the Windows server. Run from the repo root.
# Downloads the latest release zip from GitHub and copies only the addon folder.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$tmp = Join-Path $env:TEMP "gdunit4"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item $tmp -ItemType Directory | Out-Null
$rel = Invoke-RestMethod "https://api.github.com/repos/MikeSchulze/gdUnit4/releases/latest"
$zip = Join-Path $tmp "gdunit4.zip"
Invoke-WebRequest $rel.zipball_url -OutFile $zip
Expand-Archive $zip -DestinationPath $tmp
$src = Get-ChildItem $tmp -Directory | Where-Object { Test-Path (Join-Path $_.FullName "addons\gdUnit4") } | Select-Object -First 1
$dest = Join-Path $repo "game\addons\gdUnit4"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item (Split-Path $dest) -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $src.FullName "addons\gdUnit4") $dest -Recurse
Write-Host "gdUnit4 $($rel.tag_name) installed to $dest"
Write-Host "Now enable it once: open game/ in the Godot editor > Project > Project Settings > Plugins > gdUnit4, or add"
Write-Host '  [editor_plugins] enabled=PackedStringArray("res://addons/gdUnit4/plugin.cfg")  to game/project.godot'
