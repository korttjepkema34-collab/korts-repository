# Registers the persistent assistant runner and (optionally) the dashboard and GPU tunnel as
# Windows scheduled tasks that start at logon and restart after failures. Run in an elevated or
# normal PowerShell as the same Windows user that owns the private runtime (%USERPROFILE%\KortAssistant).
# Review before running; nothing here is executed automatically by the assistant.
param(
  [switch]$Dashboard,
  [switch]$Tunnel,
  [string]$TunnelTarget = '',        # e.g. worker@100.x.y.z  (gaming PC over Tailscale)
  [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $python)) { $python = Join-Path $repo '.venv\Scripts\python.exe' }
if (-not (Test-Path $python)) { throw 'Run scripts/setup-assistant.ps1 first.' }
$user = "$env:USERDOMAIN\$env:USERNAME"

function Register-Assistant($name, $exe, $arguments) {
  $action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew -StartWhenAvailable
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description 'Kort assistant (see docs/assistant/OPERATIONS.md)' -Force | Out-Null
  Write-Host "Registered $name"
}

$names = @('KortAssistant-Runner', 'KortAssistant-Dashboard', 'KortAssistant-GpuTunnel')
if ($Uninstall) {
  foreach ($n in $names) { Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
  Write-Host 'Removed scheduled tasks. Task state in the private runtime is untouched.'
  return
}

& (Join-Path $repo '.venv\Scripts\python.exe') -m assistant.run doctor
if ($LASTEXITCODE -ne 0) { Write-Warning 'Doctor reported setup gaps. The runner will start but tasks may block until they are fixed.' }

# The runner holds a SQLite lease: a second copy refuses to start, a crashed copy is replaced.
Register-Assistant 'KortAssistant-Runner' $python '-m assistant.runner'
if ($Dashboard) { Register-Assistant 'KortAssistant-Dashboard' $python '-m assistant.web serve' }
if ($Tunnel) {
  if (-not $TunnelTarget) { throw 'Pass -TunnelTarget user@gaming-pc-tailscale-ip' }
  $ps = (Get-Command powershell.exe).Source
  Register-Assistant 'KortAssistant-GpuTunnel' $ps "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$repo\scripts\gpu-tunnel.ps1`" -Target $TunnelTarget"
}
Write-Host 'Start now with: Start-ScheduledTask -TaskName KortAssistant-Runner'
Write-Host 'Verify after a reboot: python -m assistant.run health  (runner heartbeat should be recent)'
