# Removes ADCS Windows auto-start tasks (does not delete data)
$ErrorActionPreference = 'SilentlyContinue'
"ADCS-MySQL","ADCS-Backend","ADCS-Frontend" | ForEach-Object {
  Unregister-ScheduledTask -TaskName $_ -Confirm:$false
  Write-Host "Removed $_ (if it existed)"
}