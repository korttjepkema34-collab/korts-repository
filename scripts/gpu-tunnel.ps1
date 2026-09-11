# Keeps the SSH port forward to the gaming PC's Ollama alive across sleep, reboot and network drops.
# Server 127.0.0.1:11435 -> gaming PC 127.0.0.1:11434. Host-key checking stays ON: accept the
# gaming PC key once interactively before using this script.
param([Parameter(Mandatory = $true)][string]$Target, [int]$LocalPort = 11435, [int]$RemotePort = 11434)
$ErrorActionPreference = 'Continue'
$logDir = Join-Path $env:USERPROFILE 'KortAssistant\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'gpu-tunnel.log'
$delay = 5
while ($true) {
  $started = Get-Date
  Add-Content $log "$(Get-Date -Format o) connecting to $Target"
  & ssh -N -L "127.0.0.1:${LocalPort}:127.0.0.1:${RemotePort}" `
      -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 `
      -o BatchMode=yes -o ConnectTimeout=15 $Target
  $code = $LASTEXITCODE
  $ran = ((Get-Date) - $started).TotalSeconds
  Add-Content $log "$(Get-Date -Format o) ssh exited with $code after $([int]$ran)s"
  # Back off while the gaming PC sleeps or is off; reset once a connection held for a while.
  if ($ran -gt 120) { $delay = 5 } else { $delay = [Math]::Min($delay * 2, 300) }
  Start-Sleep -Seconds $delay
}
