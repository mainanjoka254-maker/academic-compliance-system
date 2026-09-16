$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$startupKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$command = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\scripts\start-system.ps1`""

New-Item -Path $startupKey -Force | Out-Null
Set-ItemProperty -Path $startupKey -Name "AcademicComplianceSystem" -Value $command
Write-Host "Registered Academic Compliance System to start when you sign in to Windows."
Write-Host "Run manually any time with: powershell -ExecutionPolicy Bypass -File $root\scripts\start-system.ps1"
