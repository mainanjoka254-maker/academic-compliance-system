@echo off
REM Run this as Administrator (right-click -> "Run as administrator")
REM Installs ADCS auto-start tasks (MySQL, Backend :8000, Frontend :4173)
cd /d "C:\Users\user\Documents\GitHub\academic compliance system"
echo === ADCS autostart install (requires Administrator) ===
powershell -NoProfile -ExecutionPolicy Bypass -File ".\deploy\windows\install-adcs-autostart.ps1"
if errorlevel 1 (
  echo.
  echo Install failed. Make sure you ran this file as Administrator.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File ".\deploy\windows\start-adcs-now.ps1"
echo.
echo === Verifying tasks ===
powershell -NoProfile -Command "Get-ScheduledTask -TaskName ADCS-MySQL,ADCS-Backend,ADCS-Frontend -ErrorAction SilentlyContinue | Select-Object TaskName,State,LastRunTime,NextRunTime | Format-Table -AutoSize"
echo.
echo If tasks are listed as Ready/Running, setup is complete.
pause
