# Removes the per-user ADCS startup shortcut (no admin). Does not delete data.
$ErrorActionPreference = 'SilentlyContinue'
$link = Join-Path ([Environment]::GetFolderPath('Startup')) "ADCS-Start.lnk"
Remove-Item $link -Force
Write-Host "Removed $link (if it existed)"