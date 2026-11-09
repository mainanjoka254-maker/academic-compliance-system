@echo off
setlocal
set ROOT=C:\Users\user\Documents\GitHub\academic compliance system
REM Keep ADCS running (no admin required). Place a shortcut to this file in shell:startup.
REM MySQL (XAMPP MariaDB)
tasklist /FI "IMAGENAME eq mysqld.exe" | find /I "mysqld.exe" >nul || start "" /MIN "C:\xampp\mysql\bin\mysqld.exe" --defaults-file=C:\xampp\mysql\bin\my.ini --standalone
REM Backend
powershell -NoProfile -Command "if(-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)){Start-Process -WindowStyle Minimized -WorkingDirectory '%ROOT%\ADCS\backend' -FilePath '%ROOT%\ADCS\backend\.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000'}"
REM Frontend (preview, requires prior build)
powershell -NoProfile -Command "if(-not (Get-NetTCPConnection -LocalPort 4173 -State Listen -ErrorAction SilentlyContinue)){Start-Process -WindowStyle Minimized -WorkingDirectory '%ROOT%\ADCS\frontend' -FilePath 'cmd.exe' -ArgumentList '/c','npm run preview -- --host --port 4173'}"
endlocal