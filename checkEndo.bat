@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%checkEndo.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

exit /b %EXIT_CODE%
