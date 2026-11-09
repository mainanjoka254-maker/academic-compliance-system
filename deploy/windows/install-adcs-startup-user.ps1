# Creates a per-user Startup shortcut to run ADCS at logon (NO admin required).
# This keeps services active while you are logged in (laptop must be on). Not 24/7 if the machine sleeps/shuts down.
$ErrorActionPreference = 'Stop'
$root = "C:\Users\user\Documents\GitHub\academic compliance system"
$target = Join-Path $root "deploy\windows\start-adcs.cmd"
$startup = [Environment]::GetFolderPath('Startup')
$link = Join-Path $startup "ADCS-Start.lnk"
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($link)
$sc.TargetPath = $target
$sc.WorkingDirectory = $root
$sc.WindowStyle = 7
$sc.Description = "Start ADCS (MySQL, backend, frontend)"
$sc.Save()
Write-Host "Created startup shortcut: $link"
Write-Host "Run now: $target"