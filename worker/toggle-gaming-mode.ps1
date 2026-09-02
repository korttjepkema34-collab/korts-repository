# Desktop shortcut target. Creates or removes the GAMING_MODE file the worker watches.
$flag = Join-Path $PSScriptRoot "GAMING_MODE"
if (Test-Path $flag) { Remove-Item $flag; Write-Host "Gaming mode OFF: worker will resume pulling jobs." }
else { New-Item $flag -ItemType File | Out-Null; Write-Host "Gaming mode ON: worker will finish its current job and free VRAM." }
