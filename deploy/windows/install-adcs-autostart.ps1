# ADCS local always-on (Windows) — keeps services running while this machine is on
# Run in an elevated PowerShell if task creation is denied. No secrets stored here.

$ErrorActionPreference = 'Stop'
$root = "C:\Users\user\Documents\GitHub\academic compliance system"
$backend = Join-Path $root "ADCS\backend"
$frontend = Join-Path $root "ADCS\frontend"
$mysql = "C:\xampp\mysql\bin\mysqld.exe"
$cmd = "$env:SystemRoot\System32\cmd.exe"
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) { $npm = "C:\Program Files\nodejs\npm.cmd" }

function Ensure-Task($name, $action, $trigger, $settings) {
  $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($existing) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
  Write-Host "Registered $name"
}

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)

# MySQL (XAMPP MariaDB)
if (Test-Path $mysql) {
  $mysqlAction = New-ScheduledTaskAction -Execute $mysql -WorkingDirectory "C:\xampp\mysql"
  $mysqlTrigger = New-ScheduledTaskTrigger -AtStartup
  Ensure-Task "ADCS-MySQL" $mysqlAction $mysqlTrigger $settings
}

# Backend (Uvicorn) - uses project venv; reads ADCS/backend/.env
$uvicorn = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $uvicorn)) { throw "Python venv not found: $uvicorn" }
$backendAction = New-ScheduledTaskAction -Execute $uvicorn -Argument "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $backend
$backendTrigger = New-ScheduledTaskTrigger -AtStartup
Ensure-Task "ADCS-Backend" $backendAction $backendTrigger $settings

# Frontend preview (built) - serves on 4173 with /api proxy
if (-not (Test-Path $frontend)) { throw "Frontend path not found: $frontend" }
if (-not (Test-Path $npm)) { throw "npm.cmd not found (install Node.js): $npm" }
$frontendAction = New-ScheduledTaskAction -Execute $cmd -Argument "/c `"$npm`" run preview -- --host --port 4173" -WorkingDirectory $frontend
$frontendTrigger = New-ScheduledTaskTrigger -AtStartup
Ensure-Task "ADCS-Frontend" $frontendAction $frontendTrigger $settings

Get-ScheduledTask -TaskName "ADCS-*" | Select-Object TaskName,State | Format-Table -AutoSize