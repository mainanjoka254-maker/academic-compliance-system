# Start ADCS tasks now (after install). Requires tasks to exist.
$ErrorActionPreference = 'SilentlyContinue'
Start-ScheduledTask -TaskName "ADCS-MySQL"
Start-Sleep -Seconds 5
Start-ScheduledTask -TaskName "ADCS-Backend"
Start-Sleep -Seconds 4
Start-ScheduledTask -TaskName "ADCS-Frontend"
Get-ScheduledTask -TaskName "ADCS-*" | Select-Object TaskName,State | Format-Table -AutoSize