$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$taskName = "Academic Compliance System"
$command = "powershell.exe -ExecutionPolicy Bypass -File `"$root\scripts\start-system.ps1`""

schtasks.exe /Create /TN $taskName /TR $command /SC ONLOGON /F | Out-Host
Write-Host "Registered '$taskName' to start when you sign in to Windows."
Write-Host "Run manually any time with: powershell -ExecutionPolicy Bypass -File $root\scripts\start-system.ps1"
